import cv2
import mediapipe as mp
import pygame
import random
import sys

# --- 1. 初始化设置 ---

# 屏幕设置
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 900
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Pygame 初始化
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Gesture Shooting - Gemini Demo")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

# MediaPipe 手部检测初始化
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# 摄像头初始化
cap = cv2.VideoCapture(0)

# --- 2. 游戏类定义 ---

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 40))
        self.image.fill(GREEN)  # 玩家是绿色的
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 0 # 速度由手势决定

    def update(self, hand_x):
        # hand_x 是 0.0 到 1.0 之间的数值
        if hand_x is not None:
            # 映射摄像头坐标到屏幕坐标
            target_x = int(hand_x * SCREEN_WIDTH)
            # 平滑移动 (简单的线性插值)
            self.rect.centerx += (target_x - self.rect.centerx) * 0.2
        
        # 边界检查
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH

    def shoot(self):
        bullet = Bullet(self.rect.centerx, self.rect.top)
        all_sprites.add(bullet)
        bullets.add(bullet)

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Enemy types: define properties for each type
        # types: ('name', color, (w,h), hp, min_speed, max_speed, score)
        self.enemy_types = [
            ('weak', (200, 200, 0), (30, 20), 1, 1, 2, 5),
            ('normal', RED, (40, 30), 3, 1, 3, 10),
            ('tank', BLUE, (60, 50), 6, 0.5, 2, 25),
        ]
        self.set_type(random.choice(self.enemy_types))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)

    def set_type(self, t):
        # t is a tuple from enemy_types
        name, color, size, hp, min_s, max_s, score = t
        self.type = name
        self.color = color
        self.size = size
        self.max_hp = hp
        self.hp = hp
        self.score_value = score
        self.image = pygame.Surface(size)
        self.image.fill(color)
        # choose speed as float in range
        self.min_speed = min_s
        self.max_speed = max_s
        self.speedy = random.uniform(self.min_speed, self.max_speed)

    def reset(self):
        # randomize type and position when respawning
        self.set_type(random.choice(self.enemy_types))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)

    def take_damage(self, amount):
        self.hp -= amount

    def update(self, *args):
        self.rect.y += self.speedy
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.reset()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 20))
        self.image.fill(WHITE) # 子弹是白色的
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speedy = -10

    def update(self, *args):
        self.rect.y += self.speedy
        if self.rect.bottom < 0:
            self.kill()

# --- 3. 辅助函数：手势识别 ---

def count_fingers(hand_landmarks):
    """
    计算伸出的手指数量来判断是张开手掌还是握拳。
    返回: (finger_count, is_fist)
    """
    fingers = []
    
    # 拇指 (比较指尖和指关节的x坐标，取决于左右手，这里做简化处理)
    # 注意：为了简单，这里假设右手操作。如果拇指指尖在指关节右侧(画面左侧)，视为伸出
    if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # 其他四个手指 (比较指尖y坐标是否高于指关节y坐标)
    # 注意：图像坐标系中，y轴向下为正，所以"高"意味着y值更小
    tips = [8, 12, 16, 20] # 食指、中指、无名指、小指的指尖索引
    pips = [6, 10, 14, 18] # 对应的指关节索引

    for i in range(4):
        if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y:
            fingers.append(1)
        else:
            fingers.append(0)
    
    total_fingers = sum(fingers)
    # 如果伸出的手指少于等于1个，认为是握拳（停火）
    # 如果大于等于4个，认为是手掌张开（开火）
    return total_fingers


def palm_openness(hand_landmarks):
    """
    计算手掌开合程度，返回一个 0.0-1.0 之间的值，1.0 表示完全张开，0.0 表示完全合拢。
    使用手腕(0)与每个指尖(4,8,12,16,20)之间的平均距离作为简单估计。
    """
    wrist = hand_landmarks.landmark[0]
    tips = [4, 8, 12, 16, 20]
    dists = []
    for t in tips:
        lm = hand_landmarks.landmark[t]
        dx = lm.x - wrist.x
        dy = lm.y - wrist.y
        d = (dx * dx + dy * dy) ** 0.5
        dists.append(d)
    avg = sum(dists) / len(dists)
    # 经验映射：将平均距离大致映射到 [0.0, 1.0]
    # 下面的 min_dist 和 max_dist 是经验值，适配大多数摄像头/手势距离
    min_dist = 0.03
    max_dist = 0.22
    openness = (avg - min_dist) / (max_dist - min_dist)
    if openness < 0:
        openness = 0.0
    if openness > 1:
        openness = 1.0
    return openness


def fingertip_distance(hand_landmarks, idx1=4, idx2=8):
    """
    计算两个指尖之间的归一化距离（基于 MediaPipe 标准化坐标），返回欧氏距离。
    默认计算拇指（4）与食指（8）之间的距离。
    """
    a = hand_landmarks.landmark[idx1]
    b = hand_landmarks.landmark[idx2]
    dx = a.x - b.x
    dy = a.y - b.y
    return (dx * dx + dy * dy) ** 0.5

# --- 4. 游戏主循环 ---

# 精灵组
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

for i in range(8):
    e = Enemy()
    all_sprites.add(e)
    enemies.add(e)

running = True
hand_x_position = 0.5 # 默认在中间
is_firing = False
score = 0
fire_cooldown = 0 # 射击冷却时间 (旧逻辑保留为后备)

# --- Ammo & firing control ---
max_ammo = 20
ammo = float(max_ammo)
ammo_refill_rate = 3.0  # 每秒回复弹药数
fire_time_acc = 0.0

# cooldown mapping (seconds): when fingers closer -> faster (smaller cooldown)
# tuned for faster overall firing
min_cooldown = 0.04  # 最快射速 (秒)
max_cooldown = 0.45   # 最慢射速 (秒)

# fingertip mapping params (thumb-index)
tip_min_dist = 0.02
tip_max_dist = 0.18

print("Game start! Please face your hand to the camera.")
print("Open palm: Fire (rate depends on how closed your hand is)")
print("Make a fist: Stop firing")
print("Move left/right: Move the plane")

while running:
    # 控制帧率并获得本帧时间增量
    dt = clock.tick(FPS) / 1000.0

    # 1. Pygame 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 2. OpenCV & MediaPipe 处理
    success, frame = cap.read()
    if not success:
        print("无法读取摄像头")
        break
    
    # 翻转图像，使其像镜子一样（自然交互）
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    display_status = "No hand detected"
    openness = None
    closure = None
    tip_dist = None
    pinch_closeness = None

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # 获取手腕的坐标 (索引0) 或 中指根部 (索引9) 作为飞机的中心控制点
            # 坐标范围是 [0.0, 1.0]
            hand_x_position = hand_landmarks.landmark[9].x

            # 识别手势
            finger_count = count_fingers(hand_landmarks)
            # 计算手掌的开合度 (0.0 合拢, 1.0 完全张开)
            openness = palm_openness(hand_landmarks)
            closure = 1.0 - openness
            # 计算拇指与食指指尖距离, 将其映射为 closeness (0..1)
            tip_dist = fingertip_distance(hand_landmarks, 4, 8)
            # 将距离映射到 [0,1]，0 -> 分离（慢），1 -> 很近（快）
            pinch_closeness = 1.0 - (tip_dist - tip_min_dist) / (tip_max_dist - tip_min_dist)
            if pinch_closeness < 0:
                pinch_closeness = 0.0
            if pinch_closeness > 1:
                pinch_closeness = 1.0

            # 保持原有简单逻辑：几乎握拳(<=1 finger) 则停止开火；大开掌(>=4 fingers) 开火
            if finger_count >= 4:
                is_firing = True
                display_status = f"Gesture: Open (firing). Openness: {openness:.2f}"
            elif finger_count <= 1:
                is_firing = False
                display_status = "Gesture: Fist (not firing)"
            else:
                # 中间姿态：显示提示，但不强制停止/开启
                display_status = f"Gesture: Adjusting. Openness: {openness:.2f}"
            
            # 在摄像头画面上绘制手部骨架（可选，用于调试）
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # 3. 游戏逻辑更新
    player.update(hand_x_position)
    enemies.update()
    bullets.update()

    # 射击逻辑
    # 弹药自动补充
    ammo = min(float(max_ammo), ammo + ammo_refill_rate * dt)

    # 基于拇指-食指距离设置射速：距离越小（pinch_closeness 越大），射速越快
    if pinch_closeness is None:
        cooldown = max_cooldown
    else:
        cooldown = max_cooldown - pinch_closeness * (max_cooldown - min_cooldown)

    # 射击计时器
    fire_time_acc += dt

    if is_firing and ammo >= 1:
        if fire_time_acc >= cooldown:
            player.shoot()
            ammo -= 1.0
            fire_time_acc = 0.0
    # 当不允许开火时，保持计时器但不发射（不强制重置）

    # 碰撞检测：子弹击中敌人（按血量扣除）
    hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
    for enemy, bullet_list in hits.items():
        # 每颗子弹造成1点伤害（可按需调整）
        for _ in bullet_list:
            enemy.take_damage(1)
        if enemy.hp <= 0:
            score += getattr(enemy, 'score_value', 10)
            # 从精灵组移除并生成新的敌人
            enemy.kill()
            e = Enemy()
            all_sprites.add(e)
            enemies.add(e)

    # 碰撞检测：敌人撞到玩家
    hits = pygame.sprite.spritecollide(player, enemies, False)
    if hits:
        print("Game Over! You were hit.")
        running = False

    # 4. 渲染绘制
    screen.fill(BLACK) # 背景黑色
    all_sprites.draw(screen)

    # 绘制敌人血条（覆盖在敌人上方）
    for en in enemies:
        try:
            bar_w = en.rect.width
            bar_h = 6
            hb_x = en.rect.x
            hb_y = en.rect.y - 10
            # 背景（红）
            pygame.draw.rect(screen, (120, 0, 0), (hb_x, hb_y, bar_w, bar_h))
            # 前景（绿）按比例
            if en.max_hp > 0:
                fill_w = int(bar_w * max(0.0, en.hp) / en.max_hp)
            else:
                fill_w = 0
            if fill_w > 0:
                pygame.draw.rect(screen, GREEN, (hb_x, hb_y, fill_w, bar_h))
        except Exception:
            pass

    # 显示分数和弹药
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))
    ammo_text = font.render(f"Ammo: {int(ammo)}/{max_ammo}", True, WHITE)
    screen.blit(ammo_text, (10, 40))

    # 显示摄像头小窗口（画中画效果，方便玩家看自己的手势）
    # 将 OpenCV 的图像转换为 Pygame 图像
    frame = cv2.resize(frame, (240, 180)) # 缩小
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = frame.swapaxes(0, 1) # Pygame需要旋转一下数据
    pygame_surface = pygame.surfarray.make_surface(frame)
    screen.blit(pygame_surface, (SCREEN_WIDTH - 250, 10))
    
    # 显示状态文字
    status_text = font.render(display_status, True, GREEN if is_firing else RED)
    screen.blit(status_text, (SCREEN_WIDTH - 250, 200))

    pygame.display.flip()

cap.release()
pygame.quit()
sys.exit()