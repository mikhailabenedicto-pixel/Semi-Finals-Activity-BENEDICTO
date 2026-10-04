# Activity 3: 3D Coordinate Geometry, Distance Metrics, & Spatial Bounding Volume

import math
import random


# ---------------------------------------------------------------------------
# Task 3.1 - Point3D: 3D vector space mathematics
# ---------------------------------------------------------------------------
class Point3D:
    """A point/vector in 3D Cartesian space R^3 (right-hand rule)."""

    def __init__(self, x: float, y: float, z: float):
        self.x, self.y, self.z = x, y, z

    # --- 3D Euclidean distance: d = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
    def distance_to(self, other: "Point3D") -> float:
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    # Squared distance (optimization insight: no sqrt needed for comparisons)
    def distance_sq_to(self, other: "Point3D") -> float:
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    # --- Vector subtraction (self - other)
    def subtract(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    # --- Dot product
    def dot(self, other: "Point3D") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    # --- Cross product (right-hand rule)
    def cross(self, other: "Point3D") -> "Point3D":
        return Point3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def magnitude(self) -> float:
        return math.sqrt(self.dot(self))

    # --- Octant determination per the right-hand rule.
    # Standard numbering: I(+,+,+), II(-,+,+), III(-,-,+), IV(+,-,+),
    #                     V(+,+,-), VI(-,+,-), VII(-,-,-), VIII(+,-,-).
    # A coordinate exactly 0 places the point ON a coordinate plane,
    # so it belongs to no octant strictly: return 0.
    def octant(self) -> int:
        if self.x == 0 or self.y == 0 or self.z == 0:
            return 0
        sx = 1 if self.x > 0 else -1
        sy = 1 if self.y > 0 else -1
        sz = 1 if self.z > 0 else -1
        table = {
            (1, 1, 1): 1, (-1, 1, 1): 2, (-1, -1, 1): 3, (1, -1, 1): 4,
            (1, 1, -1): 5, (-1, 1, -1): 6, (-1, -1, -1): 7, (1, -1, -1): 8,
        }
        return table[(sx, sy, sz)]

    def __repr__(self) -> str:
        return f"Point3D({self.x}, {self.y}, {self.z})"


# ---------------------------------------------------------------------------
# Task 3.1 - Sphere3D: spherical bounding volume
#   (x - h)^2 + (y - k)^2 + (z - l)^2 <= r^2
# ---------------------------------------------------------------------------
class Sphere3D:
    def __init__(self, center: Point3D, radius: float):
        self.center = center
        self.radius = radius

    def contains_point(self, p: Point3D) -> bool:
        return self.center.distance_to(p) <= self.radius

    def contains_point_sq(self, p: Point3D) -> bool:
        # sqrt-free equivalent of contains_point
        return self.center.distance_sq_to(p) <= self.radius ** 2

    # Sphere-sphere intersection: |C1 - C2| <= r1 + r2
    def intersects_sphere(self, other: "Sphere3D") -> bool:
        return self.center.distance_to(other.center) <= (self.radius + other.radius)

    def intersects_sphere_sq(self, other: "Sphere3D") -> bool:
        # OPTIMIZATION INSIGHT: avoid math.sqrt in broad-phase tests.
        # Compare squared distance against squared radius sum instead:
        #     dist_sq <= (r1 + r2)**2   (both sides non-negative, so equivalent)
        return self.center.distance_sq_to(other.center) <= (self.radius + other.radius) ** 2

    def bounding_aabb(self) -> "AABB":
        r = self.radius
        c = self.center
        return AABB(Point3D(c.x - r, c.y - r, c.z - r),
                    Point3D(c.x + r, c.y + r, c.z + r))

    def __repr__(self) -> str:
        return f"Sphere3D(center={self.center}, radius={self.radius:.3f})"


# ---------------------------------------------------------------------------
# Task 3.1 - AABB: axis-aligned bounding box (rectangular prism bounded by
#   planes x=k, y=k, z=k)
# ---------------------------------------------------------------------------
class AABB:
    def __init__(self, min_pt: Point3D, max_pt: Point3D):
        self.min_pt = min_pt
        self.max_pt = max_pt

    # Overlap along all three principal axes simultaneously
    def intersects(self, other: "AABB") -> bool:
        return (
            (self.min_pt.x <= other.max_pt.x and self.max_pt.x >= other.min_pt.x)
            and (self.min_pt.y <= other.max_pt.y and self.max_pt.y >= other.min_pt.y)
            and (self.min_pt.z <= other.max_pt.z and self.max_pt.z >= other.min_pt.z)
        )

    # Exact sphere-vs-AABB test: clamp sphere center to the box, then the
    # closest point on the box must be within the radius. Used as a
    # cross-check for the conservative AABB broad-phase test.
    def intersects_sphere_exact(self, s: Sphere3D) -> bool:
        c = s.center
        cx = max(self.min_pt.x, min(c.x, self.max_pt.x))
        cy = max(self.min_pt.y, min(c.y, self.max_pt.y))
        cz = max(self.min_pt.z, min(c.z, self.max_pt.z))
        closest = Point3D(cx, cy, cz)
        return c.distance_sq_to(closest) <= s.radius ** 2

    def __repr__(self) -> str:
        return f"AABB(min={self.min_pt}, max={self.max_pt})"


# ---------------------------------------------------------------------------
# Task 3.2 - Slide verification: distance P(2,-1,7) to Q(1,-3,5) must be 3.0
# ---------------------------------------------------------------------------
def task_3_2_verify_distance() -> None:
    print("=" * 64)
    print("TASK 3.2  Verify Example 3: 3D Euclidean distance")
    print("=" * 64)
    p = Point3D(2, -1, 7)
    q = Point3D(1, -3, 5)
    d = p.distance_to(q)
    print(f"P = {p}")
    print(f"Q = {q}")
    print(f"d = sqrt((1-2)^2 + (-3-(-1))^2 + (5-7)^2) = {d}")
    assert abs(d - 3.0) < 1e-12, f"Expected d = 3.0, got {d}"
    print(f"ASSERT PASSED: d == 3.0")
    print()


# ---------------------------------------------------------------------------
# Task 3.3 - Slide verification: complete the square for
#   x^2 + y^2 + z^2 + 4x - 6y + 2z + 6 = 0
#   General form x^2+y^2+z^2 + Ax + By + Cz + D = 0
#   => (x + A/2)^2 + (y + B/2)^2 + (z + C/2)^2 = (A/2)^2+(B/2)^2+(C/2)^2 - D
#   Center = (-A/2, -B/2, -C/2),  r = sqrt(center . center - D)
# ---------------------------------------------------------------------------
def task_3_3_verify_sphere_equation() -> Sphere3D:
    print("=" * 64)
    print("TASK 3.3  Verify Example 5: complete the square -> center & radius")
    print("=" * 64)
    # Coefficients of x^2 + y^2 + z^2 + 4x - 6y + 2z + 6 = 0
    A, B, C, D = 4.0, -6.0, 2.0, 6.0
    print(f"Equation: x^2 + y^2 + z^2 + {A:g}x + ({B:g})y + {C:g}z + {D:g} = 0")

    h, k, l = -A / 2.0, -B / 2.0, -C / 2.0
    print(f"Complete the square:")
    print(f"  x^2 + {A:g}x  = (x + {A/2:g})^2 - {A**2/4:g}")
    print(f"  y^2 + ({B:g})y = (y + {B/2:g})^2 - {B**2/4:g}")
    print(f"  z^2 + {C:g}z  = (z + {C/2:g})^2 - {C**2/4:g}")
    r_sq = h * h + k * k + l * l - D
    print(f"  => (x - ({h:g}))^2 + (y - {k:g})^2 + (z - ({l:g}))^2 = {r_sq:g}")

    radius = math.sqrt(r_sq)
    center = Point3D(h, k, l)
    sphere = Sphere3D(center, radius)
    print(f"Extracted center = ({h:g}, {k:g}, {l:g})")
    print(f"Extracted radius = sqrt({r_sq:g}) = {radius:.7f}")

    assert (h, k, l) == (-2.0, 3.0, -1.0), f"Expected center (-2, 3, -1), got ({h}, {k}, {l})"
    assert abs(radius - math.sqrt(8)) < 1e-12, f"Expected radius sqrt(8), got {radius}"
    assert abs(radius - 2.8284271) < 1e-6, f"Expected radius ~2.8284271, got {radius}"

    # Sanity: the original equation vanishes on the sphere surface.
    # Radius-offset points from the center all lie exactly on the surface
    for pt in (Point3D(h + radius, k, l), Point3D(h, k + radius, l),
               Point3D(h, k, l + radius), Point3D(h, k, l + radius)):
        val = (pt.x ** 2 + pt.y ** 2 + pt.z ** 2
               + A * pt.x + B * pt.y + C * pt.z + D)
        assert abs(val) < 1e-9, f"Equation check failed at {pt}: {val}"
    print(f"ASSERT PASSED: center == (-2, 3, -1), radius == sqrt(8) ~ 2.8284271")
    print(f"ASSERT PASSED: equation evaluates to 0 on 4 surface sample points")
    print()
    return sphere


# ---------------------------------------------------------------------------
# Task 3.4 - Spatial tester: 100 random 3D objects, broad-phase collision
# ---------------------------------------------------------------------------
def task_3_4_spatial_tester(n_objects: int = 100) -> None:
    print("=" * 64)
    print(f"TASK 3.4  Spatial tester: {n_objects} random objects, broad-phase collision")
    print("=" * 64)
    random.seed(42)  # reproducible stress test

    space_min, space_max = -10.0, 10.0

    def rand_pt(lo=space_min, hi=space_max):
        return Point3D(random.uniform(lo, hi), random.uniform(lo, hi),
                       random.uniform(lo, hi))

    spheres = []
    boxes = []
    for i in range(n_objects):
        if i % 2 == 0:  # 50 random spheres
            s = Sphere3D(rand_pt(), random.uniform(0.5, 3.0))
            spheres.append(s)
            boxes.append(s.bounding_aabb())
        else:           # 50 random AABBs
            a, b = rand_pt(), rand_pt()
            mn = Point3D(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
            mx = Point3D(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
            boxes.append(AABB(mn, mx))
    print(f"Populated {len(spheres)} random spheres + {len(boxes) - len(spheres)}"
          f" random AABBs (seed=42, space [{space_min:g}, {space_max:g}]^3).")

    n_pairs = n_objects * (n_objects - 1) // 2
    print(f"Brute-force broad phase scans all {n_pairs} unique pairs.\n")

    # --- Sphere-sphere pairs: sqrt-free test (dist_sq <= (r1+r2)**2)
    sphere_hits = []
    sphere_hits_sqrt = []
    for i in range(len(spheres)):
        for j in range(i + 1, len(spheres)):
            if spheres[i].intersects_sphere_sq(spheres[j]):
                sphere_hits.append((i, j))
            if spheres[i].intersects_sphere(spheres[j]):
                sphere_hits_sqrt.append((i, j))
    print(f"Sphere-sphere test (squared-distance optimization):")
    print(f"  colliding pairs = {len(sphere_hits)} of {len(spheres)*(len(spheres)-1)//2}"
          f" sphere pairs (sqrt-free)")
    print(f"  sqrt-based recheck  = {len(sphere_hits_sqrt)} pairs -> "
          f"{'IDENTICAL' if sphere_hits == sphere_hits_sqrt else 'MISMATCH'}")
    assert sphere_hits == sphere_hits_sqrt, "sqrt-free and sqrt tests disagree"
    print(f"  ASSERT PASSED: sqrt-free test agrees with math.sqrt test exactly")

    # --- AABB-AABB pairs (all 100 objects as boxes; spheres use their
    #     bounding boxes)
    aabb_hits = []
    for i in range(n_objects):
        for j in range(i + 1, n_objects):
            if boxes[i].intersects(boxes[j]):
                aabb_hits.append((i, j))
    print(f"\nAABB overlap test (axis overlap on x, y and z):")
    print(f"  colliding pairs = {len(aabb_hits)} of {n_pairs} object pairs")

    # --- Cross-check: every sphere collision must also be caught by the
    #     AABB test (AABB is conservative => no false negatives).
    # A sphere at sphere-index i lives at global object-index 2*i, so map
    # sphere pairs into the global index space before comparing.
    all_sphere_global_pairs = {
        (2 * i, 2 * j) for i in range(len(spheres))
        for j in range(i + 1, len(spheres))
    }
    sphere_hit_set = {(2 * i, 2 * j) for (i, j) in sphere_hits}
    aabb_hit_set = set(aabb_hits)
    missed = sphere_hit_set - aabb_hit_set
    print(f"\nCross-check Sphere vs AABB (sphere pairs mapped to global indices):")
    print(f"  sphere collisions missed by AABB test: {len(missed)}")
    assert not missed, f"AABB test missed sphere collisions: {missed}"
    print(f"  ASSERT PASSED: every sphere-colliding pair is also an AABB collision")

    # AABB-only pairs on sphere pairs = conservative margin of the box test
    aabb_only_sphere_pairs = (aabb_hit_set & all_sphere_global_pairs) - sphere_hit_set
    print(f"  AABB-only sphere pairs (conservative margin): "
          f"{len(aabb_only_sphere_pairs)}")

    # --- Cross-check on mixed sphere-vs-AABB pairs: exact closest-point
    #     sphere/AABB test vs the conservative box-box test.
    mixed_exact = 0
    mixed_box = 0
    for si, s in enumerate(spheres):
        box_i = s.bounding_aabb()
        for bi in range(len(spheres), n_objects):
            if box_i.intersects(boxes[bi]):
                mixed_box += 1
            if boxes[bi].intersects_sphere_exact(s):
                mixed_exact += 1
    print(f"\nCross-check mixed sphere-vs-AABB pairs (50 x 50 = 2500 pairs):")
    print(f"  exact closest-point test hits : {mixed_exact}")
    print(f"  conservative box-box test hits: {mixed_box}")
    print(f"  conservative test overshoot (false positives): {mixed_box - mixed_exact}")
    assert mixed_box >= mixed_exact, "conservative test under-reported hits"
    print(f"  ASSERT PASSED: conservative AABB test >= exact sphere/AABB test")

    print(f"\nSTRESS-TEST SUMMARY")
    print(f"  objects scanned          : {n_objects} (50 spheres + 50 AABBs)")
    print(f"  unique pairs tested      : {n_pairs}")
    print(f"  sphere-sphere collisions : {len(sphere_hits)} (sqrt-free, verified vs sqrt)")
    print(f"  AABB-AABB collisions     : {len(aabb_hits)} (includes all sphere pairs)")
    print(f"  false negatives          : 0 (sphere hits fully contained in AABB hits)")
    print()


def main() -> None:
    print("*" * 64)
    print(" ACTIVITY 3: 3D COORDINATE GEOMETRY & SPATIAL BOUNDING VOLUMES")
    print("*" * 64)
    print()

    # Quick class-behaviour demo (dot, cross, octants, containment)
    print("-" * 64)
    print("Class demonstration: vector math, octants, bounding volumes")
    print("-" * 64)
    a = Point3D(1, 2, 3)
    b = Point3D(4, 5, 6)
    print(f"a = {a}, b = {b}")
    print(f"a - b (subtraction)      = {a.subtract(b)}")
    print(f"a . b (dot product)      = {a.dot(b)}")
    c = a.cross(b)
    print(f"a x b (cross product)    = {c}")
    print(f"a . (a x b) (perp check) = {a.dot(c)}  (must be 0)")
    assert a.dot(c) == 0
    demo_points = [Point3D(1, 2, 3), Point3D(-1, 2, 3), Point3D(-1, -2, 3),
                   Point3D(1, -2, 3), Point3D(1, 2, -3), Point3D(-1, 2, -3),
                   Point3D(-1, -2, -3), Point3D(1, -2, -3), Point3D(2, 0, 5)]
    for pt in demo_points:
        o = pt.octant()
        label = f"Octant {o}" if o != 0 else "on a coordinate plane (no octant)"
        print(f"  {pt} -> {label}")
    assert [p.octant() for p in demo_points] == [1, 2, 3, 4, 5, 6, 7, 8, 0]
    s = Sphere3D(Point3D(0, 0, 0), 5.0)
    inside = Point3D(2, 2, 3)      # |(2,2,3)| = sqrt(17) ~ 4.12 <= 5
    boundary = Point3D(3, 0, 4)    # |(3,0,4)| = 5 exactly (on the surface)
    outside = Point3D(4, 4, 4)     # |(4,4,4)| = sqrt(48) ~ 6.93 > 5
    print(f"Sphere {s}: contains (2,2,3)? {s.contains_point(inside)}"
          f" | contains (3,0,4) (surface)? {s.contains_point(boundary)}"
          f" | contains (4,4,4)? {s.contains_point(outside)}")
    assert s.contains_point(inside) and s.contains_point(boundary) and not s.contains_point(outside)
    assert s.contains_point_sq(inside) and s.contains_point_sq(boundary) and not s.contains_point_sq(outside)
    assert s.center.distance_to(boundary) == 5.0
    b1 = AABB(Point3D(0, 0, 0), Point3D(2, 2, 2))
    b2 = AABB(Point3D(1, 1, 1), Point3D(3, 3, 3))
    b3 = AABB(Point3D(5, 5, 5), Point3D(6, 6, 6))
    print(f"AABB {b1} vs {b2}: intersect = {b1.intersects(b2)} (expect True)")
    print(f"AABB {b1} vs {b3}: intersect = {b1.intersects(b3)} (expect False)")
    assert b1.intersects(b2) and not b1.intersects(b3)
    print("Class demo asserts passed.\n")

    task_3_2_verify_distance()
    task_3_3_verify_sphere_equation()
    task_3_4_spatial_tester()

    print("*" * 64)
    print(" ALL ACTIVITY 3 CHECKS PASSED")
    print("*" * 64)


if __name__ == "__main__":
    main()
