# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Cut surfaces ("patches") and the kerf slab built from them.

A patch is a simple open mesh given as (verts, faces) in world space:
  * rect_patch    -> straight cut: one quad, sized independently on each axis
  * plane_patch   -> square special case of rect_patch
  * ribbon_patch  -> curved cut: the stroke, run through a spline, extruded along
                     the view direction
  * loop_patch    -> freehand cut: a closed loop drawn on the surface, spanned by a
                     relaxed membrane

Both curved patches are built at a higher resolution than the handful of editable
control points behind them: the control points are put through a centripetal
Catmull-Rom spline and, for a loop, the interior is relaxed until it is the
smoothest surface that still ends exactly on the drawn loop. That is what keeps the
printed cut face flat instead of showing the facets of the polyline.

`slab_from_patch` thickens a patch by the cut gap (kerf) into a closed solid
that is subtracted from the model with a boolean.
"""

import bmesh
from mathutils import Vector

SURFACE_DETAIL = 3  # spline samples generated per control point segment
RELAX_PASSES = 40  # membrane relaxation passes for a strongly non planar loop
MAX_LOOP_SAMPLES = 160  # boundary samples a filled loop is capped to, whatever the settings


# ----------------------------------------------------------------------------
# polyline helpers
# ----------------------------------------------------------------------------
def newell_normal(points):
    n = Vector((0.0, 0.0, 0.0))
    m = len(points)
    for i in range(m):
        a = points[i]
        b = points[(i + 1) % m]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    if n.length < 1e-12:
        return Vector((0.0, 0.0, 1.0))
    return n.normalized()


def polyline_length(points, closed=False):
    total = 0.0
    m = len(points)
    rng = m if closed else m - 1
    for i in range(rng):
        total += (points[(i + 1) % m] - points[i]).length
    return total


def resample_polyline(points, count, closed=False):
    """Arc-length resample to `count` points (for closed loops the first point is not repeated)."""
    pts = [Vector(p) for p in points]
    if len(pts) < 2 or count < 2:
        return pts
    if closed:
        pts = pts + [pts[0]]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    if total <= 1e-12:
        return [pts[0].copy() for _ in range(count)]
    steps = count if closed else count - 1
    out = []
    target = 0.0
    i = 0
    acc = 0.0
    for k in range(steps + (0 if closed else 1)):
        target = total * k / steps
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        t = 0.0 if seg[i] <= 1e-12 else (target - acc) / seg[i]
        t = max(0.0, min(1.0, t))
        out.append(pts[i].lerp(pts[i + 1], t))
    return out


def smooth_polyline(points, factor, closed=False, iterations=None):
    """Laplacian smoothing. factor in [0,1]. End points of open lines are pinned."""
    pts = [Vector(p) for p in points]
    m = len(pts)
    if m < 3 or factor <= 0.0:
        return pts
    if iterations is None:
        iterations = max(1, int(round(factor * 8)))
    f = min(1.0, factor)
    for _ in range(iterations):
        new = [p.copy() for p in pts]
        rng = range(m) if closed else range(1, m - 1)
        for i in rng:
            prev = pts[(i - 1) % m]
            nxt = pts[(i + 1) % m]
            avg = (prev + nxt) * 0.5
            new[i] = pts[i].lerp(avg, f * 0.5)
        pts = new
    return pts


def dedupe_polyline(points, min_dist):
    out = []
    for p in points:
        if not out or (p - out[-1]).length >= min_dist:
            out.append(Vector(p))
    return out


def plane_basis(normal):
    n = Vector(normal).normalized()
    helper = Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = helper.cross(n).normalized()
    v = n.cross(u).normalized()
    return u, v


def _catmull_rom(p0, p1, p2, p3, steps, alpha=0.5):
    """Centripetal Catmull-Rom samples on the p1..p2 span (p2 itself not included).

    Centripetal (alpha=0.5) is the variant that never loops back on itself when two
    control points sit close together - which happens all the time in a hand drawn
    stroke resampled onto the model surface.
    """
    t0 = 0.0
    t1 = t0 + max((p1 - p0).length ** alpha, 1e-6)
    t2 = t1 + max((p2 - p1).length ** alpha, 1e-6)
    t3 = t2 + max((p3 - p2).length ** alpha, 1e-6)
    out = []
    for k in range(steps):
        t = t1 + (t2 - t1) * (k / steps)
        a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
        a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
        a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
        b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
        b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
        out.append(b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1)))
    return out


def spline_polyline(points, detail, closed=False):
    """`detail` spline samples per segment, passing through every input point.

    The control points stay exactly where the user put them; only the geometry
    between them stops being a straight line. Open lines get a mirrored end tangent,
    so the two tails leave the curve straight instead of curling.
    """
    pts = [Vector(p) for p in points]
    m = len(pts)
    if m < 3 or detail <= 1:
        return pts
    out = []
    for i in range(m if closed else m - 1):
        p1 = pts[i % m]
        p2 = pts[(i + 1) % m]
        if closed:
            p0, p3 = pts[(i - 1) % m], pts[(i + 2) % m]
        else:
            p0 = pts[i - 1] if i > 0 else p1 + (p1 - p2)
            p3 = pts[i + 2] if i + 2 < m else p2 + (p2 - p1)
        out.extend(_catmull_rom(p0, p1, p2, p3, detail))
    if not closed:
        out.append(pts[-1])
    return out


# ----------------------------------------------------------------------------
# patches
# ----------------------------------------------------------------------------
def rect_patch(center, normal, u_dir, half_u, v_range):
    """One quad on the plane (`center`, `normal`).

    Spans +-`half_u` along `u_dir` and `v_range` = (v0, v1) along `normal` x `u_dir`,
    both measured from `center`. Keeping the two axes independent is what lets a cut
    surface be exactly as wide as the stroke that was drawn while still reaching all
    the way through the model in depth.
    """
    n = Vector(normal).normalized()
    u = Vector(u_dir)
    u = u - n * u.dot(n)
    if u.length < 1e-9:
        u, _ = plane_basis(n)
    u.normalize()
    v = n.cross(u).normalized()
    c = Vector(center)
    a = c + v * v_range[0]
    b = c + v * v_range[1]
    verts = [a - u * half_u, a + u * half_u, b + u * half_u, b - u * half_u]
    return verts, [(0, 1, 2, 3)]


def plane_patch(center, normal, u_dir, size):
    """One quad of `size` x `size` centred on `center`, face normal == `normal`."""
    h = size * 0.5
    return rect_patch(center, normal, u_dir, h, (-h, h))


def ribbon_patch(points, view_dir, depth, extend, depth_range=None, detail=SURFACE_DETAIL):
    """Stroke `points` extruded along `view_dir`; both ends extended by `extend`.

    Without `depth_range` the ribbon spans -depth..+depth along the view
    direction; with `depth_range=(t0, t1)` it spans p + view*t0 .. p + view*t1.
    Face normals == tangent x view_dir (consistent along the ribbon).

    The stroke is splined to `detail` samples per segment before it is extruded, so
    the cut face is a smooth ruled surface rather than the flat facets of the control
    polyline. The extension tails are added afterwards and stay straight.
    """
    pts = [Vector(p) for p in points]
    t0, t1 = (-depth, depth) if depth_range is None else depth_range
    if len(pts) < 2:
        raise ValueError("ribbon needs at least 2 points")
    d = Vector(view_dir).normalized()
    pts = spline_polyline(pts, detail)
    if extend > 0.0:
        e0 = pts[0] - pts[1]
        e1 = pts[-1] - pts[-2]
        if e0.length > 1e-9:
            pts.insert(0, pts[0] + e0.normalized() * extend)
        if e1.length > 1e-9:
            pts.append(pts[-1] + e1.normalized() * extend)
    verts = []
    for p in pts:
        verts.append(p + d * t0)
        verts.append(p + d * t1)
    faces = []
    for i in range(len(pts) - 1):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))
    return verts, faces


def loop_flatness(points):
    """Max distance from the loop's own best fit plane, relative to the loop radius."""
    pts = [Vector(p) for p in points]
    c = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
    radius = max((p - c).length for p in pts)
    if radius < 1e-12:
        return 0.0
    n = newell_normal(pts)
    return max(abs((p - c).dot(n)) for p in pts) / radius


def _bridge_rings(outer, inner, faces):
    """Triangulate between two closed rings of vertex indices of different lengths.

    Both rings are walked by their normalised position, so the triangles stay well
    shaped even when the inner ring carries far fewer points. Winding follows the
    outer ring.
    """
    no, ni = len(outer), len(inner)
    i = j = 0
    while i < no or j < ni:
        take_outer = j >= ni or (i < no and (i + 1) / no <= (j + 1) / ni)
        if take_outer:
            faces.append((outer[i % no], outer[(i + 1) % no], inner[j % ni]))
            i += 1
        else:
            faces.append((inner[j % ni], outer[i % no], inner[(j + 1) % ni]))
            j += 1


def _relax(verts, faces, fixed, passes):
    """Move every interior vertex onto the average of its neighbours; boundary pinned.

    The fixed point of this iteration is the discrete minimal surface spanning the
    boundary: on a loop that lies in a plane it is exactly that plane, and on a loop
    drawn around the model it is the smoothest surface that still ends on the drawn
    loop - no centroid spike, no crease where two sides meet at different heights.
    """
    n = len(verts)
    if passes <= 0 or n <= fixed:
        return verts
    links = [set() for _ in range(n)]
    for f in faces:
        k = len(f)
        for i in range(k):
            a, b = f[i], f[(i + 1) % k]
            links[a].add(b)
            links[b].add(a)
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    interior = [(i, tuple(links[i]), 1.0 / max(1, len(links[i]))) for i in range(fixed, n)]
    for _ in range(passes):
        for i, nb, inv in interior:
            sx = sy = sz = 0.0
            for j in nb:
                sx += xs[j]
                sy += ys[j]
                sz += zs[j]
            xs[i] = sx * inv
            ys[i] = sy * inv
            zs[i] = sz * inv
    for i in range(fixed, n):
        verts[i] = Vector((xs[i], ys[i], zs[i]))
    return verts


def membrane_fill(points, rings=None, passes=RELAX_PASSES):
    """Span a closed loop with a smooth relaxed surface. Returns (verts, faces).

    The loop is filled with concentric rings shrinking towards its centroid (a fan of
    quads split into triangles, the innermost ring closed by a single centre vertex),
    then the interior is relaxed. The boundary vertices are the first `len(points)`
    entries of `verts` and are never moved, so the cut still lands exactly on the
    drawn loop.
    """
    bnd = [Vector(p) for p in points]
    m = len(bnd)
    if m < 3:
        raise ValueError("loop needs at least 3 points")
    centre = sum(bnd, Vector((0.0, 0.0, 0.0))) / m
    if rings is None:
        rings = max(2, min(24, int(round(m / 8.0))))
    verts = list(bnd)
    ring_idx = [list(range(m))]
    for r in range(1, rings):
        t = r / rings
        count = max(3, int(round(m * (1.0 - t))))
        idx = []
        for k in range(count):
            f = k * m / count
            i0 = int(f) % m
            p = bnd[i0].lerp(bnd[(i0 + 1) % m], f - int(f))
            idx.append(len(verts))
            verts.append(p.lerp(centre, t))
        ring_idx.append(idx)
    centre_idx = len(verts)
    verts.append(centre.copy())
    faces = []
    for r in range(len(ring_idx) - 1):
        _bridge_rings(ring_idx[r], ring_idx[r + 1], faces)
    last = ring_idx[-1]
    for k in range(len(last)):
        faces.append((last[k], last[(k + 1) % len(last)], centre_idx))
    _relax(verts, faces, m, passes)
    return verts, faces


def loop_patch(points, detail=SURFACE_DETAIL, passes=None):
    """Fill a closed loop with a smooth surface. Returns (verts, faces).

    The loop itself is splined first, so the boundary follows the control points
    without the corners a hand drawn stroke leaves behind, and the inside is spanned
    by `membrane_fill`. A loop drawn from one viewpoint comes out as flat as a plane
    cut; a loop drawn while orbiting - front, far side, back to the front - comes out
    as a smooth saddle instead of a cone, so the printed faces still mate.
    """
    pts = [Vector(p) for p in points]
    if len(pts) < 3:
        raise ValueError("loop needs at least 3 points")
    pts = dedupe_polyline(spline_polyline(pts, detail, closed=True), 1e-9)
    if len(pts) < 3:
        raise ValueError("loop is degenerate")
    if len(pts) > MAX_LOOP_SAMPLES:
        # the fill grows with the square of the boundary: keep the worst case bounded
        pts = resample_polyline(pts, MAX_LOOP_SAMPLES, closed=True)
    if passes is None:
        # a flat loop is already solved by the initial fill; a wrap-around one is not
        passes = max(8, int(round(RELAX_PASSES * min(1.0, 0.2 + loop_flatness(pts) * 4.0))))
    return membrane_fill(pts, passes=passes)


def patch_normal(verts, faces):
    """Area weighted average normal of a patch."""
    n = Vector((0.0, 0.0, 0.0))
    for f in faces:
        n += newell_normal([verts[i] for i in f]) * _poly_area(verts, f)
    if n.length < 1e-12:
        return Vector((0.0, 0.0, 1.0))
    return n.normalized()


def _poly_area(verts, f):
    pts = [verts[i] for i in f]
    total = Vector((0.0, 0.0, 0.0))
    for i in range(1, len(pts) - 1):
        total += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
    return total.length * 0.5


def patch_center(verts):
    c = Vector((0.0, 0.0, 0.0))
    for v in verts:
        c += v
    return c / max(1, len(verts))


# ----------------------------------------------------------------------------
# slab (kerf solid)
# ----------------------------------------------------------------------------
def slab_from_patch(verts, faces, thickness):
    """Closed manifold solid = patch offset +-thickness/2 along vertex normals."""
    t = max(thickness, 1e-5)
    src = bmesh.new()
    bverts = [src.verts.new(Vector(v)) for v in verts]
    for f in faces:
        try:
            src.faces.new([bverts[i] for i in f])
        except ValueError:
            pass
    src.normal_update()
    out = bmesh.new()
    top = [out.verts.new(v.co + v.normal * (t * 0.5)) for v in src.verts]
    bot = [out.verts.new(v.co - v.normal * (t * 0.5)) for v in src.verts]
    src.verts.index_update()
    for f in src.faces:
        idx = [v.index for v in f.verts]
        out.faces.new([top[i] for i in idx])
        out.faces.new([bot[i] for i in reversed(idx)])
    for f in src.faces:
        for loop in f.loops:
            if loop.edge.is_boundary:
                a = loop.vert.index
                b = loop.link_loop_next.vert.index
                out.faces.new([top[a], bot[a], bot[b], top[b]])
    src.free()
    bmesh.ops.remove_doubles(out, verts=out.verts, dist=1e-9)
    bmesh.ops.recalc_face_normals(out, faces=out.faces)
    return out
