"""
Activity 4: Software 3D Projection Pipeline in Pygame
=====================================================
3D Projection Engine: Orthographic, Oblique (Cavalier / Cabinet) & Perspective.

Renders a wireframe cube (8 vertices, 12 edges) centered at the origin and
switches live between four projection modes with keys 1-4:

    1. Orthographic          x_p = x,                y_p = y           (z discarded)
    2. Cavalier oblique      x_p = x + z*L1*cos(phi), y_p = y + z*L1*sin(phi)
                             DOP angle 45 deg  -> L1 = 1/tan(45)  = 1.0 (no depth foreshortening)
    3. Cabinet oblique       same formula, DOP angle 63.4 deg -> L1 = 1/tan(63.4) = 0.5
                             (depth foreshortened by 50%)
    4. One-point perspective x_p = x*D/(z+D), y_p = y*D/(z+D), D = distance from
                             the Center of Projection to the view plane (default 400).

Real-time rotation matrices around X, Y, Z are applied to the vertices BEFORE
projection. In perspective mode the four z-parallel edges are extended toward
their shared vanishing point, which is marked on screen.

ARCHITECTURAL RULE (lab manual, sec. 4.4): in oblique projection the front face
of an object oriented parallel to the view plane keeps its true shape and
scale; distortion occurs only along the receding z-axis. This is visible in
the code: the oblique formulas add a depth term ONLY to the projected
coordinates through z * L1 * (cos phi, sin phi); a point with z = 0 (the front
face) projects to exactly (x, y), identical to the orthographic result.

Run on a desktop:      python activity_4.py
Headless self-test:    python activity_4.py --selftest
                       (math asserts + saves one PNG capture per mode to
                        activity_4_projections/captures/)

Requires Python 3.10+ and pygame 2.1+. No other dependencies.
"""

from __future__ import annotations

import math
import os
import sys

import pygame

# ----------------------------------------------------------------------------
# Window / rendering constants
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
CENTER_X, CENTER_Y = 400, 300          # screen offset that centers the projection
FPS = 60

EDGE_COLOR = (240, 240, 240)
FRONT_FACE_COLOR = (80, 200, 255)      # edges of the front face (z = -100)
VERTEX_COLOR = (255, 210, 70)
VANISHING_COLOR = (255, 80, 80)
HUD_COLOR = (180, 180, 200)

# ----------------------------------------------------------------------------
# Cube mesh: 8 vertices (x, y, z) centered at the origin, 12 edges
# ----------------------------------------------------------------------------
CUBE_VERTICES: list[tuple[float, float, float]] = [
    (-100.0, -100.0, -100.0),
    ( 100.0, -100.0, -100.0),
    ( 100.0,  100.0, -100.0),
    (-100.0,  100.0, -100.0),
    (-100.0, -100.0,  100.0),
    ( 100.0, -100.0,  100.0),
    ( 100.0,  100.0,  100.0),
    (-100.0,  100.0,  100.0),
]
CUBE_EDGES: list[tuple[int, int]] = [
    (0, 1), (1, 2), (2, 3), (3, 0),        # front face (z = -100)
    (4, 5), (5, 6), (6, 7), (7, 4),        # back face  (z = +100)
    (0, 4), (1, 5), (2, 6), (3, 7),        # the four z-parallel edges
]
Z_PARALLEL_EDGES = [(0, 4), (1, 5), (2, 6), (3, 7)]

# ----------------------------------------------------------------------------
# Projection parameters
# ----------------------------------------------------------------------------
PERSPECTIVE_D = 400.0                   # Center-of-Projection to view-plane distance
CAVALIER_PHI_DEG = 45.0                 # direction-of-projection angle
CAVALIER_L1 = 1.0                       # = 1/tan(45 deg): no depth foreshortening
CABINET_PHI_DEG = 63.4                  # direction-of-projection angle
CABINET_L1 = 0.5                        # = 1/tan(63.4 deg): depth halved

ROT_SPEED_DEG_PER_FRAME = 1.5           # smooth rotation while a key is held

MODE_NAMES = [
    "1: Orthographic",
    "2: Cavalier Oblique (DOP 45 deg, L1 = 1.0)",
    "3: Cabinet Oblique (DOP 63.4 deg, L1 = 0.5)",
    "4: One-Point Perspective (D = 400)",
]


# ----------------------------------------------------------------------------
# 3D rotation matrices (applied to vertices BEFORE projection)
# ----------------------------------------------------------------------------
def rotation_matrix_x(deg: float) -> tuple[tuple[float, ...], ...]:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0),
            (0, c, -s),
            (0, s, c))


def rotation_matrix_y(deg: float) -> tuple[tuple[float, ...], ...]:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s),
            (0, 1, 0),
            (-s, 0, c))


def rotation_matrix_z(deg: float) -> tuple[tuple[float, ...], ...]:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0),
            (s, c, 0),
            (0, 0, 1))


def mat_vec_mul(m, v):
    return tuple(sum(m[r][c] * v[c] for c in range(3)) for r in range(3))


def rotate_vertex(vertex, rx: float, ry: float, rz: float):
    """Apply Rz * Ry * Rx to a single (x, y, z) vertex."""
    v = mat_vec_mul(rotation_matrix_x(rx), vertex)
    v = mat_vec_mul(rotation_matrix_y(ry), v)
    v = mat_vec_mul(rotation_matrix_z(rz), v)
    return v


def rotate_all(vertices, rx: float, ry: float, rz: float):
    return [rotate_vertex(v, rx, ry, rz) for v in vertices]


# ----------------------------------------------------------------------------
# Projection functions (each returns UNCENTERED (x_p, y_p) floats; the +400/+300
# screen offset is applied once in project_to_screen so the math stays clean)
# ----------------------------------------------------------------------------
def project_orthographic(x: float, y: float, z: float) -> tuple[float, float]:
    """Orthographic parallel projection: drop z, keep (x, y) unchanged."""
    return x, y


def project_oblique(x: float, y: float, z: float,
                    phi_deg: float, l1: float) -> tuple[float, float]:
    """Oblique parallel projection.

    x_p = x + z * L1 * cos(phi)
    y_p = y + z * L1 * sin(phi)

    ARCHITECTURAL RULE: the depth term vanishes when z = 0, so the face
    parallel to the view plane projects at true shape and scale; only the
    receding z-axis is sheared (by phi) and scaled (by L1).
    """
    phi = math.radians(phi_deg)
    xp = x + z * l1 * math.cos(phi)
    yp = y + z * l1 * math.sin(phi)
    return xp, yp


def project_perspective(x: float, y: float, z: float,
                        d: float = PERSPECTIVE_D) -> tuple[float, float]:
    """One-point perspective: x_p = x*D/(z+D), y_p = y*D/(z+D).

    The (z + D) == 0 case (vertex exactly on the center of projection plane)
    is guarded with a tiny epsilon so the pipeline never divides by zero.
    """
    distance = z + d
    if abs(distance) < 1e-9:
        distance = 1e-9 if distance >= 0 else -1e-9
    xp = (x * d) / distance
    yp = (y * d) / distance
    return xp, yp


def project_vertex(vertex, mode: int):
    x, y, z = vertex
    if mode == 0:
        return project_orthographic(x, y, z)
    if mode == 1:
        return project_oblique(x, y, z, CAVALIER_PHI_DEG, CAVALIER_L1)
    if mode == 2:
        return project_oblique(x, y, z, CABINET_PHI_DEG, CABINET_L1)
    return project_perspective(x, y, z, PERSPECTIVE_D)


def project_to_screen(vertex, mode: int) -> tuple[int, int]:
    """Project a world vertex and center it on the screen (+400, +300)."""
    xp, yp = project_vertex(vertex, mode)
    return int(xp + CENTER_X), int(yp + CENTER_Y)


def vanishing_point(direction, d: float = PERSPECTIVE_D):
    """Screen location where world lines parallel to `direction` converge.

    A line p(t) = p0 + t*dir under x_p = x*D/(z+D) tends to
    (D*dx/dz, D*dy/dz) as t -> +/-inf, so the vanishing point is the
    projection of the point at infinity along that direction. For the
    unrotated cube the z-parallel edges share VP = (D*0/1, D*0/1), i.e. the
    screen center (400, 300). Returns None when the direction is parallel to
    the view plane (dz == 0): such lines stay parallel and have no finite VP.
    """
    dx, dy, dz = direction
    if abs(dz) < 1e-9:
        return None
    return (CENTER_X + d * dx / dz, CENTER_Y + d * dy / dz)


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def draw_wireframe(screen, projected):
    for i, j in CUBE_EDGES:
        color = FRONT_FACE_COLOR if (i, j) in ((0, 1), (1, 2), (2, 3), (3, 0)) else EDGE_COLOR
        pygame.draw.line(screen, color, projected[i], projected[j], 2)
    for px, py in projected:
        pygame.draw.circle(screen, VERTEX_COLOR, (px, py), 4)


def draw_dashed_line(screen, color, start, end, dash_len=12.0, gap_len=8.0, max_len=None):
    """Dashed line that stays bounded even when `end` sits far off-screen."""
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    if max_len is not None:
        length = min(length, max_len)
    ux, uy = dx / length, dy / length
    t = 0.0
    while t < length:
        t2 = min(t + dash_len, length)
        p1 = (sx + ux * t, sy + uy * t)
        p2 = (sx + ux * t2, sy + uy * t2)
        pygame.draw.line(screen, color, p1, p2, 1)
        t = t2 + gap_len


def draw_perspective_aids(screen, rotated_vertices):
    """Extend the four z-parallel edges toward their shared vanishing point.

    The VP is computed from the WORLD direction of the edges (so it stays
    correct even while the cube rotates): VP = (CENTER + D*dx/dz, CENTER +
    D*dy/dz). When dz ~ 0 the edges are parallel to the view plane and no
    finite vanishing point exists; the extension is skipped.
    """
    a, b = Z_PARALLEL_EDGES[0]
    direction = (rotated_vertices[b][0] - rotated_vertices[a][0],
                 rotated_vertices[b][1] - rotated_vertices[a][1],
                 rotated_vertices[b][2] - rotated_vertices[a][2])
    vp = vanishing_point(direction)
    if vp is None:
        return None
    projected = [project_to_screen(v, 3) for v in rotated_vertices]
    for a, b in Z_PARALLEL_EDGES:
        # extend from the more distant endpoint of the edge toward the VP
        start = a if rotated_vertices[a][2] > rotated_vertices[b][2] else b
        draw_dashed_line(screen, VANISHING_COLOR, projected[start], vp, max_len=1400.0)
    if 0 <= vp[0] < WIDTH and 0 <= vp[1] < HEIGHT:
        pygame.draw.circle(screen, VANISHING_COLOR, (int(vp[0]), int(vp[1])), 6, 2)
        pygame.draw.circle(screen, VANISHING_COLOR, (int(vp[0]), int(vp[1])), 1)
    return vp


def draw_hud(screen, font, mode: int, fps: float):
    lines = [
        MODE_NAMES[mode],
        "Arrow Up/Down: rotate X   Arrow Left/Right: rotate Y   Q/E: rotate Z",
        "1-4: projection mode   R: reset rotation   ESC: quit",
        f"FPS: {fps:5.1f}",
    ]
    for i, text in enumerate(lines):
        screen.blit(font.render(text, True, HUD_COLOR), (12, 10 + i * 22))


# ----------------------------------------------------------------------------
# Main loop (desktop)
# ----------------------------------------------------------------------------
def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Activity 4: 3D Projection Engine (Ortho / Cavalier / Cabinet / Perspective)")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    mode = 0
    rx = ry = rz = 0.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= event.key <= pygame.K_4:
                    mode = event.key - pygame.K_1
                elif event.key == pygame.K_r:
                    rx = ry = rz = 0.0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            rx -= ROT_SPEED_DEG_PER_FRAME
        if keys[pygame.K_DOWN]:
            rx += ROT_SPEED_DEG_PER_FRAME
        if keys[pygame.K_LEFT]:
            ry -= ROT_SPEED_DEG_PER_FRAME
        if keys[pygame.K_RIGHT]:
            ry += ROT_SPEED_DEG_PER_FRAME
        if keys[pygame.K_q]:
            rz -= ROT_SPEED_DEG_PER_FRAME
        if keys[pygame.K_e]:
            rz += ROT_SPEED_DEG_PER_FRAME

        rotated = rotate_all(CUBE_VERTICES, rx, ry, rz)
        projected = [project_to_screen(v, mode) for v in rotated]

        screen.fill((18, 18, 28))
        if mode == 3:
            vp = draw_perspective_aids(screen, rotated)
            if vp is not None and 0 <= vp[0] < WIDTH and 0 <= vp[1] < HEIGHT:
                label = font.render("Vanishing Point", True, VANISHING_COLOR)
                lx = min(max(int(vp[0]) + 10, 4), WIDTH - label.get_width() - 4)
                screen.blit(label, (lx, int(vp[1]) - 8))
        draw_wireframe(screen, projected)
        draw_hud(screen, font, mode, clock.get_fps())

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


# ----------------------------------------------------------------------------
# Headless self-test: math asserts + frame-capture PNGs (no display needed)
# ----------------------------------------------------------------------------
def run_selftest(frames: int = 360) -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.Font(None, 24)

    # ---- math verification -------------------------------------------------
    # 1) Orthographic leaves x, y unchanged.
    for v in ((37.0, -21.0, 90.0), (-100.0, 100.0, -100.0)):
        xp, yp = project_orthographic(*v)
        assert (xp, yp) == (v[0], v[1]), f"orthographic moved x,y for {v}"

    # 2) Cabinet depth contribution is exactly half of Cavalier's at same phi.
    for z in (-100.0, -37.5, 0.0, 63.5, 100.0):
        cx, cy = project_oblique(0.0, 0.0, z, 45.0, CAVALIER_L1)
        bx, by = project_oblique(0.0, 0.0, z, 45.0, CABINET_L1)
        assert math.isclose(bx, cx / 2) and math.isclose(by, cy / 2), \
            "cabinet is not half of cavalier for the same phi"
    # L1 constants match 1/tan(DOP angle).
    assert math.isclose(CAVALIER_L1, 1.0 / math.tan(math.radians(45.0)))
    assert math.isclose(CABINET_L1, 1.0 / math.tan(math.radians(63.4)), abs_tol=5e-3)

    # 3) Perspective: a point with z = 0 maps to itself (z+D = D cancels).
    for x, y in ((0.0, 0.0), (123.0, -77.0), (-100.0, 100.0)):
        xp, yp = project_perspective(x, y, 0.0)
        assert math.isclose(xp, x) and math.isclose(yp, y), "perspective z=0 != identity"
    # Guard: z + D == 0 must not raise or produce inf/nan.
    xp, yp = project_perspective(50.0, -50.0, -PERSPECTIVE_D)
    assert all(math.isfinite(t) for t in (xp, yp))

    # 4) Vanishing point of the unrotated z-parallel edges is the screen center.
    vp = vanishing_point((0.0, 0.0, 1.0))
    assert vp == (CENTER_X, CENTER_Y), f"unexpected VP {vp}"
    assert vanishing_point((1.0, 0.0, 0.0)) is None  # dz == 0 -> no finite VP

    # 5) Every projected (rotated) cube vertex stays within screen bounds,
    #    for all four modes, across several hundred simulated frames.
    rx = ry = rz = 0.0
    for frame in range(frames):
        rx += 0.37
        ry += 0.53
        rz += 0.11
        rotated = rotate_all(CUBE_VERTICES, rx, ry, rz)
        for m in range(4):
            for v in rotated:
                sx, sy = project_to_screen(v, m)
                assert 0 <= sx < WIDTH and 0 <= sy < HEIGHT, \
                    f"vertex outside screen: mode {m}, frame {frame}, ({sx}, {sy})"

    # ---- frame captures: one PNG per projection mode ------------------------
    rx, ry, rz = 20.0, -30.0, 10.0          # a pleasant fixed orientation
    rotated = rotate_all(CUBE_VERTICES, rx, ry, rz)
    capture_names = ["mode1_orthographic.png", "mode2_cavalier.png",
                     "mode3_cabinet.png", "mode4_perspective.png"]
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "captures")
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for m in range(4):
        projected = [project_to_screen(v, m) for v in rotated]
        screen.fill((18, 18, 28))
        if m == 3:
            draw_perspective_aids(screen, rotated)
        draw_wireframe(screen, projected)
        draw_hud(screen, font, m, FPS)
        path = os.path.join(out_dir, capture_names[m])
        pygame.image.save(screen, path)
        saved.append(path)

    pygame.quit()
    print(f"SELF-TEST PASSED: {frames} frames x 4 modes, all asserts OK.")
    for p in saved:
        print(f"  captured: {p}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        run_selftest()
    else:
        main()
