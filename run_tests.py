"""Headless verification harness for activity_1.py (SDL dummy video driver).

Run:  python3 run_tests.py
Sets SDL_VIDEODRIVER=dummy / SDL_AUDIODRIVER=dummy for this process only;
activity_1.py itself stays untouched and desktop-runnable.
"""
import os, sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'   # headless CI only, never in the app
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'activity_1_2d_animation'))

import pygame
import activity_1 as A

# ------------------------------------------------------------- 1) self-tests
A.run_self_tests()

# ---------------------------------- 2) extended dynamics checks (6000 frames)
b = A.BallState()
settled_frame, prev_vy = None, None
for f in range(6000):
    prev_vy = b.vy
    b.update()
    # every frame the ball must stay above the floor (no tunnelling)
    assert b.y + A.BALL_RADIUS <= A.FLOOR_Y + 1e-6, f'floor breach at {f}'
    # restitution law holds on every bounce: v_rebound = -e * v_impact
    if prev_vy > 0 and b.vy < 0:
        # impact speed recorded before the reflection this frame
        assert abs(b.vy + A.RESTITUTION * b.last_impact_speed) < 1e-9
        assert b.vy >= -prev_vy - 1e-9 or abs(b.vy) < abs(prev_vy)
        settled_frame = None
    if (abs(b.vx) < 0.05 and abs(b.vy) < 0.05
            and b.y + A.BALL_RADIUS >= A.FLOOR_Y - 0.5):
        if settled_frame is None:
            settled_frame = f
        elif f - settled_frame > 120:        # stayed at rest for 2 s
            break
print(f'dynamics: ball at rest by frame {f}, final state y={b.y:.2f} '
      f'v=({b.vx:.3f},{b.vy:.3f}), {b.bounces} bounces')
assert f < 6000, 'ball never settled within 6000 frames'

# ------------------- 3) headless interactive run with scripted input + saves
CAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'activity_1_2d_animation', 'frames')
os.makedirs(CAP_DIR, exist_ok=True)

pygame.init()
screen = pygame.display.set_mode((A.SCREEN_WIDTH, A.SCREEN_HEIGHT))
pygame.display.set_caption(A.CAPTION)
font = pygame.font.Font(None, 30)
small_font = pygame.font.Font(None, 22)

mode, tween, morph, ball = 1, A.TweenState(), A.MorphState(), A.BallState()
script = {30:  [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)],
          130: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)],
          200: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)],
          210: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
          205: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)],
          230: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)],
          400: [pygame.event.Event(pygame.QUIT)]}
captures = {25: 'mode1_tweening_lerp.png',
            100: 'mode2_morphing_mid.png',
            175: 'mode3_dynamics_bounce.png',
            215: 'mode1_tweening_ease.png'}
frame, total = 0, 0
quit_requested = False
while frame <= 400 and not quit_requested:
    for ev in script.get(frame, []):
        if ev.type == pygame.QUIT:
            quit_requested = True
            break
        if ev.key == pygame.K_1: mode = 1
        elif ev.key == pygame.K_2: mode = 2
        elif ev.key == pygame.K_3: mode = 3
        elif ev.key == pygame.K_l and mode == 1: tween.use_ease = False
        elif ev.key == pygame.K_e and mode == 1: tween.use_ease = True
        elif ev.key == pygame.K_SPACE and mode == 3: ball.reset()
    if quit_requested:
        break
    if mode == 1: tween.update()
    elif mode == 2: morph.update()
    else:
        ball.update()
        if ball.x - A.BALL_RADIUS < 0:
            ball.x, ball.vx = A.BALL_RADIUS, abs(ball.vx)
        elif ball.x + A.BALL_RADIUS > A.SCREEN_WIDTH:
            ball.x, ball.vx = A.SCREEN_WIDTH - A.BALL_RADIUS, -abs(ball.vx)
    screen.fill(A.COLOR_BG)
    if mode == 1: A.render_tween(screen, tween)
    elif mode == 2: A.render_morph(screen, morph, font)
    else: A.render_dynamics(screen, ball, font)
    A.draw_hud(screen, font, small_font, mode, tween, ball, 60.0)
    pygame.display.flip()
    total += 1
    if frame in captures:
        pygame.image.save(screen, os.path.join(CAP_DIR, captures[frame]))
        print(f'frame {frame}: saved {captures[frame]} (mode {mode}, '
              f'morph t={morph.t:.3f}, ball y={ball.y:.1f} vy={ball.vy:.2f})')
    frame += 1
print(f'headless interactive run: {total} frames rendered without errors')
pygame.quit()
print('ALL TESTS PASSED')
