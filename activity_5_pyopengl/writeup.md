# Activity 5: Hardware Graphics Pipeline & Shading with PyOpenGL

**Deliverable:** `activity_5.py` (standalone Python file)
**Stack:** Python 3.10+, pygame 2.1+, PyOpenGL 3.1+

## What the program does

A single 800x600 double-buffered OpenGL window renders three coexisting
objects driven by one game loop:

1. **Solid colored cube (Task 5.2)** - the six `GL_QUADS` faces built from
   the manual's vertex, color, and surface tables, with one distinct color
   per vertex applied through `glColor3fv()` + `glVertex3fv()`.
2. **Articulated arm (Task 5.3)** - a two-segment hierarchical arm
   (shoulder -> elbow -> hand) modeled with nested `glPushMatrix()` /
   `glPopMatrix()` blocks, `glTranslatef()` to hop between joints, and
   `glRotatef()` about Z at each joint.
3. **Alpha blending demo (Task 5.4)** - two overlapping semi-transparent
   quads blended with `glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)`.

## How each required technique is implemented

### Task 5.1 - OpenGL context and pipeline setup

The context is created with `pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)`,
then `setup_gl()` configures the fixed-function pipeline exactly as the
manual prescribes:

| Call | Purpose |
| --- | --- |
| `gluPerspective(45, 800/600, 0.1, 50.0)` | 45-degree perspective frustum, near 0.1 / far 50.0, correct aspect ratio |
| `glTranslatef(0.0, 0.0, -5.0)` | push the scene 5 units into the screen |
| `glEnable(GL_DEPTH_TEST)` | z-buffer hidden-surface removal |

`glViewport` is set to the full window and the projection matrix is loaded
before the frustum is defined, so the aspect ratio matches the 800x600 window.

### Task 5.2 - Solid cube with per-vertex colors

`draw_colored_cube()` opens a `glBegin(GL_QUADS)` block and walks the
manual's `surfaces` table (6 faces x 4 vertex indices), issuing
`glColor3fv(colors[i])` immediately before each `glVertex3fv(vertices[i])`.
Because colors are set per-vertex, Gouraud interpolation blends colors
across each face, and depth testing resolves the visible faces correctly.

### Task 5.3 - Continuous rotation and the articulated arm

- **Cube rotation:** every frame adds a small increment to `spin_y`
  (auto-rotation, toggle with SPACE) and the cube is spun with
  `glRotatef(spin_y, 0, 1, 0)` / `glRotatef(spin_x, 1, 0, 0)`. The arrow
  keys override the auto-rotation manually.
- **Arm hierarchy:** `draw_arm()` nests three matrix levels:

  ```
  push  translate to shoulder joint        (world -> shoulder frame)
        rotate shoulder angle about Z
          draw upper arm segment
          push  translate (0, 1.5, 0)      (shoulder -> elbow)
                rotate elbow angle about Z
                  draw forearm segment
                  push  translate (0, 1.2, 0)   (elbow -> hand)
                        draw hand quad
                  pop
          pop
  pop
  ```

  Each `glPopMatrix()` returns the modelview to exactly the state before
  the matching `glPushMatrix()`, which is what makes hierarchical
  transforms composable: rotating the shoulder carries the elbow and hand
  with it, while rotating the elbow affects only the forearm and hand.
  The joints are driven by sinusoidal functions of wall-clock time
  (`math.sin(time.time() * ...)`), so the arm animates smoothly and
  frame-rate independently. Keys J (toggle animation), K and L (elbow
  plus/minus 10 degrees) and A (show/hide the whole arm) control it.

### Task 5.4 - Alpha blending

Blending is enabled once at startup:

```python
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
```

`draw_blending_demo()` then draws a red quad with alpha 0.5 overlapping a
blue quad with alpha 1.0, offset in x/y/z so their projections intersect.
This realizes the manual's equation `I = a1*I1 + a2*I2` (with
`a2 = 1 - a1`): each red fragment contributes 50% of its own color and
50% of whatever was already in the framebuffer. Both quads are drawn with
`glDepthMask(GL_FALSE)` so depth writing does not reject the second quad's
fragments where the two overlap. Key B toggles the demo.

### Buffer clearing rule

The first GL call of every frame is exactly:

```python
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
```

so neither color nor depth residue from the previous frame can bleed
through or corrupt z-buffer decisions.

## Program structure

```
main()                     events -> state update -> render -> flip, Clock.tick(60)
 |- setup_gl()             Task 5.1 pipeline configuration (once)
 |- draw_colored_cube()    Task 5.2
 |- draw_arm()             Task 5.3 (hierarchical matrix stack)
 |- draw_blending_demo()   Task 5.4
```

Event handling, state update, rendering and `pygame.time.Clock().tick(60)`
FPS regulation are kept in separate stages of the loop, and `main()`
exits with `pygame.quit()` on ESC or window close.

## Controls

| Key | Action |
| --- | --- |
| ESC / window close | quit |
| SPACE | toggle cube auto-rotation |
| Arrow keys | manual cube rotation (X and Y axes) |
| A | toggle the articulated arm |
| J | toggle arm joint animation |
| K / L | elbow angle +10 / -10 degrees |
| B | toggle the alpha blending demo |

## Headless verification (what could and could not be tested here)

This code was developed in a sandbox with **no display and no GPU**. The
results of the two-step check requested by the lab:

1. `SDL_VIDEODRIVER=dummy` with pygame 2.6.1 installed: creating an
   `OPENGL | DOUBLEBUF` context fails with *"OpenGL support is either not
   configured in SDL or not available in current SDL video driver (dummy)"*.
   SDL's dummy video driver provides no GL context, so **no screenshot and
   no live GL run were possible; none are included and none were fabricated**.
2. Therefore the module was structured so every pure-logic piece is
   importable without pygame/OpenGL (all GL imports live inside the
   drawing functions), and a separate test file,
   `test_activity_5_logic.py`, verifies:
   - the cube vertex/color/surface tables (8 vertices, 6 quads, all
     indices valid and all vertices used),
   - the Python mirror of the arm's matrix chain
     (`compute_arm_chain()`, which performs the same
     translate -> rotate -> translate -> rotate -> translate
     composition as `draw_arm()`'s GL stack) against an independent
     hand-computed trigonometric forward-kinematics solution for 16
     shoulder/elbow angle combinations, including the zero-angle case
     (hand at (-3, 1.7, 0)) and the 90-degree shoulder case
     (hand at (-5.7, -1, 0)),
   - the blending equation `alpha_blend((1,0,0,0.5), (0,0,1,1)) ==
     (0.5,0,0.5,1)`, plus opaque, transparent and symmetric 50/50 cases.

   Result: **all logic tests pass** (`python3 test_activity_5_logic.py` ->
   `ALL LOGIC TESTS PASSED`), and both files compile cleanly
   (`python -m py_compile`).

What the tests cannot cover is the GL pipeline itself (context creation,
rasterization, the actual framebuffer blend and depth test), which by
nature requires a desktop with OpenGL.

## Exact run instructions

```bash
pip install "pygame>=2.1" "PyOpenGL>=3.1"
python activity_5.py
```

Requires a desktop environment with hardware or software OpenGL 2.x+
(e.g. X11/Wayland on Linux, Windows, macOS). On Linux without a display
server, an X server is required; `SDL_VIDEODRIVER=dummy` will NOT work
for OpenGL contexts (see above).
