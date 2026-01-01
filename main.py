import sys
import random
import cv2
import mediapipe as mp
import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WHITE, BLACK, GREEN
from entities import Player, Enemy, Bullet, set_max_width, set_screen_height
from hand_utils import count_fingers, palm_openness, fingertip_distance


# ============================================================================
# Initialization Functions
# ============================================================================

def init_pygame():
    """Initialize Pygame display and resources."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Gesture Shooting - Gemini Demo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24)
    return screen, clock, font


def init_mediapipe():
    """Initialize MediaPipe hand detection."""
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    mp_draw = mp.solutions.drawing_utils
    return hands, mp_draw, mp_hands


def init_camera():
    """Initialize video capture."""
    cap = cv2.VideoCapture(0)
    return cap


def init_sprites():
    """Initialize all game sprites."""
    all_sprites = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)
    all_sprites.add(player)

    for _ in range(20):
        enemy = Enemy()
        enemy.rect.x = random.randrange(0, max(1, SCREEN_WIDTH - enemy.rect.width))
        enemy.rect.y = random.randrange(-100, -40)
        all_sprites.add(enemy)
        enemies.add(enemy)

    return all_sprites, enemies, bullets, player


def init_game_state():
    """Initialize game state variables."""
    return {
        'running': True,
        'hand_x': 0.5,
        'hand_y': 0.5,
        'is_firing': False,
        'score': 0,
        'ammo': 100.0,
        'fire_time_acc': 0.0,
    }


def init_firing_config():
    """Initialize firing configuration constants."""
    return {
        'max_ammo': 100,
        'ammo_refill_rate': 10.0,
        'min_cooldown': 0.04,
        'max_cooldown': 0.45,
        'bullets_per_shot': 5,
        'tip_min_dist': 0.02,
        'tip_max_dist': 0.18,
    }


# ============================================================================
# Game Loop Logic Functions
# ============================================================================

def process_events():
    """Process pygame events. Returns whether to continue running."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True


def process_hand_gesture(frame, hands, mp_hands, mp_draw, firing_config):
    """
    Process hand gesture from camera frame.
    Returns: (hand_x, hand_y, is_firing, openness, pinch_closeness, display_status, frame)
    """
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    hand_x, hand_y = 0.5, 0.5
    is_firing = False
    openness = None
    pinch_closeness = None
    display_status = "No hand detected"

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            hand_x = hand_landmarks.landmark[9].x
            hand_y = hand_landmarks.landmark[9].y
            finger_count = count_fingers(hand_landmarks)
            openness = palm_openness(hand_landmarks)
            tip_dist = fingertip_distance(hand_landmarks, 4, 8)

            tip_min = firing_config['tip_min_dist']
            tip_max = firing_config['tip_max_dist']
            pinch_closeness = 1.0 - (tip_dist - tip_min) / (tip_max - tip_min)
            pinch_closeness = max(0.0, min(1.0, pinch_closeness))

            if finger_count >= 4:
                is_firing = True
                display_status = f"Gesture: Open (firing). Openness: {openness:.2f}"
            elif finger_count <= 1:
                is_firing = False
                display_status = "Gesture: Fist (not firing)"
            else:
                display_status = f"Gesture: Adjusting. Openness: {openness:.2f}"

            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    return hand_x, hand_y, is_firing, openness, pinch_closeness, display_status, frame


def update_game_state(player, enemies, bullets, state, dt, firing_config):
    """Update player, enemies, and bullets."""
    try:
        player._update_positions(state['hand_x'], state['hand_y'])
    except Exception:
        player.update(state['hand_x'])
    
    enemies.update()
    bullets.update()

    # Refill ammo
    max_ammo = firing_config['max_ammo']
    refill_rate = firing_config['ammo_refill_rate']
    state['ammo'] = min(float(max_ammo), state['ammo'] + refill_rate * dt)


def handle_firing(player, all_sprites, bullets, state, pinch_closeness, firing_config):
    """Handle player firing."""
    max_cooldown = firing_config['max_cooldown']
    min_cooldown = firing_config['min_cooldown']
    max_ammo = firing_config['max_ammo']
    bullets_per_shot = firing_config['bullets_per_shot']

    cooldown = max_cooldown
    if pinch_closeness is not None:
        cooldown = max_cooldown - pinch_closeness * (max_cooldown - min_cooldown)

    state['fire_time_acc'] += 1.0 / FPS

    if state['is_firing'] and state['ammo'] >= 1:
        if state['fire_time_acc'] >= cooldown:
            to_fire = min(int(state['ammo']), bullets_per_shot)
            if to_fire > 0:
                fired = player.shoot_multiple(to_fire)
                for b in fired:
                    all_sprites.add(b)
                    bullets.add(b)
                state['ammo'] -= float(to_fire)
                state['fire_time_acc'] = 0.0


def handle_collisions(player, all_sprites, enemies, bullets, state, firing_config):
    """Handle all collision detection and responses."""
    # Bullets -> Enemies
    hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
    for enemy, bullet_list in hits.items():
        for _ in bullet_list:
            enemy.take_damage(1)
        
        if enemy.hp <= 0:
            max_ammo = firing_config['max_ammo']
            state['score'] += getattr(enemy, 'score_value', 10)
            
            restore_map = {'weak': 3, 'normal': 5, 'tank': 10}
            restore_amount = restore_map.get(
                getattr(enemy, 'type', None),
                getattr(enemy, 'max_hp', 1)
            )
            state['ammo'] = min(float(max_ammo), state['ammo'] + restore_amount)
            
            enemy.kill()
            new_enemy = Enemy()
            new_enemy.rect.x = random.randrange(0, max(1, SCREEN_WIDTH - new_enemy.rect.width))
            new_enemy.rect.y = random.randrange(-100, -40)
            all_sprites.add(new_enemy)
            enemies.add(new_enemy)

    # Enemy -> Player
    hits = pygame.sprite.spritecollide(player, enemies, False)
    if hits:
        print("Game Over! You were hit.")
        state['running'] = False


def render_game(screen, font, player, all_sprites, enemies, frame, state, is_firing, display_status):
    """Render all game graphics."""
    screen.fill(BLACK)
    all_sprites.draw(screen)

    # Enemy HP bars
    for enemy in enemies:
        try:
            bar_w = enemy.rect.width
            bar_h = 6
            hb_x = enemy.rect.x
            hb_y = enemy.rect.y - 10
            pygame.draw.rect(screen, (120, 0, 0), (hb_x, hb_y, bar_w, bar_h))
            fill_w = int(bar_w * max(0.0, enemy.hp) / enemy.max_hp) if enemy.max_hp > 0 else 0
            if fill_w > 0:
                pygame.draw.rect(screen, GREEN, (hb_x, hb_y, fill_w, bar_h))
        except Exception:
            pass

    # HUD
    score_text = font.render(f"Score: {state['score']}", True, WHITE)
    screen.blit(score_text, (10, 10))
    ammo_text = font.render(
        f"Ammo: {int(state['ammo'])}/{int(state['ammo'])}", True, WHITE
    )
    screen.blit(ammo_text, (10, 40))

    # Camera preview
    small = cv2.resize(frame, (240, 180))
    small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    small = small.swapaxes(0, 1)
    pygame_surface = pygame.surfarray.make_surface(small)
    screen.blit(pygame_surface, (SCREEN_WIDTH - 250, 10))

    status_color = GREEN if is_firing else (255, 0, 0)
    status_text = font.render(display_status, True, status_color)
    screen.blit(status_text, (SCREEN_WIDTH - 250, 200))

    pygame.display.flip()


def game_loop(screen, clock, font, hands, mp_hands, mp_draw, cap, all_sprites, enemies, bullets, player, state, firing_config):
    """Main game loop."""
    set_max_width(SCREEN_WIDTH)
    set_screen_height(SCREEN_HEIGHT)
    
    print("Game start! Please face your hand to the camera.")

    while state['running']:
        dt = clock.tick(FPS) / 1000.0

        # Process input
        state['running'] = process_events()

        success, frame = cap.read()
        if not success:
            print("Failed to read camera")
            break

        # Process hand gesture
        hand_x, hand_y, is_firing, openness, pinch_closeness, display_status, frame = \
            process_hand_gesture(frame, hands, mp_hands, mp_draw, firing_config)

        state['hand_x'] = hand_x
        state['hand_y'] = hand_y
        state['is_firing'] = is_firing

        # Update game
        update_game_state(player, enemies, bullets, state, dt, firing_config)
        handle_firing(player, all_sprites, bullets, state, pinch_closeness, firing_config)
        handle_collisions(player, all_sprites, enemies, bullets, state, firing_config)

        # Render
        render_game(screen, font, player, all_sprites, enemies, frame, state, is_firing, display_status)

    cap.release()


def main():
    """Main entry point."""
    # Initialize all systems
    screen, clock, font = init_pygame()
    hands, mp_draw, mp_hands = init_mediapipe()
    cap = init_camera()
    all_sprites, enemies, bullets, player = init_sprites()
    state = init_game_state()
    firing_config = init_firing_config()

    try:
        # Run game
        game_loop(screen, clock, font, hands, mp_hands, mp_draw, cap,
                  all_sprites, enemies, bullets, player, state, firing_config)
    finally:
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    main()