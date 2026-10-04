# Computer Graphics Programming: Semi-Final Laboratory Activities

Five progressive Python activities covering 2D animation, Pygame game
architecture, 3D geometry, 3D projections, and the OpenGL pipeline.
Built with Python 3.10+, pygame >= 2.1, and PyOpenGL >= 3.1 (Activity 5 only).

## Repository layout (matches the required submission structure)

| Folder | Activity | Topics | Weight |
|---|---|---|---|
| activity_1_2d_animation/ | Activity 1 | Tweening (LERP + ease), polygon morphing, bouncing ball dynamics | 20% |
| activity_2_pygame_sprites/ | Activity 2 | Game loop, OOP sprites, collision detection, HUD, particles | 20% |
| activity_3_3d_geometry/ | Activity 3 | 3D distance, spheres, AABBs, broad-phase collision | 20% |
| activity_4_projections/ | Activity 4 | Orthographic, Cavalier, Cabinet, one-point perspective | 20% |
| activity_5_pyopengl/ | Activity 5 | GL pipeline, per-vertex colors, matrix stack, depth + blending | 20% |

Each folder contains the standalone `.py` program, `writeup.md`
(derivation + verification log), and frame captures where applicable.

## How to run

```bash
pip install "pygame>=2.1" "PyOpenGL>=3.1"
python activity_1_2d_animation/activity_1.py   # keys 1/2/3 = modes, L/E = easing, SPACE = reset ball
python activity_2_pygame_sprites/activity_2.py # arrows = move, collision arena with HUD
python activity_3_3d_geometry/activity_3.py    # console program; prints verification + stress test
python activity_4_projections/activity_4.py    # keys 1-4 = projections, arrows + Q/E = rotate, R = reset
python activity_5_pyopengl/activity_5.py       # needs a real display (OpenGL); A toggles arm, B toggles blending
```

Activity 3 is console-only by design. Activity 5 requires a GPU/display;
its pure-logic parts are tested headlessly by
`activity_5_pyopengl/test_activity_5_logic.py`.
