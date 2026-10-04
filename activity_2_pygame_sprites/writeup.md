# Activity 2 Technical Write-Up: Game Loop, Custom Sprites, & Collision Detection

**File:** `activity_2.py` (standalone, Python 3.10+, Pygame 2.1+)
**Window:** 800x600, 60 FPS, title `Activity 2: Sprite System & Collision Arena`

## 1. Architecture Overview

The program follows the classic game loop required by the manual:

```
Process Input -> Update Game State -> Render Display -> Regulate FPS
```

All four stages live in `main()`. A thin `Game` class owns the mutable state
(player, obstacle group, particle group, score, health, font) so the main loop
stays readable, while every stage is its own method:

| Stage | Where | What happens |
|---|---|---|
| Process Input | `Game.process_events()` | `pygame.event.get()` handles QUIT and ESC |
| Update State | `Game.update_state()` | `group.update()` for all sprites, then collision resolution |
| Render Display | `Game.render()` | `screen.fill`, `group.draw(screen)`, HUD blit, `pygame.display.flip()` |
| Regulate FPS | main loop | `clock.tick(60)` |

**Separation of concerns:** rendering is kept strictly OUT of
`sprite.update()`. Every sprite's `update()` only mutates its own state
(position, velocity, alpha); all blitting happens in the render stage through
`pygame.sprite.Group.draw(screen)`. This keeps sprites testable headlessly and
makes the render pipeline a single, predictable place.

## 2. Object-Oriented Sprite Design

All three entities subclass `pygame.sprite.Sprite` and override both
`__init__()` and `update()`.

**`Player`** draws a 40x40 circle in `(44, 94, 138)` on a
`pygame.Surface(..., pygame.SRCALPHA)` surface and centres itself on the
screen. Its `update()` uses `pygame.key.get_pressed()` for *continuous*
steering (held keys, unlike the event-based KEYDOWN approach) and applies
strict boundary clamping afterwards, so the player can never rest even one
pixel outside the arena:

```python
self.rect.left = max(self.rect.left, 0)
self.rect.right = min(self.rect.right, SCREEN_WIDTH)
```

The clamp is applied *after* the direction checks (`rect.left > 0`, etc.), so
movement and safety are independent layers.

**`Obstacle`** is a 30x30 red square `(220, 50, 50)` with an inner highlight.
Each instance spawns at a random position with a uniformly random direction and
speed in [3.0, 6.0] px/frame. `update()` moves by `velocity` and bounces off
the four screen edges: when an edge is crossed, the rect is snapped back to the
boundary and the velocity component is reflected (`abs()` / `-abs()`), which
guarantees the outgoing direction points back into the arena. This was verified
by a 400-frame invariant test: the obstacle never leaves the screen and its
velocity never points off-screen while flush against an edge.

**`Particle`** is a short-lived translucent circle (radius 3-7) spawned by
`spawn_particles()` on each collision. It drifts outward with a random
velocity and fades via *per-surface alpha*: `image.set_alpha()` decreases
linearly from 255 to 0 over a lifetime of 18-30 frames, then `self.kill()`
removes it from the group. Each particle owns its own SRCALPHA surface, so
alpha values never interfere between particles. The whole group is capped at
`MAX_PARTICLES = 300` so a collision storm cannot grow without bound.

## 3. Collision Detection & Game Feedback

`Game.update_state()` calls

```python
pygame.sprite.spritecollide(player, obstacles, False, pygame.sprite.collide_rect)
```

which performs bounding-rect intersection between the player and every obstacle
in the group (the manual's Task 2.3). On each hit the game:

1. increments `score` and decrements `health` (game feedback),
2. spawns a burst of translucent particles at the obstacle's centre,
3. respawns the obstacle at a random position away from the player
   (`respawn_away_from_player()` rejects positions that overlap or sit within
   80 px of the player, with a bounded retry loop), and
4. assigns the obstacle a fresh random velocity.

The game runs until the player closes the window or presses ESC; health is
tracked and displayed live from the start value of 10.

## 4. HUD Rendering Without Memory Leaks

A single `pygame.font.Font(None, 36)` is created **once** in `Game.__init__`
and reused every frame. `update_hud()` only calls `font.render(text, True, ...)`
(anti-aliased) and blits the result, showing `Score`, `Health`, and the live
`FPS` from `clock.get_fps()`. Because the font object is never re-created, no
per-frame font or surface allocation leak occurs. This was verified by running
400+ simulated frames with no exception and stable behaviour.

## 5. Headless Verification (Sandbox Testing)

The sandbox has no display, so the harness runs with
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`, drives the real classes
directly, and simulates the actual game loop for several hundred frames.
Results (all PASS):

| Check | Result |
|---|---|
| Obstacle group populated (8 sprites) | PASS |
| Player 40x40 SRCALPHA surface, correct colour, centred | PASS |
| Obstacle bounce invariants over 400 frames (never out of bounds, velocity flips at every edge) | PASS |
| Strict player clamping after forced overshoot (both corners) | PASS |
| Forced collision: score 0 -> 1, health 10 -> 9 | PASS |
| Forced collision spawns particles (14) and respawns obstacle away from player | PASS |
| Particle alpha decays 255 -> 0 and sprite is killed at end of life | PASS |
| 300+ full frames of the real loop run with no exceptions | PASS |
| Particle group stays bounded (no leak) | PASS |
| Anti-aliased HUD font renders non-empty surfaces | PASS |

Two frame captures were saved with `pygame.image.save()`:

- `frame_normal.png`: a normal play frame after 120 simulated frames
  (score 0, health 10, no particles).
- `frame_collision.png`: a collision frame with a live particle burst
  (score 4, health 6, 55 particles mid-fade), taken right after forcing three
  simultaneous collisions.

The deliverable `activity_2.py` itself is untouched by the harness and runs
unchanged on a real desktop (`python activity_2.py`).

## 6. Key Design Decisions

- **Velocity reflection via abs()/-abs():** prevents the classic sticky-edge
  bug where a sprite jitters at the boundary, because the outgoing direction is
  always forced inward.
- **Bounded respawn retry (1000 attempts):** `respawn_away_from_player` cannot
  loop forever even in pathological states.
- **Particle cap (300):** worst-case safety against unbounded group growth
  while keeping bursts visually dense.
- **Font as a long-lived attribute:** one allocation, rendered thousands of
  times; the HUD update path allocates only the small text surfaces blitted
  each frame.
- **`Game` container class:** keeps the four loop stages symmetrical and makes
  every stage independently callable in tests.
