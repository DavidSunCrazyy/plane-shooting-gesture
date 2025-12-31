import sys
import random
import cv2
import mediapipe as mp
import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WHITE, BLACK, GREEN
from entities import Player, Enemy, Bullet, set_max_width, set_screen_height
from hand_utils import count_fingers, palm_openness, fingertip_distance


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Gesture Shooting - Gemini Demo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24)

    # MediaPipe
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)
    mp_draw = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)

    # provide screen size to entities module
    set_max_width(SCREEN_WIDTH)
    set_screen_height(SCREEN_HEIGHT)

    # sprite groups
    all_sprites = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)
    all_sprites.add(player)

    for i in range(20):
        e = Enemy()
        # place properly within screen
        e.rect.x = random.randrange(0, max(1, SCREEN_WIDTH - e.rect.width))
        e.rect.y = random.randrange(-100, -40)
        all_sprites.add(e)
        enemies.add(e)

    # state
    running = True
    hand_x_position = 0.5
    hand_y_position = 0.5
    is_firing = False
    score = 0

    # ammo & firing
    max_ammo = 100
    ammo = float(max_ammo)
    ammo_refill_rate = 10.0
    fire_time_acc = 0.0
    min_cooldown = 0.04
    max_cooldown = 0.45
    tip_min_dist = 0.02
    tip_max_dist = 0.18

    print("Game start! Please face your hand to the camera.")

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        success, frame = cap.read()
        if not success:
            print("Failed to read camera")
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        display_status = "No hand detected"
        openness = None
        pinch_closeness = None

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                hand_x_position = hand_landmarks.landmark[9].x
                hand_y_position = hand_landmarks.landmark[9].y
                finger_count = count_fingers(hand_landmarks)
                openness = palm_openness(hand_landmarks)
                tip_dist = fingertip_distance(hand_landmarks, 4, 8)
                pinch_closeness = 1.0 - (tip_dist - tip_min_dist) / (tip_max_dist - tip_min_dist)
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

        # update (pass both horizontal and vertical targets)
        try:
            player._update_positions(hand_x_position, hand_y_position)
        except Exception:
            # fallback to legacy single-arg update if something unexpected occurs
            player.update(hand_x_position)
        enemies.update()
        bullets.update()

        # ammo refill
        ammo = min(float(max_ammo), ammo + ammo_refill_rate * dt)

        # cooldown
        cooldown = max_cooldown if pinch_closeness is None else (max_cooldown - pinch_closeness * (max_cooldown - min_cooldown))
        fire_time_acc += dt

        bullets_per_shot = 5
        if is_firing and ammo >= 1:
            if fire_time_acc >= cooldown:
                to_fire = min(int(ammo), bullets_per_shot)
                if to_fire > 0:
                    fired = player.shoot_multiple(to_fire)
                    for b in fired:
                        all_sprites.add(b)
                        bullets.add(b)
                    ammo -= float(to_fire)
                    fire_time_acc = 0.0

        # collisions: bullets -> enemies
        hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
        for enemy, bullet_list in hits.items():
            for _ in bullet_list:
                enemy.take_damage(1)
            if enemy.hp <= 0:
                score += getattr(enemy, 'score_value', 10)
                restore_map = {'weak': 3, 'normal': 5, 'tank': 10}
                restore_amount = restore_map.get(getattr(enemy, 'type', None), getattr(enemy, 'max_hp', 1))
                ammo = min(float(max_ammo), ammo + restore_amount)
                enemy.kill()
                e = Enemy()
                e.rect.x = random.randrange(0, max(1, SCREEN_WIDTH - e.rect.width))
                e.rect.y = random.randrange(-100, -40)
                all_sprites.add(e)
                enemies.add(e)

        # collisions: enemy -> player
        hits = pygame.sprite.spritecollide(player, enemies, False)
        if hits:
            print("Game Over! You were hit.")
            running = False

        # render
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # enemy HP bars
        for en in enemies:
            try:
                bar_w = en.rect.width
                bar_h = 6
                hb_x = en.rect.x
                hb_y = en.rect.y - 10
                pygame.draw.rect(screen, (120,0,0), (hb_x, hb_y, bar_w, bar_h))
                fill_w = int(bar_w * max(0.0, en.hp) / en.max_hp) if en.max_hp > 0 else 0
                if fill_w > 0:
                    pygame.draw.rect(screen, GREEN, (hb_x, hb_y, fill_w, bar_h))
            except Exception:
                pass

        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        ammo_text = font.render(f"Ammo: {int(ammo)}/{max_ammo}", True, WHITE)
        screen.blit(ammo_text, (10, 40))

        # camera preview
        small = cv2.resize(frame, (240, 180))
        small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        small = small.swapaxes(0, 1)
        pygame_surface = pygame.surfarray.make_surface(small)
        screen.blit(pygame_surface, (SCREEN_WIDTH - 250, 10))

        status_text = font.render(display_status, True, GREEN if is_firing else (255,0,0))
        screen.blit(status_text, (SCREEN_WIDTH - 250, 200))

        pygame.display.flip()

    cap.release()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()