# Activity 3 Technical Write-Up
## 3D Coordinate Geometry, Distance Metrics, & Spatial Bounding Volumes

**Module:** `activity_3_3d_geometry/activity_3.py`
**Environment:** Python 3.10+, standard library only (`math`, `random`). No Pygame required.

## 1. Design Overview

The single file `activity_3.py` implements the three classes of the lab starter template, then three verification tasks and a spatial stress test, all driven from `main()` with asserts on every manual-specified result.

### 1.1 `Point3D` (Task 3.1)

Stores `(x, y, z)` and implements:

- **Euclidean distance** `distance_to`: `d = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)`, plus a `distance_sq_to` helper that skips the square root (used by the optimization insight in Task 3.4).
- **Vector subtraction** `subtract`: component-wise `(x1-x2, y1-y2, z1-z2)`.
- **Dot product** `dot`: `x1*x2 + y1*y2 + z1*z2`.
- **Cross product** `cross`: determinant expansion `(y1*z2 - z1*y2, z1*x2 - x1*z2, x1*y2 - y1*x2)`, correct per the right-hand rule.
- **Octant determination** `octant()`: classifies by the sign triple `(sx, sy, sz)` using the standard numbering I(+,+,+), II(-,+,+), III(-,-,+), IV(+,-,+), V(+,+,-), VI(-,+,-), VII(-,-,-), VIII(+,-,-). A point with any zero coordinate lies on a coordinate plane, not strictly inside an octant, and reports octant 0.

### 1.2 `Sphere3D` (Task 3.1)

Models `(x-h)^2 + (y-k)^2 + (z-l)^2 <= r^2` from a center `Point3D` and radius.

- `contains_point(p)`: `center.distance_to(p) <= radius` (a `contains_point_sq` variant does the same without `sqrt`).
- `intersects_sphere(other)`: sphere-sphere test `|C1 - C2| <= r1 + r2`.
- `intersects_sphere_sq(other)`: the sqrt-free equivalent `dist_sq <= (r1 + r2)**2`. This is exact, not an approximation: both sides are non-negative, so squaring preserves the inequality.
- `bounding_aabb()`: derives the enclosing AABB `[C-r, C+r]` per axis, used by the stress test so spheres and boxes live in one 100-object array.

### 1.3 `AABB` (Task 3.1)

Models the rectangular prism bounded by the planes `x = k`, `y = k`, `z = k` from `min_pt`/`max_pt`.

- `intersects(other)`: simultaneous axis overlap on all three principal axes, `(A.min_x <= B.max_x and A.max_x >= B.min_x) and (same for y) and (same for z)`.
- `intersects_sphere_exact(s)`: an exact mixed test (clamp the sphere center to the box, then compare the closest point's distance against `r`), used only for cross-checking the conservative box-box test.

## 2. Task 3.2: Distance Verification (Example 3)

For `P(2, -1, 7)` and `Q(1, -3, 5)`:

```
d = sqrt((1-2)^2 + (-3-(-1))^2 + (5-7)^2) = sqrt(1 + 4 + 4) = sqrt(9) = 3.0
```

The script prints `d = 3.0` and asserts `abs(d - 3.0) < 1e-12`. **Result: passes.**

## 3. Task 3.3: Sphere Equation via Completing the Square (Example 5)

For `x^2 + y^2 + z^2 + 4x - 6y + 2z + 6 = 0` with the general form
`x^2 + y^2 + z^2 + Ax + By + Cz + D = 0`:

```
x^2 + 4x      = (x + 2)^2 - 4
y^2 + (-6)y   = (y - 3)^2 - 9
z^2 + 2z      = (z + 1)^2 - 1
=> (x - (-2))^2 + (y - 3)^2 + (z - (-1))^2 = 4 + 9 + 1 - 6 = 8
```

The code computes the center as `(-A/2, -B/2, -C/2) = (-2, 3, -1)` and the radius as `sqrt(h^2 + k^2 + l^2 - D) = sqrt(8) = 2.8284271`, asserting:

- center `== (-2, 3, -1)` exactly,
- `abs(radius - math.sqrt(8)) < 1e-12` and `abs(radius - 2.8284271) < 1e-6`,
- the original polynomial evaluates to 0 at four radius-offset surface points.

**Result: passes.**

## 4. Task 3.4: Spatial Tester and Broad-Phase Collision Detection

- **Population:** 100 random objects in `[-10, 10]^3` with `random.seed(42)` for reproducibility: 50 random spheres (radius `0.5` to `3.0`) interleaved with 50 random AABBs. Each sphere also contributes its bounding AABB, so all 100 objects share one AABB array.
- **Brute-force broad phase:** all `C(100, 2) = 4950` unique pairs are scanned. Sphere-sphere pairs are tested with the **squared-distance optimization** required by the manual: `dist_sq <= (r1 + r2)**2`, avoiding `math.sqrt` entirely in the hot loop. A `math.sqrt`-based recheck runs over the same 1,225 sphere pairs and asserts the pair sets are identical.
- **Cross-checks (both methods agree where applicable):**
  1. Sphere-sphere: the sqrt-free and sqrt-based tests return exactly the same 43 colliding pairs.
  2. Sphere vs AABB: every sphere collision must also be caught by the AABB test, because a sphere is contained in its bounding box, so the box test is conservative (no false negatives, only false positives). Sphere pairs are mapped from sphere indices `(i, j)` to global object indices `(2i, 2j)` before comparison. Zero sphere collisions are missed by the AABB test; the 16 AABB-only sphere pairs quantify the conservative margin.
  3. Mixed sphere-vs-AABB pairs: the conservative box-box test reports 305 hits versus 290 for the exact closest-point test, i.e. 15 false positives and 0 false negatives, matching theory.
- **Results (seed 42):** 43 sphere-sphere colliding pairs of 1,225; 899 AABB colliding pairs of 4,950; 0 missed sphere collisions.

## 5. Optimization Insight

The manual's production guidance is implemented literally: `Sphere3D.intersects_sphere_sq` compares squared center distance against `(r1 + r2)**2` and never calls `math.sqrt`. Since `x <= y` iff `x^2 <= y^2` for non-negative `x, y`, the test is mathematically identical to the sqrt form, and the stress test verifies both paths produce the identical pair set. In a real engine the sqrt version would only run on narrow-phase candidates.

## 6. Verification Summary

| Check | Expected | Actual | Status |
|---|---|---|---|
| Task 3.2 distance P-Q | 3.0 | 3.0 | pass (assert) |
| Task 3.3 center | (-2, 3, -1) | (-2, 3, -1) | pass (assert) |
| Task 3.3 radius | sqrt(8) = 2.8284271 | 2.8284271 | pass (assert) |
| Octants on demo points | 1..8 plus plane case | 1..8 plus 0 | pass (assert) |
| Cross product perpendicularity | a . (a x b) = 0 | 0 | pass (assert) |
| Sphere containment / boundary / outside | True / True / False | True / True / False | pass (assert) |
| Sphere-sphere sqrt-free vs sqrt | identical pair sets | 43 = 43 | pass (assert) |
| AABB catches every sphere collision | 0 missed | 0 missed | pass (assert) |
| Conservative AABB >= exact sphere/AABB | overshoot >= 0 | 305 >= 290 | pass (assert) |

## 7. Execution Log

Actual sandbox output of `python3 activity_3.py` (exit code 0, all asserts passed):

```
****************************************************************
 ACTIVITY 3: 3D COORDINATE GEOMETRY & SPATIAL BOUNDING VOLUMES
****************************************************************

----------------------------------------------------------------
Class demonstration: vector math, octants, bounding volumes
----------------------------------------------------------------
a = Point3D(1, 2, 3), b = Point3D(4, 5, 6)
a - b (subtraction)      = Point3D(-3, -3, -3)
a . b (dot product)      = 32
a x b (cross product)    = Point3D(-3, 6, -3)
a . (a x b) (perp check) = 0  (must be 0)
  Point3D(1, 2, 3) -> Octant 1
  Point3D(-1, 2, 3) -> Octant 2
  Point3D(-1, -2, 3) -> Octant 3
  Point3D(1, -2, 3) -> Octant 4
  Point3D(1, 2, -3) -> Octant 5
  Point3D(-1, 2, -3) -> Octant 6
  Point3D(-1, -2, -3) -> Octant 7
  Point3D(1, -2, -3) -> Octant 8
  Point3D(2, 0, 5) -> on a coordinate plane (no octant)
Sphere Sphere3D(center=Point3D(0, 0, 0), radius=5.000): contains (2,2,3)? True | contains (3,0,4) (surface)? True | contains (4,4,4)? False
AABB AABB(min=Point3D(0, 0, 0), max=Point3D(2, 2, 2)) vs AABB(min=Point3D(1, 1, 1), max=Point3D(3, 3, 3)): intersect = True (expect True)
AABB AABB(min=Point3D(0, 0, 0), max=Point3D(2, 2, 2)) vs AABB(min=Point3D(5, 5, 5), max=Point3D(6, 6, 6)): intersect = False (expect False)
Class demo asserts passed.

================================================================
TASK 3.2  Verify Example 3: 3D Euclidean distance
================================================================
P = Point3D(2, -1, 7)
Q = Point3D(1, -3, 5)
d = sqrt((1-2)^2 + (-3-(-1))^2 + (5-7)^2) = 3.0
ASSERT PASSED: d == 3.0

================================================================
TASK 3.3  Verify Example 5: complete the square -> center & radius
================================================================
Equation: x^2 + y^2 + z^2 + 4x + (-6)y + 2z + 6 = 0
Complete the square:
  x^2 + 4x  = (x + 2)^2 - 4
  y^2 + (-6)y = (y + -3)^2 - 9
  z^2 + 2z  = (z + 1)^2 - 1
  => (x - (-2))^2 + (y - 3)^2 + (z - (-1))^2 = 8
Extracted center = (-2, 3, -1)
Extracted radius = sqrt(8) = 2.8284271
ASSERT PASSED: center == (-2, 3, -1), radius == sqrt(8) ~ 2.8284271
ASSERT PASSED: equation evaluates to 0 on 4 surface sample points

================================================================
TASK 3.4  Spatial tester: 100 random objects, broad-phase collision
================================================================
Populated 50 random spheres + 50 random AABBs (seed=42, space [-10, 10]^3).
Brute-force broad phase scans all 4950 unique pairs.

Sphere-sphere test (squared-distance optimization):
  colliding pairs = 43 of 1225 sphere pairs (sqrt-free)
  sqrt-based recheck  = 43 pairs -> IDENTICAL
  ASSERT PASSED: sqrt-free test agrees with math.sqrt test exactly

AABB overlap test (axis overlap on x, y and z):
  colliding pairs = 899 of 4950 object pairs

Cross-check Sphere vs AABB (sphere pairs mapped to global indices):
  sphere collisions missed by AABB test: 0
  ASSERT PASSED: every sphere-colliding pair is also an AABB collision
  AABB-only sphere pairs (conservative margin): 16

Cross-check mixed sphere-vs-AABB pairs (50 x 50 = 2500 pairs):
  exact closest-point test hits : 290
  conservative box-box test hits: 305
  conservative test overshoot (false positives): 15
  ASSERT PASSED: conservative AABB test >= exact sphere/AABB test

STRESS-TEST SUMMARY
  objects scanned          : 100 (50 spheres + 50 AABBs)
  unique pairs tested      : 4950
  sphere-sphere collisions : 43 (sqrt-free, verified vs sqrt)
  AABB-AABB collisions     : 899 (includes all sphere pairs)
  false negatives          : 0 (sphere hits fully contained in AABB hits)

****************************************************************
 ALL ACTIVITY 3 CHECKS PASSED
****************************************************************
```
