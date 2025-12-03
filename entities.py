import pygame
import random

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((6, 12))
        self.image.fill((255,255,255))
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.vx = 0.0
        self.vy = -10.0

    def set_velocity(self, vx, vy):
        self.vx = vx
        self.vy = vy

    def update(self, *args):
        # move by float velocities but store as ints for rect
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        if self.rect.bottom < 0:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Enemy types: (name, color, (w,h), hp, min_speed, max_speed, score)
        self.enemy_types = [
            ('weak', (200, 200, 0), (30, 20), 1, 1, 2, 5),
            ('normal', (255,0,0), (40, 30), 3, 1, 3, 10),
            ('tank', (0,0,255), (60, 50), 6, 0.5, 2, 25),
        ]
        self.set_type(random.choice(self.enemy_types))
        self.rect = self.image.get_rect()
        self.rect.x = 0
        self.rect.y = random.randrange(-100, -40)

    def set_type(self, t):
        name, color, size, hp, min_s, max_s, score = t
        self.type = name
        self.color = color
        self.size = size
        self.max_hp = hp
        self.hp = hp
        self.score_value = score
        self.image = pygame.Surface(size)
        self.image.fill(color)
        self.min_speed = min_s
        self.max_speed = max_s
        self.speedy = random.uniform(self.min_speed, self.max_speed)

    def reset(self):
        self.set_type(random.choice(self.enemy_types))
        self.rect = self.image.get_rect()
        # place x within current max width if provided
        try:
            self.rect.x = random.randrange(0, _max_width - self.rect.width)
        except Exception:
            self.rect.x = 0
        self.rect.y = random.randrange(-100, -40)

    def take_damage(self, amount):
        self.hp -= amount

    def update(self, *args):
        self.rect.y += self.speedy
        if _screen_height is not None:
            if self.rect.top > _screen_height + 10:
                self.reset()


class Player(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y):
        super().__init__()
        self.image = pygame.Surface((50, 40))
        self.image.fill((0,255,0))
        self.rect = self.image.get_rect()
        self.rect.centerx = start_x
        self.rect.bottom = start_y
        self.speed = 0

    def update(self, hand_x):
        if hand_x is not None:
            target_x = int(hand_x * args_max_width())
            self.rect.centerx += (target_x - self.rect.centerx) * 0.2
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > args_max_width():
            self.rect.right = args_max_width()

    def shoot(self):
        b = Bullet(self.rect.centerx, self.rect.top)
        return [b]

    def shoot_multiple(self, count=3):
        fired = []
        patterns = {
            3: [(-4, -10), (0, -12), (4, -10)],
            2: [(-4, -11), (4, -11)],
            1: [(0, -12)],
        }
        vecs = patterns.get(count, patterns[3])
        for vx, vy in vecs:
            b = Bullet(self.rect.centerx, self.rect.top)
            b.set_velocity(vx, vy)
            fired.append(b)
        return fired

# helper used to avoid circular import; main will monkeypatch if needed
_max_width = None
_screen_height = None

def args_max_width():
    global _max_width
    return _max_width if _max_width is not None else 800

def set_max_width(w):
    global _max_width
    _max_width = w

def set_screen_height(h):
    global _screen_height
    _screen_height = h
