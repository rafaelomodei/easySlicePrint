"""Cut surfaces ("patches") and the kerf slab built from them.

A patch is a simple open mesh given as (verts, faces) in world space:
  * plane_patch   -> straight cut (one quad)
  * ribbon_patch  -> curved cut: the stroke extruded along the view direction
  * loop_patch    -> freehand cut: a closed loop drawn on the surface, filled

`slab_from_patch` thickens a patch by the cut gap (kerf) into a closed solid
that is subtracted from the model with a boolean.
"""

import bmesh
from mathutils import Vector


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


# ----------------------------------------------------------------------------
# patches
# ----------------------------------------------------------------------------
def plane_patch(center, normal, u_dir, size):
    """One quad of `size` x `size` centred on `center`, face normal == `normal`."""
    n = Vector(normal).normalized()
    u = Vector(u_dir)
    u = u - n * u.dot(n)
    if u.length < 1e-9:
        u, _ = plane_basis(n)
    u.normalize()
    v = n.cross(u).normalized()
    h = size * 0.5
    c = Vector(center)
    verts = [c - u * h - v * h, c + u * h - v * h, c + u * h + v * h, c - u * h + v * h]
    return verts, [(0, 1, 2, 3)]


def ribbon_patch(points, view_dir, depth, extend, depth_range=None):
    """Stroke `points` extruded along `view_dir`; both ends extended by `extend`.

    Without `depth_range` the ribbon spans -depth..+depth along the view
    direction; with `depth_range=(t0, t1)` it spans p + view*t0 .. p + view*t1.
    Face normals == tangent x view_dir (consistent along the ribbon).
    """
    pts = [Vector(p) for p in points]
    t0, t1 = (-depth, depth) if depth_range is None else depth_range
    if len(pts) < 2:
        raise ValueError("ribbon needs at least 2 points")
    d = Vector(view_dir).normalized()
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


def loop_patch(points):
    """Fill a closed loop with triangles. Returns (verts, faces)."""
    pts = [Vector(p) for p in points]
    if len(pts) < 3:
        raise ValueError("loop needs at least 3 points")
    bm = bmesh.new()
    bverts = [bm.verts.new(p) for p in pts]
    try:
        face = bm.faces.new(bverts)
    except ValueError:
        bm.free()
        raise ValueError("loop is degenerate") from None
    bmesh.ops.triangulate(bm, faces=[face], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    verts = [v.co.copy() for v in bm.verts]
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, faces


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
