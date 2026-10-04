# Activity 4 Technical Write-Up
## 3D Projection Engine: Orthographic, Oblique (Cavalier / Cabinet) & Perspective

**File:** `activity_4.py` (standalone, Python 3.10+, pygame 2.1+)
**Run:** `python activity_4.py` | **Headless self-test:** `python activity_4.py --selftest`

## 1. Overview

The program renders a wireframe cube (8 vertices, 12 edges, centered at the origin)
and switches live between four projection modes with keys **1-4**. Rotation
matrices around the X, Y, and Z axes are applied to the vertices **before**
projection, so every mode renders the currently rotated mesh. The projected
image is centered on the 800x600 window with the **+400, +300** screen offset
used in the lab starter template. The loop runs at 60 FPS via `pygame.time.Clock.tick(60)`.

## 2. Projection Mathematics

All projections map a world vertex (x, y, z) to view-plane coordinates (x_p, y_p);
the screen offset (+400, +300) is applied once, in `project_to_screen()`.

**1. Orthographic (parallel, view-plane normal = z):**

    x_p = x,  y_p = y      (z discarded)

**2. Oblique (Cavalier / Cabinet), direction of projection (DOP) at angle phi:**

    x_p = x + z * L1 * cos(phi)
    y_p = y + z * L1 * sin(phi)

    Cavalier: phi = 45 deg  -> L1 = 1/tan(45)  = 1.0  (no depth foreshortening)
    Cabinet:  phi = 63.4 deg -> L1 = 1/tan(63.4) = 0.5 (depth foreshortened 50%)

**3. One-point perspective**, with D = distance from the Center of Projection to
the view plane (default 400):

    x_p = x * D / (z + D),  y_p = y * D / (z + D)

Derivation: with the view plane at z = 0 and the center of projection at
(0, 0, -D), the ray from (0, 0, -D) through (x, y, z) crosses z = 0 at the
parameter t = D/(z + D), which yields the formulas above. The case z + D = 0
(a vertex exactly on the plane through the center of projection) is guarded in
`project_perspective()` with a signed epsilon, so no division by zero or
non-finite coordinates can occur (verified by assert).

## 3. Architecture: Oblique Front-Face Rule

The lab manual's architectural rule states that in oblique projection the front
face parallel to the view plane keeps true shape and scale, and distortion occurs
only along the receding z-axis. The code makes this structurally true: the depth
term `z * L1 * (cos phi, sin phi)` vanishes exactly when z = 0, so every point of
the front face (z = -100 face of the unrotated cube, and any face brought to the
view plane by rotation) projects to precisely (x, y), i.e. the orthographic
result. The shear (phi) and depth scale (L1) affect only the z coordinate.
Cabinet projection applies the same shear but halves the depth term (L1 = 0.5),
which is why its receding edges are exactly half as long as Cavalier's for the
same phi.

## 4. 3D Rotation (Task 4.2)

Rotation matrices Rx, Ry, Rz are built from the angle each frame and composed as
`Rz * Ry * Rx`, applied to all 8 vertices before projection:

    Rx = [[1,0,0],[0,cos a,-sin a],[0,sin a,cos a]]
    Ry = [[cos a,0,sin a],[0,1,0],[-sin a,0,cos a]]
    Rz = [[cos a,-sin a,0],[sin a,cos a,0],[0,0,1]]

Controls (smooth, per-frame increments of 1.5 deg while held):
Arrow Up/Down rotate X, Arrow Left/Right rotate Y, Q/E rotate Z,
R resets the rotation, ESC quits, keys 1-4 switch projection mode.

## 5. Wireframe Rendering & Vanishing Point (Tasks 4.1, 4.4)

Edges are rasterized with `pygame.draw.line` between projected 2D coordinates,
and each projected vertex is drawn as a small circle; the front face edges are
highlighted so the true-shape face is identifiable in the oblique modes.

In perspective mode the four z-parallel edges are extended as dashed lines
toward their shared vanishing point, which is marked with a red circle labeled
"Vanishing Point". The point is computed from the world-space direction (dx, dy, dz)
of the edges: a line p(t) = p0 + t*dir under x_p = x*D/(z+D) converges to
(D*dx/dz, D*dy/dz) as t -> inf, i.e. the projection of the point at infinity
along that direction. For the z-parallel edges of the unrotated cube this is
the screen center (400, 300). When the rotated edges become parallel to the
view plane (dz ~ 0) they stay parallel and no finite vanishing point exists;
the extension is skipped. The dashed extension is length-capped so off-screen
VPs cannot stall rendering.

## 6. Verification (headless, `--selftest`)

Run with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`; executes 360 simulated
frames (several hundred) applying continuous rotation through all four modes,
then asserts:

1. **Orthographic** leaves (x, y) unchanged for sampled vertices.
2. **Cabinet** depth contribution is exactly half of Cavalier's for the same phi
   (checked for z in {-100, -37.5, 0, 63.5, 100}), and L1 constants match
   1/tan(DOP angle) for 45 deg and 63.4 deg.
3. **Perspective** maps any point with z = 0 to itself ((z + D) = D cancels),
   and z = -D does not raise and produces finite coordinates.
4. **Vanishing point** of the z-parallel edges is the screen center (400, 300);
   a direction with dz = 0 correctly yields no finite VP.
5. **Screen bounds:** every projected vertex of the rotated cube stays within
   0 <= x < 800 and 0 <= y < 600, for all four modes, across all 360 frames.

Result: `SELF-TEST PASSED: 360 frames x 4 modes, all asserts OK.`
Four frame captures were saved with `pygame.image.save`, one per mode:
`captures/mode1_orthographic.png`, `captures/mode2_cavalier.png`,
`captures/mode3_cabinet.png`, `captures/mode4_perspective.png`.
The file runs unchanged on a real desktop (`python activity_4.py`); the dummy
video drivers are only set inside the self-test path.

## 7. Observed Differences Between Modes

- **Orthographic:** parallel cube edges stay parallel; depth is invisible
  (front and back faces draw at identical scale when unrotated).
- **Cavalier:** receding edges drawn at full length along the 45 deg DOP, so the
  cube looks elongated in depth.
- **Cabinet:** identical shear direction but receding edges at half length,
  giving the more natural-looking depth.
- **Perspective:** all four z-parallel edges converge at the marked vanishing
  point; the back face (z = +100) projects smaller than the front face (z = -100).
