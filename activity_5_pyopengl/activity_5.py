"""
Activity 5: Hardware Graphics Pipeline & Shading with PyOpenGL
==============================================================

Tasks (from the laboratory manual, "Activity 5"):
  Task 5.1  Configure the PyOpenGL pipeline with gluPerspective(), depth
            testing and double buffering.
  Task 5.2  Render a solid 3D cube with distinct per-vertex colors using
            GL_QUADS.
  Task 5.3  Continuous rotation with glRotatef() and an articulated arm
            (shoulder -> elbow -> hand) built with glPushMatrix()/glPopMatrix(),
            as detailed in slide 11 of the Graphics Libraries lecture.
  Task 5.4  Enable GL_BLEND with glBlendFunc(GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA) and demonstrate semi-transparent
            polygons overlapping in 3D space.

Run:  python activity_5.py      (requires pygame >= 2.1, PyOpenGL >= 3.1,
                                 a desktop with an OpenGL 2.x-compatible GPU)

Controls:
  ESC / window close .... quit
  LEFT / RIGHT .......... rotate cube about the Y axis (manual override)
  UP / DOWN ............. rotate cube about the X axis (manual override)
  SPACE ................. toggle auto-rotation of the cube
  A ..................... toggle the articulated arm on/off
  J / K / L ............. animate / increase / decrease arm joint angles
  B ..................... toggle the alpha-blending demo (Task 5.4)

Note: this module also exposes the pure-logic helpers (cube tables, the
Python mirror of the arm's forward-kinematics matrix chain, and the alpha
blending equation) so they can be unit-tested on a machine without a
display or GPU. See test_activity_5_logic.py.
"""

import math
import time

# ---------------------------------------------------------------------------
# Pure-logic section: importable and testable WITHOUT pygame / OpenGL.
# ---------------------------------------------------------------------------

# Cube vertex positions (x, y, z), exactly as given in the manual.
CUBE_VERTICES = [
    (1.0, -1.0, -1.0),
    (1.0, 1.0, -1.0),
    (-1.0, 1.0, -1.0),
    (-1.0, -1.0, -1.0),
    (1.0, -1.0, 1.0),
    (1.0, 1.0, 1.0),
    (-1.0, -1.0, 1.0),
    (-1.0, 1.0, 1.0),
]

# Distinct per-vertex colors (r, g, b), as given in the manual.
CUBE_COLORS = [
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (1.0, 1.0, 0.0),
    (1.0, 0.0, 1.0),
    (0.0, 1.0, 1.0),
    (1.0, 1.0, 1.0),
    (0.5, 0.5, 0.5),
]

# Quad surfaces: each tuple lists the 4 vertex indices of one cube face.
CUBE_SURFACES = [
    (0, 1, 2, 3),
    (3, 2, 7, 6),
    (6, 7, 5, 4),
    (4, 5, 1, 0),
    (1, 5, 7, 2),
    (4, 0, 3, 6),
]

# Articulated arm geometry (object-space, units match the cube's scale).
ARM_SHOULDER_POS = (-3.0, -1.0, 0.0)   # shoulder joint origin, world space
ARM_SHOULDER_LEN = 1.5                 # shoulder -> elbow segment length
ARM_ELBOW_LEN = 1.2                    # elbow -> hand segment length


def rotation_matrix_y(angle_deg):
    """Column-major 4x4 rotation about the Y axis (matches glRotatef(a,0,1,0))."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    # Column-major, as OpenGL stores matrices: m[col][row] flattened.
    return (
        c, 0.0, -s, 0.0,
        0.0, 1.0, 0.0, 0.0,
        s, 0.0, c, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def rotation_matrix_z(angle_deg):
    """Column-major 4x4 rotation about the Z axis (matches glRotatef(a,0,0,1))."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return (
        c, s, 0.0, 0.0,
        -s, c, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def translation_matrix(tx, ty, tz):
    """Column-major 4x4 translation (matches glTranslatef(tx,ty,tz))."""
    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    )


def mat_multiply(a, b):
    """Column-major 4x4 matrix product a * b (i.e. apply b first, then a)."""
    out = [0.0] * 16
    for col in range(4):
        for row in range(4):
            out[col * 4 + row] = sum(
                a[k * 4 + row] * b[col * 4 + k] for k in range(4)
            )
    return tuple(out)


def transform_point(m, point):
    """Apply a column-major 4x4 matrix to a 3D point (w = 1, affine)."""
    x, y, z = point
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * y + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


def compute_arm_chain(shoulder_angle_deg, elbow_angle_deg):
    """
    Python mirror of the GL matrix stack used by draw_arm().

    The GL code performs (current = identity):
        glTranslate(shoulder)          -> move to shoulder joint
        glRotate(shoulder_angle, 0,0,1) -> rotate the upper arm about Z
        draw segment of length ARM_SHOULDER_LEN along local +Y
        glTranslate(0, ARM_SHOULDER_LEN, 0) -> move to the elbow joint
        glRotate(elbow_angle, 0,0,1)   -> rotate the forearm about Z
        glTranslate(0, ARM_ELBOW_LEN, 0) -> move to the hand
    The hand position returned is the elbow->hand end point, i.e. the tip
    of the forearm segment. This chain reproduces exactly what
    glPushMatrix()/glPopMatrix() would produce on the GPU.
    """
    base = translation_matrix(*ARM_SHOULDER_POS)
    shoulder = mat_multiply(base, rotation_matrix_z(shoulder_angle_deg))

    elbow_local = translation_matrix(0.0, ARM_SHOULDER_LEN, 0.0)
    elbow_world = mat_multiply(shoulder, elbow_local)
    forearm = mat_multiply(elbow_world, rotation_matrix_z(elbow_angle_deg))

    hand_local = translation_matrix(0.0, ARM_ELBOW_LEN, 0.0)
    hand_world = mat_multiply(forearm, hand_local)

    # The elbow joint sits at the translation column of elbow_world
    # (identical in `forearm`, since a pure rotation adds no translation).
    elbow_joint = (
        elbow_world[12], elbow_world[13], elbow_world[14],
    )
    hand_joint = (
        hand_world[12], hand_world[13], hand_world[14],
    )
    return {
        "shoulder_matrix": shoulder,
        "elbow_matrix": forearm,
        "elbow_joint": elbow_joint,
        "hand": hand_joint,
    }


def alpha_blend(src, dst):
    """
    Python mirror of glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA):
        I = a1 * I1 + a2 * I2, with a2 = 1 - a1.
    `src` and `dst` are (r, g, b, a) tuples in [0, 1].
    """
    a = src[3]
    return tuple(
        src[i] * a + dst[i] * (1.0 - a) for i in range(3)
    ) + (1.0,)


# ---------------------------------------------------------------------------
# GL rendering section: executed only when a display/GPU is available.
# ---------------------------------------------------------------------------

IS_HEADLESS_TEST = False  # flipped to True by test harnesses that skip GL


def _load_gl():
    """Import pygame and PyOpenGL. Raises ImportError when unavailable."""
    import pygame  # noqa: F401
    from OpenGL.GL import glClear  # noqa: F401
    from OpenGL.GLU import gluPerspective  # noqa: F401
    return pygame, gluPerspective


def draw_colored_cube():
    """Task 5.2: solid cube, one GL_QUADS face at a time, per-vertex colors."""
    from OpenGL.GL import glBegin, glEnd, GL_QUADS, glColor3fv, glVertex3fv
    glBegin(GL_QUADS)
    for surface in CUBE_SURFACES:
        for vertex_idx in surface:
            glColor3fv(CUBE_COLORS[vertex_idx])
            glVertex3fv(CUBE_VERTICES[vertex_idx])
    glEnd()


def draw_arm(shoulder_angle_deg, elbow_angle_deg):
    """
    Task 5.3: two-segment articulated arm (shoulder -> elbow -> hand).

    The matrix stack mirrors compute_arm_chain() above exactly:
      push  translate to shoulder      push  rotate about Z (shoulder)
            draw upper arm            push  translate along local +Y
            push rotate about Z (elbow)      draw forearm
            push translate along local +Y    draw hand sphere
            pop x3                    pop x2  back to base modelview.
    """
    from OpenGL.GL import (glPushMatrix, glPopMatrix, glTranslatef,
                           glRotatef, glBegin, glEnd, GL_QUADS,
                           glColor3f, glVertex3f)

    SEG_HALF = 0.12  # half-width of the rectangular arm segments

    def segment(length, r, g, b):
        # A thin quad strip drawn as two quads in the local XY plane,
        # extending along local +Y for `length` units.
        glBegin(GL_QUADS)
        glColor3f(r, g, b)
        glVertex3f(-SEG_HALF, 0.0, 0.0)
        glVertex3f(SEG_HALF, 0.0, 0.0)
        glVertex3f(SEG_HALF, length, 0.0)
        glVertex3f(-SEG_HALF, length, 0.0)
        # give the segment thickness so it is visible from any angle
        glVertex3f(-SEG_HALF, 0.0, SEG_HALF)
        glVertex3f(SEG_HALF, 0.0, SEG_HALF)
        glVertex3f(SEG_HALF, length, SEG_HALF)
        glVertex3f(-SEG_HALF, length, SEG_HALF)
        glEnd()

    glPushMatrix()
    glTranslatef(*ARM_SHOULDER_POS)
    # shoulder joint: rotation about Z (in the XY plane, facing the camera)
    glRotatef(shoulder_angle_deg, 0.0, 0.0, 1.0)
    segment(ARM_SHOULDER_LEN, 0.9, 0.9, 0.9)      # upper arm

    glPushMatrix()
    glTranslatef(0.0, ARM_SHOULDER_LEN, 0.0)      # move to elbow joint
    glRotatef(elbow_angle_deg, 0.0, 0.0, 1.0)     # elbow flexion
    segment(ARM_ELBOW_LEN, 0.9, 0.6, 0.2)         # forearm

    glPushMatrix()
    glTranslatef(0.0, ARM_ELBOW_LEN, 0.0)         # move to the hand
    # hand: small colored quad marker at the wrist end
    glBegin(GL_QUADS)
    glColor3f(0.2, 0.6, 1.0)
    glVertex3f(-0.18, -0.10, 0.0)
    glVertex3f(0.18, -0.10, 0.0)
    glVertex3f(0.18, 0.10, 0.0)
    glVertex3f(-0.18, 0.10, 0.0)
    glEnd()
    glPopMatrix()   # hand
    glPopMatrix()   # elbow
    glPopMatrix()   # shoulder / base


def draw_blending_demo(spin_deg):
    """
    Task 5.4: two semi-transparent overlapping quads in 3D space.
    Relies on the blending mode enabled once at startup:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    Render order matters: because the depth buffer would reject the
    fragment drawn second if it were behind, both quads are drawn with
    depth writes disabled so both contribute to the final blended color.
    """
    from OpenGL.GL import (glBegin, glEnd, GL_QUADS, glColor4f,
                           glDepthMask, glVertex3f)

    glDepthMask(GL_FALSE)
    glBegin(GL_QUADS)
    # red quad, alpha = 0.5
    glColor4f(1.0, 0.0, 0.0, 0.5)
    glVertex3f(-0.8, -0.8, 0.5)
    glVertex3f(0.8, -0.8, 0.5)
    glVertex3f(0.8, 0.8, 0.5)
    glVertex3f(-0.8, 0.8, 0.5)
    # blue quad, alpha = 1.0, offset along x/y/z so it overlaps the red one
    glColor4f(0.0, 0.0, 1.0, 1.0)
    glVertex3f(-0.4, -0.4, 1.4)
    glVertex3f(1.2, -0.4, 1.4)
    glVertex3f(1.2, 1.2, 1.4)
    glVertex3f(-0.4, 1.2, 1.4)
    glEnd()
    glDepthMask(GL_TRUE)


def setup_gl(display_size):
    """Task 5.1: context + perspective + depth test + blending."""
    from OpenGL.GL import (glEnable, GL_DEPTH_TEST, GL_BLEND, glBlendFunc,
                           GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, glClearColor,
                           glViewport, glMatrixMode, GL_PROJECTION, glLoadIdentity,
                           GL_MODELVIEW)
    from OpenGL.GLU import gluPerspective

    glViewport(0, 0, display_size[0], display_size[1])
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, display_size[0] / display_size[1], 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -5)
    glEnable(GL_DEPTH_TEST)
    # Task 5.4: standard "over" alpha blending, enabled once globally.
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.05, 0.05, 0.10, 1.0)


def main():
    """Main loop: events -> state update -> GL render -> buffer swap."""
    pygame, _ = _load_gl()
    from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN, K_ESCAPE
    from OpenGL.GL import (glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
                           glRotatef, glLoadIdentity)

    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption('Activity 5: Hardware Pipeline with PyOpenGL')
    setup_gl(display)

    clock = pygame.time.Clock()
    auto_rotate = True
    show_arm = True
    show_blend = True
    arm_animating = True
    spin_y = 0.0
    spin_x = 0.0
    shoulder_angle = 45.0
    elbow_angle = -60.0

    running = True
    while running:
        # ---- events ----
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    auto_rotate = not auto_rotate
                elif event.key == pygame.K_a:
                    show_arm = not show_arm
                elif event.key == pygame.K_b:
                    show_blend = not show_blend
                elif event.key == pygame.K_j:
                    arm_animating = not arm_animating
                elif event.key == pygame.K_k:
                    elbow_angle += 10.0
                elif event.key == pygame.K_l:
                    elbow_angle -= 10.0

        # ---- state update ----
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            spin_y -= 2.0
        if keys[pygame.K_RIGHT]:
            spin_y += 2.0
        if keys[pygame.K_UP]:
            spin_x -= 2.0
        if keys[pygame.K_DOWN]:
            spin_x += 2.0
        if auto_rotate:
            spin_y += 0.5          # continuous rotation, time-independent step
        if arm_animating:
            shoulder_angle = 45.0 + 25.0 * math.sin(time.time() * 0.8)
            elbow_angle = -60.0 + 30.0 * math.sin(time.time() * 1.3)

        # ---- render ----
        # BUFFER CLEARING RULE: clear color AND depth at the start of
        # every frame, or previous frames bleed through and the z-buffer
        # produces artifacts.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -5)
        glRotatef(spin_x, 1.0, 0.0, 0.0)
        glRotatef(spin_y, 0.0, 1.0, 0.0)

        draw_colored_cube()
        if show_arm:
            draw_arm(shoulder_angle, elbow_angle)
        if show_blend:
            draw_blending_demo(spin_y)

        pygame.display.flip()
        clock.tick(60)             # FPS regulation at 60 frames/second

    # ---- clean shutdown ----
    pygame.quit()


if __name__ == "__main__":
    main()
