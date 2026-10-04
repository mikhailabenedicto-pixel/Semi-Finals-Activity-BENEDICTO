#!/usr/bin/env python3
"""
Activity 1: 2D Animation, Tweening & Morphing Engine
=====================================================
A standalone Pygame program demonstrating three classic 2D computer-animation
techniques, switchable at runtime with the keyboard:

  Mode 1 (key 1)  TWEENING : a sprite travels along a multi-point spline path
                             using linear interpolation (LERP) or ease-in/
                             ease-out (smoothstep) parameterization.
  Mode 2 (key 2)  MORPHING : a triangle morphs into a quadrilateral by linear
                             vertex interpolation (vertex correspondence rule).
  Mode 3 (key 3)  DYNAMICS : a bouncing ball simulated with explicit Euler
                             integration, gravity and coefficient of restitution.

Controls
--------
  1 / 2 / 3   switch mode (Tweening / Morphing / Dynamics)
  L           tweening only: toggle LINEAR interpolation
  E           tweening only: toggle EASE-IN/EASE-OUT (smoothstep) interpolation
  SPACE       dynamics only: reset the ball to its initial state
  ESC / quit  exit

Mathematical background (implemented in pure functions below, never inside
rendering code):

  1. Linear interpolation (LERP) between two scalars a and b:
         P(t) = (1 - t) * P_start + t * P_end,          t in [0, 1]
  2. Ease-in / ease-out (smoothstep):
         s(t) = t*t * (3 - 2*t)
     which has zero slope at both endpoints, producing a gentle start/stop.
  3. Catmull-Rom spline: a cubic interpolating curve through every waypoint.
     For points P0, P1, P2, P3 and parameter u in [0, 1] on the P1->P2 span:
         pos = 0.5 * ( (2*P1)                +
                       (-P0 + P2) * u        +
                       (2*P0 - 5*P1 + 4*P2 - P3) * u^2 +
                       (-P0 + 3*P1 - 3*P2 + P3) * u^3 )
  4. Morphing (vertex correspondence rule): when polygon A has fewer vertices
     than polygon B, edges of A are subdivided (a duplicated midpoint vertex is
     inserted) until both keyframes hold the SAME vertex count. Each vertex is
     then interpolated pairwise:
         V_mid(t) = (1 - t) * V_A + t * V_B
  5. Newtonian dynamics (explicit Euler integration, dt = 1 frame):
         y_next = y + v * dt
         v_next = v + g * dt
     On floor contact the vertical velocity is reflected and damped:
         v_rebound = -e * v_impact                (e = coefficient of restitution)
     A small horizontal drag factor removes energy each bounce so the ball
     eventually comes to rest.

Architecture / separation of concerns:
  * All mathematics lives in module-level pure functions and small state
    classes (update logic only, NO pygame.draw / blit calls).
  * All drawing lives in render_* functions.
  * The main loop follows  Input -> Update -> Render -> FPS regulation.

Requires: Python 3.10+, pygame 2.1+.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field

import pygame

# ---------------------------------------------------------------- constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
CAPTION = 'Activity 1: 2D Animation, Tweening & Morphing Engine'

# --- Mode 1: tweening ------------------------------------------------------
TWEEN_PATH = [                      # 5 waypoints -> 4 Catmull-Rom segments
    (120, 300),
    (280, 150),
    (430, 320),
    (580, 150),
    (700, 330),
]
TWEEN_DURATION_FRAMES = 240         # 4 seconds at 60 FPS for a full traversal
SPRITE_RADIUS = 18

# --- Mode 2: morphing ------------------------------------------------------
# KEYFRAME A: a triangle with only 3 vertices...
TRIANGLE_A = [(400, 120), (250, 400), (550, 400)]
# KEYFRAME B: a quadrilateral with 4 vertices.
# Vertex order matches the triangle's boundary traversal (top -> left ->
# bottom -> right) so the pairwise vertex correspondence produces a clean,
# self-intersection-free intermediate shape.
QUADRILATERAL_B = [(400, 100), (200, 300), (420, 430), (620, 250)]

# --- Mode 3: dynamics ------------------------------------------------------
GRAVITY = 0.5                       # px per frame^2 (lab manual value)
RESTITUTION = 0.78                  # e: v_rebound = -e * v_impact
FLOOR_Y = 500.0                     # y coordinate of the floor surface
BALL_START = (600.0, 100.0)
BALL_RADIUS = 22
HORIZONTAL_DRAG = 0.995             # tiny per-frame drag -> ball settles
ROLL_STOP_SPEED = 0.08              # below this |vx| the ball stops rolling
MIN_BOUNCE_SPEED = 3.5              # below this impact speed the bounce
                                    # becomes a rest contact (kills the
                                    # discrete micro-bounce limit cycle)

# --- colours ---------------------------------------------------------------
COLOR_BG = (16, 18, 28)
COLOR_TEXT = (230, 232, 240)
COLOR_DIM = (130, 138, 160)
COLOR_ACCENT = (86, 180, 233)
COLOR_SPRITE = (240, 110, 70)
COLOR_SHAPE_A = (86, 180, 233)
COLOR_SHAPE_B = (255, 170, 60)
COLOR_BALL = (240, 110, 70)
COLOR_FLOOR = (90, 100, 120)
COLOR_TRAIL = (120, 190, 240)


# ============================================================================
#  PURE MATH HELPERS  (no pygame calls -> trivially unit-testable)
# ============================================================================
def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation: (1 - t)*a + t*b, with t normalized to [0, 1]."""
    return (1.0 - t) * a + t * b


def lerp_point(p1: tuple[float, float], p2: tuple[float, float],
               t: float) -> tuple[float, float]:
    """LERP between two 2D points: P(t) = (1-t)*P_start + t*P_end."""
    return (lerp(p1[0], p2[0], t), lerp(p1[1], p2[1], t))


def ease_in_out(t: float) -> float:
    """Smoothstep easing: s(t) = t*t * (3 - 2t).

    Maps the normalized time t to an eased parameter with zero derivative at
    t = 0 and t = 1, giving a natural ease-in / ease-out motion.
    """
    return t * t * (3.0 - 2.0 * t)


def clamp01(t: float) -> float:
    """Clamp a value into the normalized interval [0, 1]."""
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)


def catmull_rom_point(p0, p1, p2, p3, u):
    """Catmull-Rom spline point on the P1->P2 span for u in [0, 1].

    Standard centripetal-neutral (uniform) Catmull-Rom, tension 0.5.
    """
    u2 = u * u
    u3 = u2 * u
    x = 0.5 * ((2.0 * p1[0])
               + (-p0[0] + p2[0]) * u
               + (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * u2
               + (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * u3)
    y = 0.5 * ((2.0 * p1[1])
               + (-p0[1] + p2[1]) * u
               + (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * u2
               + (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * u3)
    return (x, y)


def sample_spline(points, t):
    """Evaluate a closed-loop Catmull-Rom spline through `points` at t in [0,1).

    The path wraps around (the sprite keeps flying), which makes the looping
    animation seamless. t is normalized over the WHOLE loop.
    """
    n = len(points)
    if n < 2:
        return points[0]
    seg_f = clamp01(t) * n                # n segments in a closed loop
    seg = int(seg_f)
    u = seg_f - seg
    p0 = points[(seg - 1) % n]
    p1 = points[seg % n]
    p2 = points[(seg + 1) % n]
    p3 = points[(seg + 2) % n]
    return catmull_rom_point(p0, p1, p2, p3, u)


def split_edge(poly, edge_index):
    """Return a copy of `poly` with a duplicated midpoint vertex on one edge.

    This is the VERTEX CORRESPONDENCE RULE in action: inserting the midpoint
    of the edge between vertex `edge_index` and the next one raises the vertex
    count by one while leaving the polygon's shape unchanged.
    """
    a = poly[edge_index % len(poly)]
    b = poly[(edge_index + 1) % len(poly)]
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    return list(poly[:edge_index + 1]) + [mid] + list(poly[edge_index + 1:])


def equalize_vertex_count(poly_a, poly_b):
    """Equalize two polygons' vertex counts by subdividing the smaller one.

    Edges are split round-robin (0, 1, 2, ...) so the inserted duplicate
    vertices stay evenly distributed around the boundary. Returns
    (poly_a_equalized, poly_b_equalized).
    """
    a, b = [tuple(map(float, p)) for p in poly_a], \
           [tuple(map(float, p)) for p in poly_b]
    k = 0
    while len(a) < len(b):
        a = split_edge(a, k % len(a))
        k += 1
    k = 0
    while len(b) < len(a):
        b = split_edge(b, k % len(b))
        k += 1
    return a, b


def morph_polygon(poly_a, poly_b, t):
    """Vertex-pairing morph: V_mid(t) = (1-t)*V_A + t*V_B for every vertex.

    Both polygons must already have equal vertex counts (see
    equalize_vertex_count / the vertex correspondence rule).
    """
    assert len(poly_a) == len(poly_b), "keyframes must have equal vertex counts"
    return [lerp_point(a, b, t) for a, b in zip(poly_a, poly_b)]


# ============================================================================
#  STATE CLASSES  (update logic only - rendering happens in render functions)
# ============================================================================
@dataclass
class TweenState:
    """State of the tweening demo: progress along the path + easing style."""
    frame: int = 0
    use_ease: bool = False                       # False = pure linear LERP

    def update(self) -> None:
        """Advance the normalized cycle time. dt = 1 frame at 60 FPS."""
        self.frame = (self.frame + 1) % TWEEN_DURATION_FRAMES

    def normalized_time(self) -> float:
        """Normalized time t in [0, 1] over one traversal of the path."""
        return self.frame / (TWEEN_DURATION_FRAMES - 1)

    def sprite_position(self) -> tuple[float, float]:
        """Current sprite position on the spline for the active easing style.

        Pure linear LERP parameterizes the spline directly with t, so the
        sprite moves at constant speed per segment. Smoothstep warps the
        parameter s(t) = t*t*(3-2t) first, slowing the motion at both ends.
        """
        t = self.normalized_time()
        if self.use_ease:
            t = ease_in_out(t)
        return sample_spline(TWEEN_PATH, t)


@dataclass
class MorphState:
    """State of the morphing demo: a ping-pong parameter t in [0, 1]."""
    t: float = 0.0
    direction: int = 1                           # +1 -> toward quad, -1 -> back
    speed: float = 1.0 / 180.0                   # full morph in 3 s at 60 FPS
    poly_a: list = field(default_factory=list)
    poly_b: list = field(default_factory=list)

    def __post_init__(self) -> None:
        # VERTEX CORRESPONDENCE RULE: the triangle (3 vertices) gets one edge
        # split with an inserted midpoint duplicate so both keyframes hold 4
        # vertices and can be interpolated pairwise.
        if not self.poly_a:
            self.poly_a, self.poly_b = equalize_vertex_count(
                TRIANGLE_A, QUADRILATERAL_B)

    def update(self) -> None:
        """Ping-pong the morph parameter so the animation loops forever."""
        self.t += self.direction * self.speed
        if self.t >= 1.0:
            self.t, self.direction = 1.0, -1
        elif self.t <= 0.0:
            self.t, self.direction = 0.0, 1

    def current_polygon(self) -> list:
        """Interpolated intermediate polygon V_mid(t)."""
        return morph_polygon(self.poly_a, self.poly_b, self.t)


@dataclass
class BallState:
    """State of the bouncing ball: position, velocity, and bounce bookkeeping."""
    x: float = BALL_START[0]
    y: float = BALL_START[1]
    vx: float = -3.2
    vy: float = 0.0
    bounces: int = 0
    last_impact_speed: float = 0.0
    settled: bool = False

    def reset(self) -> None:
        """Restore the initial launch configuration (SPACE key)."""
        self.__init__()                          # type: ignore[call-arg]

    def update(self) -> None:
        """One physics step of explicit Euler integration (dt = 1 frame).

        y_next = y + v*dt      (position update)
        v_next = v + g*dt      (velocity update, gravity g = 0.5)
        On crossing the floor: v_rebound = -e * v_impact with e = 0.78,
        plus slight horizontal energy decay so the ball eventually settles.
        """
        if self.settled:
            return
        # 1) integrate position with the CURRENT velocity
        self.y += self.vy
        self.x += self.vx
        # 2) integrate velocity (gravity acts after the position step)
        self.vy += GRAVITY
        # 3) small horizontal drag (air/rolling resistance)
        self.vx *= HORIZONTAL_DRAG

        # 4) floor collision: reflect vertical velocity with restitution
        if self.y + BALL_RADIUS >= FLOOR_Y:
            self.y = FLOOR_Y - BALL_RADIUS       # resolve penetration
            impact = self.vy
            self.vy = -RESTITUTION * impact      # v_rebound = -e * v_impact
            self.bounces += 1
            self.last_impact_speed = abs(impact)
            # Kill micro-bounces: below this speed the ball rests instead.
            if abs(self.vy) < MIN_BOUNCE_SPEED:
                self.vy = 0.0
            # Kill micro-rolling as well.
            if abs(self.vx) < ROLL_STOP_SPEED:
                self.vx = 0.0
            # At rest on the floor with no motion -> settled.
            if self.vy == 0.0 and self.vx == 0.0:
                self.settled = True


# ============================================================================
#  RENDER FUNCTIONS  (all drawing lives here; update logic stays above)
# ============================================================================
def draw_hud(screen, font, small_font, mode: int, tween: TweenState,
             ball: BallState, fps_measured: float) -> None:
    """On-screen mode label, controls hint, and live dynamics readout."""
    names = {1: 'MODE 1: TWEENING (spline path + LERP / smoothstep)',
             2: 'MODE 2: MORPHING (triangle -> quadrilateral)',
             3: 'MODE 3: DYNAMICS (bouncing ball, gravity + restitution)'}
    pygame.display.set_caption(CAPTION)
    title = font.render(CAPTION, True, COLOR_ACCENT)
    screen.blit(title, title.get_rect(topleft=(16, 10)))
    label = font.render(names[mode], True, COLOR_TEXT)
    screen.blit(label, label.get_rect(topleft=(16, 40)))

    if mode == 1:
        style = 'ease-in/ease-out (smoothstep)' if tween.use_ease \
            else 'pure linear (LERP)'
        hint = small_font.render(
            f"interpolation: {style}   [L]inear / [E]ase toggle", True,
            COLOR_DIM)
        screen.blit(hint, hint.get_rect(topleft=(16, 66)))
    elif mode == 2:
        hint = small_font.render(
            'vertex correspondence: triangle edge split -> 4 vertices each; '
            'ping-pong morph loop', True, COLOR_DIM)
        screen.blit(hint, hint.get_rect(topleft=(16, 66)))
    else:
        v = math.hypot(ball.vx, ball.vy)
        lines = (
            f"position: ({ball.x:7.1f}, {ball.y:7.1f})",
            f"velocity: vx={ball.vx:6.2f}  vy={ball.vy:6.2f}  |v|={v:6.2f} px/frame",
            f"bounces: {ball.bounces}   last |v_impact|={ball.last_impact_speed:5.2f}"
            f"   e={RESTITUTION}   g={GRAVITY}"
            + ("   [SETTLED]" if ball.settled else ""),
            "press SPACE to relaunch the ball",
        )
        for i, txt in enumerate(lines):
            surf = small_font.render(txt, True, COLOR_TEXT if i == 1 else COLOR_DIM)
            screen.blit(surf, surf.get_rect(topleft=(16, 66 + 20 * i)))

    fps_surf = small_font.render(f"FPS: {fps_measured:5.1f}", True, COLOR_DIM)
    screen.blit(fps_surf, fps_surf.get_rect(topright=(SCREEN_WIDTH - 14, 12)))
    keys = small_font.render("[1][2][3] switch mode   [ESC] quit", True,
                             COLOR_DIM)
    screen.blit(keys, keys.get_rect(bottomright=(SCREEN_WIDTH - 14,
                                                 SCREEN_HEIGHT - 10)))


def render_tween(screen, tween: TweenState) -> None:
    """Draw the spline path, waypoints, and the tweened sprite."""
    # faint trail of sampled spline points
    pts = [sample_spline(TWEEN_PATH, i / 400.0) for i in range(400)]
    for i in range(len(pts) - 1):
        pygame.draw.line(screen, (40, 60, 90), pts[i], pts[i + 1], 2)
    # waypoints
    for i, wp in enumerate(TWEEN_PATH):
        pygame.draw.circle(screen, COLOR_ACCENT, wp, 5)
        num = pygame.font.Font(None, 20).render(str(i + 1), True, COLOR_DIM)
        screen.blit(num, num.get_rect(center=(wp[0], wp[1] - 14)))
    # the moving sprite
    x, y = tween.sprite_position()
    pygame.draw.circle(screen, COLOR_SPRITE, (int(x), int(y)), SPRITE_RADIUS)
    pygame.draw.circle(screen, (255, 220, 200), (int(x) - 5, int(y) - 5), 5)


def render_morph(screen, morph: MorphState, font) -> None:
    """Draw both keyframes ghosted plus the live interpolated polygon."""
    # keyframe A (triangle, after equalization it has 4 vertices as well)
    for poly, color, label in ((morph.poly_a, COLOR_SHAPE_A, 'keyframe A'),
                               (morph.poly_b, COLOR_SHAPE_B, 'keyframe B')):
        ghost = [(int(px), int(py)) for px, py in poly]
        pygame.draw.lines(screen, color, True, ghost, 1)
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        lab = pygame.font.Font(None, 22).render(label, True, color)
        screen.blit(lab, lab.get_rect(center=(cx, cy)))
    # the live morph target
    verts = [(int(px), int(py)) for px, py in morph.current_polygon()]
    pygame.draw.polygon(screen, (200, 120, 160), verts)
    pygame.draw.polygon(screen, COLOR_TEXT, verts, 2)
    # show the interpolated vertices
    for v in verts:
        pygame.draw.circle(screen, COLOR_TEXT, v, 3)
    pct = pygame.font.Font(None, 26).render(f"t = {morph.t:.3f}", True,
                                            COLOR_TEXT)
    screen.blit(pct, pct.get_rect(topleft=(16, SCREEN_HEIGHT - 60)))
    va = pygame.font.Font(None, 22).render(
        f"A: {len(TRIANGLE_A)} vertices -> split -> {len(morph.poly_a)}",
        True, COLOR_DIM)
    screen.blit(va, va.get_rect(topleft=(16, SCREEN_HEIGHT - 36)))
    vb = pygame.font.Font(None, 22).render(
        f"B: {len(QUADRILATERAL_B)} vertices (quadrilateral)", True, COLOR_DIM)
    screen.blit(vb, vb.get_rect(topleft=(240, SCREEN_HEIGHT - 36)))


def render_dynamics(screen, ball: BallState, font) -> None:
    """Draw the floor, walls, the ball, and its velocity vector."""
    pygame.draw.rect(screen, COLOR_FLOOR,
                     (0, int(FLOOR_Y), SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
    pygame.draw.line(screen, (200, 210, 230), (0, FLOOR_Y),
                     (SCREEN_WIDTH, FLOOR_Y), 3)
    # wall reflections keep the ball inside the window
    pygame.draw.line(screen, COLOR_FLOOR, (0, 0), (0, SCREEN_HEIGHT), 4)
    pygame.draw.line(screen, COLOR_FLOOR, (SCREEN_WIDTH, 0),
                     (SCREEN_WIDTH, SCREEN_HEIGHT), 4)
    # velocity vector (visualizes the live readout)
    scale = 6.0
    tip = (int(ball.x + ball.vx * scale), int(ball.y + ball.vy * scale))
    pygame.draw.line(screen, COLOR_ACCENT, (ball.x, ball.y), tip, 2)
    pygame.draw.circle(screen, COLOR_BALL,
                       (int(ball.x), int(ball.y)), BALL_RADIUS)
    pygame.draw.circle(screen, (255, 220, 200),
                       (int(ball.x) - 7, int(ball.y) - 7), 6)
    readout = font.render(f"|v| = {math.hypot(ball.vx, ball.vy):.2f}", True,
                          COLOR_ACCENT)
    screen.blit(readout, readout.get_rect(topleft=(int(ball.x) + 30,
                                                   int(ball.y) - 10)))


# ============================================================================
#  SELF-TESTS  (pure math verification, runnable without any display)
# ============================================================================
def run_self_tests() -> None:
    """Assert the core mathematics used by all three modes.

    LERP midpoint, morph midpoint vertices, and the restitution law
    v_rebound = -e * v_impact are all verified with exact numeric checks.
    """
    # --- 1. LERP midpoint: P(0.5) must be exactly the midpoint -------------
    assert lerp(0.0, 10.0, 0.5) == 5.0
    assert lerp_point((0, 0), (100, 200), 0.5) == (50.0, 100.0)
    assert lerp(2.0, 4.0, 0.0) == 2.0 and lerp(2.0, 4.0, 1.0) == 4.0

    # --- 2. smoothstep endpoints and midpoint -------------------------------
    assert ease_in_out(0.0) == 0.0
    assert ease_in_out(1.0) == 1.0
    assert abs(ease_in_out(0.5) - 0.5) < 1e-12

    # --- 3. vertex correspondence rule --------------------------------------
    tri, quad = equalize_vertex_count(TRIANGLE_A, QUADRILATERAL_B)
    assert len(tri) == len(quad) == 4
    # the split edge midpoint must lie exactly halfway between its endpoints
    assert tri[1] == ((TRIANGLE_A[0][0] + TRIANGLE_A[1][0]) / 2.0,
                      (TRIANGLE_A[0][1] + TRIANGLE_A[1][1]) / 2.0)
    # splitting the same polygon twice must double its vertex count
    tri3 = split_edge(TRIANGLE_A, 0)
    assert len(tri3) == 4
    assert tri3[1] == tri[1]                 # same edge (0->1) -> same midpoint

    # --- 4. morph midpoint vertices ------------------------------------------
    mid = morph_polygon(tri, quad, 0.5)
    for m, a, b in zip(mid, tri, quad):
        assert m == ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    # at t = 0 and t = 1 the morph reproduces the exact keyframes
    assert morph_polygon(tri, quad, 0.0) == tri
    assert morph_polygon(tri, quad, 1.0) == quad

    # --- 5. restitution: v_rebound must equal -e * v_impact ------------------
    ball = BallState()
    ball.y = FLOOR_Y - BALL_RADIUS           # resting exactly on the floor
    ball.vy = 10.0                           # downward impact speed 10 px/frame
    ball.update()                            # gravity is applied first, then
                                             # the collision check, so the true
                                             # impact speed is 10 + g = 10.5
    # restitution law: v_rebound = -e * v_impact (checked on the recorded
    # impact speed, which includes the gravity added in the same frame)
    assert ball.vy == -RESTITUTION * ball.last_impact_speed
    assert abs(ball.last_impact_speed - 10.5) < 1e-9
    assert ball.vy < 0                       # rebound points upward

    # --- 6. Euler gravity integration: v grows by g per frame ----------------
    b = BallState()
    b.vy = 0.0
    b.y = 0.0                                # far above the floor
    b.update()
    assert b.vy == GRAVITY                   # v_next = v + g*dt, dt = 1
    assert b.y == 0.0                        # y_next = y + v*dt with v = 0

    # --- 7. spline passes through its waypoints at segment boundaries --------
    for i, wp in enumerate(TWEEN_PATH):
        t = i / len(TWEEN_PATH)              # closed loop: n segments
        s = sample_spline(TWEEN_PATH, t)
        assert abs(s[0] - wp[0]) < 1e-6 and abs(s[1] - wp[1]) < 1e-6

    print('All self-tests passed: LERP, smoothstep, vertex correspondence, '
          'morph midpoint, Euler gravity, restitution.')


# ============================================================================
#  MAIN LOOP
# ============================================================================
def main() -> None:
    """Input -> Update -> Render -> FPS regulation, at 60 FPS."""
    run_self_tests() if '--selftest' in sys.argv else None

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(CAPTION)
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 30)
    small_font = pygame.font.Font(None, 22)

    mode = 1                                  # start in tweening mode
    tween = TweenState()
    morph = MorphState()
    ball = BallState()
    fps_measured = FPS

    running = True
    while running:
        # ---------------- INPUT ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    mode = 1
                elif event.key == pygame.K_2:
                    mode = 2
                elif event.key == pygame.K_3:
                    mode = 3
                elif event.key == pygame.K_l and mode == 1:
                    tween.use_ease = False
                elif event.key == pygame.K_e and mode == 1:
                    tween.use_ease = True
                elif event.key == pygame.K_SPACE and mode == 3:
                    ball.reset()

        # ---------------- UPDATE (physics / animation state only) ------------
        if mode == 1:
            tween.update()
        elif mode == 2:
            morph.update()
        else:
            ball.update()
            # keep the ball inside the side walls
            if ball.x - BALL_RADIUS < 0:
                ball.x, ball.vx = BALL_RADIUS, abs(ball.vx)
            elif ball.x + BALL_RADIUS > SCREEN_WIDTH:
                ball.x = SCREEN_WIDTH - BALL_RADIUS
                ball.vx = -abs(ball.vx)

        # ---------------- RENDER ----------------
        screen.fill(COLOR_BG)
        if mode == 1:
            render_tween(screen, tween)
        elif mode == 2:
            render_morph(screen, morph, font)
        else:
            render_dynamics(screen, ball, font)
        draw_hud(screen, font, small_font, mode, tween, ball, fps_measured)
        pygame.display.flip()

        # ---------------- FPS REGULATION ----------------
        fps_measured = clock.get_fps() or FPS
        clock.tick(FPS)

    pygame.quit()


if __name__ == '__main__':
    main()
