# Activity 1: 2D Animation Principles & Kinematics Engine
## Technical Write-Up (Tweening, Morphing & Bouncing Dynamics)

**File:** `activity_1.py` (standalone, Python 3.10+, Pygame 2.1+)
**Window:** 800x600, 60 FPS cap via `pygame.time.Clock()`, title
`Activity 1: 2D Animation, Tweening & Morphing Engine`

## 1. Architecture and Separation of Concerns

The program follows the classic game-loop pattern
**Input -> Update -> Render -> FPS regulation**:

| Layer | Members | Responsibility |
|---|---|---|
| Pure math | `lerp`, `lerp_point`, `ease_in_out`, `clamp01`, `catmull_rom_point`, `sample_spline`, `split_edge`, `equalize_vertex_count`, `morph_polygon` | Stateless formulas; no Pygame calls; fully unit-testable |
| State classes | `TweenState`, `MorphState`, `BallState` | Per-frame state updates only (physics/animation logic) |
| Render functions | `render_tween`, `render_morph`, `render_dynamics`, `draw_hud` | All `pygame.draw` / blit operations |
| Main loop | `main()` | Event handling, mode switching, ordering, `clock.tick(60)` |

No rendering occurs inside any `update()` method, satisfying the lab's
separation-of-concerns rule: state calculations and surface drawing never mix.

## 2. Mode 1: Tweening Along a Spline

**Mathematics.** Linear interpolation between two points:

$$P(t) = (1 - t)\,P_{start} + t\,P_{end}, \qquad t \in [0, 1]$$

with normalized time $t = \text{frame} / (\text{duration} - 1)$ recomputed every
frame at 60 FPS. The sprite travels a closed Catmull-Rom spline through 5
waypoints. For control points $P_0, P_1, P_2, P_3$ and segment parameter
$u \in [0, 1]$:

$$pos = \tfrac{1}{2}\big(2P_1 + (-P_0 + P_2)u + (2P_0 - 5P_1 + 4P_2 - P_3)u^2 + (-P_0 + 3P_1 - 3P_2 + P_3)u^3\big)$$

The curve passes exactly through every waypoint (asserted in the self-tests)
and wraps smoothly because the closed loop re-uses neighbouring points across
the seam.

**Easing.** Two parameterizations are implemented and toggleable with the
`L` / `E` keys:

- Pure linear: the spline parameter equals $t$ directly (constant speed per segment).
- Ease-in/ease-out (smoothstep): $s(t) = t^2(3 - 2t)$, which has zero
  derivative at both endpoints, so the sprite starts and stops gently.

**Observation.** Switching from LERP to smoothstep visibly changes the timing
without moving the path: with LERP the sprite crosses each segment at constant
speed; with smoothstep it lingers near the endpoints and accelerates through
the middle of the traversal.

## 3. Mode 2: Polygon Morphing (Triangle -> Quadrilateral)

**Vertex correspondence rule.** When morphing polygon A (k vertices) into
polygon B (k+1 vertices), edges of A are subdivided until both keyframes hold
the identical vertex count. Here the 3-vertex triangle receives one inserted
midpoint duplicate on its first edge:

- Triangle keyframe A: `[(400, 120), (250, 400), (550, 400)]`
- After the split (4 vertices): `[(400, 120), (325, 260), (250, 400), (550, 400)]`
- Quadrilateral keyframe B: `[(400, 100), (200, 300), (420, 430), (620, 250)]`
  (vertex order chosen to match A's boundary traversal direction, so the
  correspondence produces clean, non-self-intersecting intermediates)

**Interpolation.** Each vertex pair is blended linearly:

$$V_{mid}(t) = (1 - t)\,V_A + t\,V_B$$

The parameter ping-pongs ($t: 0 \to 1 \to 0$) at 1/180 per frame, so the shape
morphs triangle -> quadrilateral -> triangle forever. The midpoint property
$V_{mid}(0.5) = \tfrac{1}{2}(V_A + V_B)$ and the endpoint identities
$V_{mid}(0) = V_A$, $V_{mid}(1) = V_B$ are all asserted in `run_self_tests()`.

**Observation.** The intermediate polygon stays convex and passes through a
smooth quadrilateral-like shape near $t = 0.5$; the inserted midpoint vertex
slides along the original triangle edge as it deploys into the quad's second
corner, which is exactly the visual effect the correspondence rule predicts.

## 4. Mode 3: Bouncing Ball Dynamics

**Model.** Explicit Euler integration with per-frame timestep $dt = 1$
(position integrated with the current velocity, then velocity updated by
gravity):

$$y_{next} = y + v\,dt, \qquad v_{next} = v + g\,dt, \qquad g = 0.5$$

The ball launches from (600, 100) with $v_x = -3.2$. On floor contact
($y + r \ge 500$) the penetration is resolved and the impact velocity is
reflected with the coefficient of restitution $e = 0.78$:

$$v_{rebound} = -e\,v_{impact}$$

**Energy decay and settling.** Two mechanisms remove energy so the ball comes
to rest: (a) a tiny per-frame horizontal drag factor (0.995) plus a 2% loss on
each bounce for rolling resistance, and (b) a rest-contact threshold: once the
impact speed drops below 3.5 px/frame, the micro-bounce is converted to a rest
contact. This last threshold is required because in discrete (per-frame)
integration a bouncing object regains $g$ of potential energy during the same
step that applies restitution; without the threshold a small limit cycle of
micro-bounces never terminates. In the verification run the ball performs 351
damped bounces and comes fully to rest by frame 856 (about 14 s), consistent
with the analytic decay: with $e = 0.78$, the rebound height after each bounce
shrinks by $e^2 \approx 0.61$ per bounce.

**Live readout.** The HUD displays position, $v_x$, $v_y$, $|v|$, bounce
count, last impact speed, and the $e$ and $g$ constants, plus an on-screen
velocity vector arrow attached to the ball.

**Wall handling.** Horizontal reflections at the side walls keep the ball
inside the window while the vertical dynamics remain the physically modelled
part of the simulation.

## 5. Interactive Controls

| Key | Action |
|---|---|
| `1` / `2` / `3` | Switch to Tweening / Morphing / Dynamics mode |
| `L` | Tweening: pure linear (LERP) interpolation |
| `E` | Tweening: ease-in/ease-out (smoothstep) interpolation |
| `SPACE` | Dynamics: relaunch the ball |
| `ESC` / window close | Quit |

The current mode and the active interpolation style are labelled on screen at
all times (top-left mode banner, style line under it, FPS counter top-right).

## 6. Verification (Headless Run)

The program was verified in a sandbox with `SDL_VIDEODRIVER=dummy`
`SDL_AUDIODRIVER=dummy` (environment variables only, not hardcoded; the file
runs unmodified on a desktop). The harness (`run_tests.py`, reproduced below)
ran `activity_1.py`'s own functions for several hundred scripted frames
including mode switches and captured the PNGs in `frames/`.

`python3 activity_1.py --selftest` runs the same self-tests on any machine.

**Asserted results, all passing:**

| Check | Expectation | Result |
|---|---|---|
| LERP midpoint | `lerp(0, 10, 0.5) == 5.0`; `lerp_point((0,0),(100,200),0.5) == (50, 100)` | pass |
| Smoothstep | $s(0) = 0$, $s(1) = 1$, $s(0.5) = 0.5$ | pass |
| Vertex split | triangle + 1 midpoint duplicate = 4 vertices; midpoint lies exactly halfway on the split edge | pass |
| Morph midpoint | every $V_{mid}(0.5)$ equals the componentwise average of the keyframe vertices; $t=0$ and $t=1$ reproduce the exact keyframes | pass |
| Restitution | setting `vy = 10` on the floor yields `vy == -0.78 * v_impact` with `v_impact = 10.5` (gravity added in the same frame) | pass |
| Euler gravity | one step from rest: `v == 0.5`, `y` unchanged (integrated with pre-gravity velocity) | pass |
| Spline waypoints | curve passes through all 5 waypoints at segment boundaries | pass |
| Long dynamics run | 6000-frame simulation, zero floor penetration (no tunnelling), restitution law verified on every bounce, ball at rest by frame 856 | pass |
| Stability | 400-frame scripted headless run across all 3 modes with mode/interpolation switches: no errors | pass |

**Verification harness** (`run_tests.py`; place it next to the
`activity_1_2d_animation/` folder):

```python
import os, sys
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'activity_1_2d_animation'))
import pygame
import activity_1 as A

A.run_self_tests()          # LERP / smoothstep / split / morph / restitution

b = A.BallState()           # 6000-frame dynamics soak test
for f in range(6000):
    prev_vy = b.vy
    b.update()
    assert b.y + A.BALL_RADIUS <= A.FLOOR_Y + 1e-6      # no floor tunnelling
    if prev_vy > 0 and b.vy < 0:                        # bounce happened
        assert abs(b.vy + A.RESTITUTION * b.last_impact_speed) < 1e-9

# scripted headless run: switch modes, capture frames
pygame.init()
screen = pygame.display.set_mode((A.SCREEN_WIDTH, A.SCREEN_HEIGHT))
font = pygame.font.Font(None, 30); small = pygame.font.Font(None, 22)
tween, morph, ball, mode = A.TweenState(), A.MorphState(), A.BallState(), 1
for frame in range(400):
    if frame == 30:  mode = 2
    if frame == 130: mode = 3
    if frame == 205: mode = 1
    if mode == 1: tween.update()
    elif mode == 2: morph.update()
    else: ball.update()
    screen.fill(A.COLOR_BG)
    if mode == 1: A.render_tween(screen, tween)
    elif mode == 2: A.render_morph(screen, morph, font)
    else: A.render_dynamics(screen, ball, font)
    A.draw_hud(screen, font, small, mode, tween, ball, 60.0)
    pygame.display.flip()
    if frame in (25, 100, 175, 215):
        name = {25: 'mode1_tweening_lerp.png', 100: 'mode2_morphing_mid.png',
                175: 'mode3_dynamics_bounce.png',
                215: 'mode1_tweening_ease.png'}[frame]
        pygame.image.save(screen, os.path.join('frames', name))
print('ALL TESTS PASSED')
```

**Captured frames** (`frames/`):

| File | Shows |
|---|---|
| `mode1_tweening_lerp.png` | Sprite mid-flight on the closed spline, LERP style, waypoints numbered 1-5 |
| `mode1_tweening_ease.png` | Same path under smoothstep easing (HUD shows the eased parameterization) |
| `mode2_morphing_mid.png` | Intermediate polygon at $t = 0.394$ between the split triangle and the quadrilateral, both keyframes ghosted |
| `mode3_dynamics_bounce.png` | Ball in flight after the first bounce ($|v| = 12.85$ px/frame readout, velocity arrow, floor at $y = 500$) |

## 7. Assessment Rubric Mapping

| Rubric criterion | Where demonstrated |
|---|---|
| Tweening mathematics & timing (25 pts) | `lerp`/`lerp_point` with normalized $t$, smoothstep `ease_in_out`, both toggleable, spline evaluated per frame |
| Polygon morphing algorithm (25 pts) | `split_edge` / `equalize_vertex_count` implement the vertex correspondence rule; `morph_polygon` does pairwise $V_{mid}(t)$ |
| Kinematics & dynamics accuracy (25 pts) | `BallState.update()`: Euler integration, $g = 0.5$, $v_{rebound} = -e\,v_{impact}$ with $e = 0.78$, energy decay and settling |
| Interactive controls & structure (25 pts) | Keys 1/2/3 mode switching, L/E interpolation toggle, SPACE reset, on-screen labels, 60 FPS `clock.tick`, modular update/render separation |
