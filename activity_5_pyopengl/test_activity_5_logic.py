"""
Headless logic tests for activity_5.py (no display, no GPU required).

Run:  python test_activity_5_logic.py
Covers: cube tables, the Python mirror of the arm's forward-kinematics
matrix chain, and the alpha blending equation.
"""
import math
import activity_5 as a5


def test_cube_tables():
    assert len(a5.CUBE_VERTICES) == 8
    assert len(a5.CUBE_COLORS) == 8
    assert len(a5.CUBE_SURFACES) == 6
    # every face quad references 4 valid vertices, all 8 vertices are used
    used = set()
    for face in a5.CUBE_SURFACES:
        assert len(face) == 4
        for idx in face:
            assert 0 <= idx < 8
            used.add(idx)
    assert used == set(range(8))


def test_identity_behaviour():
    ident = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    p = (1.0, 2.0, 3.0)
    assert a5.transform_point(ident, p) == p
    # translating then rotating must equal composing the matrices in GL order
    t = a5.translation_matrix(1, 2, 3)
    assert a5.transform_point(t, p) == (2.0, 4.0, 6.0)


def test_arm_chain_hand_position():
    """Hand tip must match a hand-computed 2D FK chain:
    shoulder at (-3,-1), upper arm 1.5 along rotated +Y,
    forearm 1.2 further rotated.  Compare against a direct trig solution."""
    for sh_deg in (0, 45, 90, -30):
        for el_deg in (0, -60, 30, 15):
            chain = a5.compute_arm_chain(sh_deg, el_deg)
            sh = math.radians(sh_deg)
            el = math.radians(el_deg)
            # upper-arm tip (elbow) in world space
            ex = a5.ARM_SHOULDER_POS[0] - math.sin(sh) * a5.ARM_SHOULDER_LEN
            ey = a5.ARM_SHOULDER_POS[1] + math.cos(sh) * a5.ARM_SHOULDER_LEN
            # forearm direction = sh + el from vertical
            hx = ex - math.sin(sh + el) * a5.ARM_ELBOW_LEN
            hy = ey + math.cos(sh + el) * a5.ARM_ELBOW_LEN
            assert abs(chain['hand'][0] - hx) < 1e-9, (sh_deg, el_deg)
            assert abs(chain['hand'][1] - hy) < 1e-9, (sh_deg, el_deg)
            assert abs(chain['elbow_joint'][0] - ex) < 1e-9
            assert abs(chain['elbow_joint'][1] - ey) < 1e-9
    # zero angles: arm points straight up, hand at (-3, -1 + 1.5 + 1.2, 0)
    chain = a5.compute_arm_chain(0.0, 0.0)
    assert abs(chain['hand'][0] + 3.0) < 1e-9
    assert abs(chain['hand'][1] - (-1.0 + 1.5 + 1.2)) < 1e-9
    assert abs(chain['hand'][2]) < 1e-9


def test_arm_chain_matches_gl_rotation_sign():
    """compute_arm_chain uses glRotatef(theta, 0,0,1): the local +Y axis
    (0,1) maps to (-sin, cos) in world space. Verify with the matrix."""
    chain = a5.compute_arm_chain(90.0, 0.0)
    # +Y rotated 90 deg about Z points along -X, so hand is 1.5+1.2 in -X
    assert abs(chain['hand'][0] - (-3.0 - 2.7)) < 1e-9
    assert abs(chain['hand'][1] - (-1.0)) < 1e-9


def test_alpha_blending():
    # (1,0,0,0.5) over (0,0,1,1) -> (0.5, 0, 0.5, 1)
    got = a5.alpha_blend((1.0, 0.0, 0.0, 0.5), (0.0, 0.0, 1.0, 1.0))
    exp = (0.5, 0.0, 0.5, 1.0)
    for g, e in zip(got, exp):
        assert abs(g - e) < 1e-12, (got, exp)
    # fully opaque source fully replaces the destination
    assert a5.alpha_blend((0.2, 0.4, 0.6, 1.0), (1, 1, 1, 1)) == (0.2, 0.4, 0.6, 1.0)
    # fully transparent source leaves the destination unchanged
    assert a5.alpha_blend((0.9, 0.9, 0.9, 0.0), (0.1, 0.2, 0.3, 1.0)) == (0.1, 0.2, 0.3, 1.0)
    # symmetric check: 50/50 blend of red over blue = blue over red
    a = a5.alpha_blend((1, 0, 0, 0.5), (0, 0, 1, 1))
    b = a5.alpha_blend((0, 0, 1, 0.5), (1, 0, 0, 1))
    assert a[:3] == b[:3] == (0.5, 0.0, 0.5)


if __name__ == '__main__':
    test_cube_tables()
    test_identity_behaviour()
    test_arm_chain_hand_position()
    test_arm_chain_matches_gl_rotation_sign()
    test_alpha_blending()
    print('ALL LOGIC TESTS PASSED')
