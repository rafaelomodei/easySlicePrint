# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Real cross sections of the model, used as cut surfaces.

A plane cut used to build a rectangle sized to the mouse stroke: as wide as the line
you dragged and as deep as every ray under it happened to reach. Drawing across one
leg of a figure therefore produced a slab the size of the whole character, because
the samples that overshot the leg hit the torso and the other leg behind it.

This module takes the other route: the model already has the geometry, so the cut
surface is simply the model sliced by the plane. `plane_section` bisects a copy of
the evaluated mesh, fills the resulting loops, splits the fill into connected
islands - one per region the plane crosses, an annulus for a hollow shell - and
hands back the islands the stroke actually ran across, grown outwards by a hair so
the boolean never has to resolve coplanar faces.

"The islands the stroke ran across" is the whole rule, and it has to be taken
literally. The cut plane contains the view direction, so on screen the whole plane
collapses onto the line that was drawn: an island is under the stroke exactly when
its span along the drawn direction overlaps the stroke's. Picking the single island
nearest the middle of the line instead looks the same on a figure with one limb in
the way and is wrong on everything else - a plane through a saint's chest also
crosses the sword and the wings, and leaving those uncut means the two halves stay
joined through them and the boolean reports that it did not split anything.

Plane cuts use this directly. Curve cuts use the one dimensional form, `band_around`,
through `plan.ribbon_surfaces`; freehand loops need none of it. See the note at the
bottom of this file for where each of the three stands.
"""

import time

import bmesh
from mathutils import Vector

from . import mesh_utils, surfaces

# The source mesh is bisected destructively, so every section needs its own copy.
# Re-reading a 500k figure out of Blender on every preview refresh is what would make
# dragging a cut plane crawl, so the untouched original is kept for a moment and only
# copied. The window is short on purpose: the cache only has to survive one drag, and
# anything longer risks slicing a mesh the user has since edited.
CACHE_SECONDS = 2.0
_cache = {"key": None, "bm": None, "time": 0.0}


def _cache_key(obj):
    mesh = obj.data
    return (
        obj.name,
        len(mesh.vertices),
        len(mesh.polygons),
        len(obj.modifiers),
        tuple(round(v, 7) for row in obj.matrix_world for v in row),
    )


def free_cache():
    if _cache["bm"] is not None:
        _cache["bm"].free()
    _cache["key"] = None
    _cache["bm"] = None
    _cache["time"] = 0.0


def source_bmesh(obj, depsgraph=None):
    """A private world space bmesh of `obj` as evaluated. The caller frees the result."""
    key = _cache_key(obj)
    now = time.monotonic()
    if _cache["key"] != key or _cache["bm"] is None or now - _cache["time"] > CACHE_SECONDS:
        free_cache()
        bm = bmesh.new()
        if depsgraph is not None:
            bm.from_object(obj, depsgraph)
        else:
            bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        _cache["key"] = key
        _cache["bm"] = bm
    _cache["time"] = now
    return _cache["bm"].copy()


# ----------------------------------------------------------------------------
# islands
# ----------------------------------------------------------------------------
def _islands(faces):
    """Group `faces` into connected components (shared edges). -> list of face lists."""
    seen = set()
    out = []
    for start in faces:
        if start.index in seen:
            continue
        seen.add(start.index)
        group = [start]
        stack = [start]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for nb in e.link_faces:
                    if nb.index not in seen:
                        seen.add(nb.index)
                        group.append(nb)
                        stack.append(nb)
        out.append(group)
    return out


def _island_distance(group, point):
    return min((v.co - point).length for f in group for v in f.verts)


def _island_span(group, origin, axis):
    """The island's extent along `axis`, measured from `origin`. -> (lo, hi)"""
    ts = [(v.co - origin).dot(axis) for f in group for v in f.verts]
    return min(ts), max(ts)


class SectionResult(tuple):
    """(verts, faces) plus what the section had to say about the model.

    `islands` is how many separate regions the plane crosses, `kept` how many ended
    up in the surface. When those differ the cut may well remove material without
    separating anything, because the part stays joined through the regions that were
    left out - which is the one thing worth telling the user about.

    `cutter` is the quad the boolean is actually given (see `clip_rect`). The section
    is what the user sees and what the connector is measured against; it is a bad
    shape to subtract with, because its rim runs along the model's surface for its
    whole length and an exact boolean asked to resolve that many near tangent
    intersections comes back with slivers - or with a part that never came apart.
    """

    def __new__(cls, verts, faces, islands=1, kept=1, cutter=None):
        self = super().__new__(cls, (verts, faces))
        self.islands = islands
        self.kept = kept
        self.cutter = cutter
        return self

    @property
    def verts(self):
        return self[0]

    @property
    def faces(self):
        return self[1]


# ----------------------------------------------------------------------------
# outward offset
# ----------------------------------------------------------------------------
def grow_section(verts, faces, margin, normal):
    """Push the boundary of a flat patch outwards, in its own plane, by `margin`.

    A section that ends exactly on the model surface leaves the boolean with coplanar
    faces to resolve, which is where exact booleans produce slivers or give up. The
    offset follows each boundary loop's own winding, so the outer loop of a hollow
    section grows outwards and the inner loop grows into the hole: both directions
    move away from the material. `normal` fixes which way "outwards" is - a recalc on
    an open patch is free to settle on either side of the plane.
    """
    if margin <= 0.0:
        return verts, faces
    bm = bmesh.new()
    bverts = [bm.verts.new(Vector(v)) for v in verts]
    bm.verts.index_update()
    for f in faces:
        try:
            bm.faces.new([bverts[i] for i in f])
        except ValueError:
            pass
    if not bm.faces:
        bm.free()
        return verts, faces
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ref = Vector(normal).normalized()
    if sum(f.normal.dot(ref) * f.calc_area() for f in bm.faces) < 0.0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    push = {}
    for f in bm.faces:
        fn = f.normal
        for loop in f.loops:
            if not loop.edge.is_boundary:
                continue
            a = loop.vert
            b = loop.link_loop_next.vert
            d = b.co - a.co
            if d.length < 1e-12:
                continue
            outward = d.normalized().cross(fn)
            if outward.length < 1e-12:
                continue
            outward.normalize()
            for v in (a, b):
                push[v.index] = push.get(v.index, Vector((0.0, 0.0, 0.0))) + outward
    out = [Vector(v) for v in verts]
    for i, acc in push.items():
        if acc.length > 1e-12:
            out[i] = out[i] + acc.normalized() * margin
    bm.free()
    return out, faces


def _disjoint(span, lo, hi):
    return span[1] < lo or span[0] > hi


def _uv_box(points, co, u, v):
    us = [(p - co).dot(u) for p in points]
    vs = [(p - co).dot(v) for p in points]
    return [min(us), max(us), min(vs), max(vs)]


def clip_rect(keep, skip, co, normal, u_axis, bounds, pad):
    """A quad on the plane holding every kept region and no skipped one.

    This is what the boolean subtracts. It runs out past the model on every side that
    has nothing to protect, and only pulls in where a region has to be spared - and
    then it stops in the middle of the empty gap between the two, never on the
    surface. That is the whole trick: a rim in free space is a cut the exact solver
    gets right every time, and the result is identical to subtracting the section
    itself, because the extra area covers nothing but air.

    `keep` and `skip` are lists of world space point lists, one per island. Returns
    (verts, faces), or None when no rectangle separates them - regions interleaved
    along both axes, where only the section's own outline will do.
    """
    n = Vector(normal).normalized()
    u = Vector(u_axis) - n * Vector(u_axis).dot(n)
    if u.length < 1e-9:
        u, _ = surfaces.plane_basis(n)
    u.normalize()
    v = n.cross(u).normalized()
    inner = _uv_box([p for isl in keep for p in isl], co, u, v)
    lim = [bounds[0] - pad, bounds[1] + pad, bounds[2] - pad, bounds[3] + pad]
    for isl in skip:
        box = _uv_box(isl, co, u, v)
        # the sides that can shut this region out, and how much room each has to spare
        options = []
        if box[1] < inner[0]:
            options.append((0, inner[0] - box[1], (inner[0] + box[1]) * 0.5))
        if box[0] > inner[1]:
            options.append((1, box[0] - inner[1], (inner[1] + box[0]) * 0.5))
        if box[3] < inner[2]:
            options.append((2, inner[2] - box[3], (inner[2] + box[3]) * 0.5))
        if box[2] > inner[3]:
            options.append((3, box[2] - inner[3], (inner[3] + box[2]) * 0.5))
        if not options:
            return None
        side, _gap, mid = max(options, key=lambda o: o[1])
        lim[side] = max(lim[side], mid) if side in (0, 2) else min(lim[side], mid)
    if lim[0] > inner[0] or lim[1] < inner[1] or lim[2] > inner[2] or lim[3] < inner[3]:
        return None
    verts = [
        co + u * lim[0] + v * lim[2],
        co + u * lim[1] + v * lim[2],
        co + u * lim[1] + v * lim[3],
        co + u * lim[0] + v * lim[3],
    ]
    return verts, [(0, 1, 2, 3)]


# ----------------------------------------------------------------------------
# the section itself
# ----------------------------------------------------------------------------
def plane_section(obj, plane_co, plane_no, span=None, reference=None, margin=0.0, depsgraph=None, epsilon=1e-6):
    """The model's own cross section on the plane (`plane_co`, `plane_no`).

    `span` is the stroke: `(axis, lo, hi)` measured from `plane_co` along a world
    direction lying in the plane. Every island overlapping it survives - draw across
    one leg and the other is left alone, draw across the whole figure and the sword
    and the wings come with it. `reference` is the fallback when the span matches
    nothing (a line drawn off the model): the island nearest that point. With neither,
    every crossed island is returned.

    Returns a `SectionResult` - a (verts, faces) pair in world space that also carries
    how many islands the plane crossed and the quad the boolean should subtract - or
    None when the plane misses the model or the section cannot be filled (an open or
    non manifold mesh may not close).
    """
    n = Vector(plane_no)
    if n.length < 1e-12:
        return None
    n.normalize()
    co = Vector(plane_co)
    bm = source_bmesh(obj, depsgraph)
    try:
        bmesh.ops.bisect_plane(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            dist=epsilon,
            plane_co=co,
            plane_no=n,
            clear_inner=True,
            clear_outer=True,
        )
        # only the loops lying on the plane are left; weld them so the fill sees
        # closed loops even where two faces met the plane at the same vertex
        if not bm.edges:
            return None
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=epsilon)
        loose = [v for v in bm.verts if not v.link_edges]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        edges = list(bm.edges)
        if not edges:
            return None
        # `triangle_fill` is the scanfill behind edit mode's F: it spans a whole edge
        # net at once and treats a loop nested inside another as a hole, which is what
        # keeps a hollow section an annulus instead of a filled disc
        bmesh.ops.triangle_fill(bm, edges=edges, use_beauty=True, use_dissolve=False, normal=n)
        if not bm.faces:
            return None
        bm.faces.index_update()
        all_groups = _islands(list(bm.faces))
        groups = all_groups
        total = len(groups)
        if total > 1:
            if span is not None:
                axis, lo, hi = Vector(span[0]).normalized(), span[1], span[2]
                touched = [g for g in groups if not _disjoint(_island_span(g, co, axis), lo, hi)]
                if touched:
                    groups = touched
                elif reference is not None:
                    groups = [min(groups, key=lambda g: _island_distance(g, Vector(reference)))]
            elif reference is not None:
                groups = [min(groups, key=lambda g: _island_distance(g, Vector(reference)))]
        kept = len(groups)
        chosen = {id(g) for g in groups}
        keep = {f.index for g in groups for f in g}
        cutter = _cutter_quad(obj, groups, [g for g in all_groups if id(g) not in chosen], co, n, span)
        drop = [f for f in bm.faces if f.index not in keep]
        if drop:
            bmesh.ops.delete(bm, geom=drop, context='FACES')
        if not bm.faces:
            return None
        bmesh.ops.dissolve_limit(bm, angle_limit=1e-4, verts=list(bm.verts), edges=list(bm.edges))
        if not bm.faces:
            return None
        bm.verts.index_update()
        used = {v.index for f in bm.faces for v in f.verts}
        remap = {}
        verts = []
        for v in bm.verts:
            if v.index in used:
                remap[v.index] = len(verts)
                verts.append(v.co.copy())
        faces = [tuple(remap[v.index] for v in f.verts) for f in bm.faces]
        if not faces:
            return None
        verts, faces = grow_section(verts, faces, margin, n)
        return SectionResult(verts, faces, islands=total, kept=kept, cutter=cutter)
    finally:
        bm.free()


def _cutter_quad(obj, keep, skip, co, n, span):
    """`clip_rect` for the islands as bmesh face groups, sized to the object."""
    mn, mx = mesh_utils.object_world_bounds(obj)
    axis = Vector(span[0]) if span is not None else surfaces.plane_basis(n)[0]
    u = Vector(axis) - n * Vector(axis).dot(n)
    if u.length < 1e-9:
        u, _ = surfaces.plane_basis(n)
    u.normalize()
    v = n.cross(u).normalized()
    corners = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    bounds = _uv_box(corners, co, u, v)
    pad = max((mx - mn).length * 0.02, 1e-4)
    return clip_rect(
        [[v.co.copy() for f in g for v in f.verts] for g in keep],
        [[v.co.copy() for f in g for v in f.verts] for g in skip],
        co,
        n,
        u,
        bounds,
        pad,
    )


# ----------------------------------------------------------------------------
# runs of material along one axis (curve cuts)
# ----------------------------------------------------------------------------
def merge_runs(intervals, tol=0.0):
    """Sorted, merged (lo, hi) runs from overlapping or touching intervals."""
    spans = sorted((min(a, b), max(a, b)) for a, b in intervals)
    out = []
    for lo, hi in spans:
        if out and lo <= out[-1][1] + tol:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def band_around(intervals, anchor, pad, tol=0.0):
    """The run of material holding `anchor`, widened into the empty space beside it.

    The one dimensional form of `clip_rect`, and it exists for the same reason. A
    curve cut used to take one depth range for its whole length, from the furthest
    ray hit anywhere under the stroke, so a line drawn across a figure's near leg
    reached through the far one as well. Taking only the run the stroke is actually
    standing on stops that, and stopping half way into the gap - rather than on the
    surface - is what keeps the boolean's rim in free space.

    `intervals` are (lo, hi) pairs of "inside the model" along one axis. Returns
    (lo, hi), or None when there is nothing to stand on.
    """
    runs = merge_runs(intervals, tol)
    if not runs:
        return None
    inside = [r for r in runs if r[0] - tol <= anchor <= r[1] + tol]
    if inside:
        run = max(inside, key=lambda r: r[1] - r[0])
    else:
        run = min(runs, key=lambda r: min(abs(r[0] - anchor), abs(r[1] - anchor)))
    i = runs.index(run)
    before = pad if i == 0 else min(pad, (run[0] - runs[i - 1][1]) * 0.5)
    after = pad if i == len(runs) - 1 else min(pad, (runs[i + 1][0] - run[1]) * 0.5)
    return run[0] - before, run[1] + after


# ----------------------------------------------------------------------------
# largest circle that fits in the section (connector placement)
# ----------------------------------------------------------------------------
def _boundary_wall(verts, faces, normal, height):
    """A thin wall standing on the patch's boundary, as a BVH.

    `find_nearest` against it is the in-plane distance from a point to the edge of
    the section - the one measurement the connector needs, and one that a BVH does
    in C instead of a Python loop over every boundary segment.
    """
    bm = bmesh.new()
    bverts = [bm.verts.new(Vector(v)) for v in verts]
    for f in faces:
        try:
            bm.faces.new([bverts[i] for i in f])
        except ValueError:
            pass
    n = Vector(normal).normalized() * height
    quads_v, quads_f = [], []
    for e in bm.edges:
        if not e.is_boundary:
            continue
        a, b = e.verts[0].co, e.verts[1].co
        i = len(quads_v)
        quads_v.extend((a + n, b + n, b - n, a - n))
        quads_f.append((i, i + 1, i + 2, i + 3))
    bm.free()
    if not quads_f:
        return None
    return mesh_utils.bvh_from_pydata(quads_v, quads_f)


def _face_samples(verts, faces, rows=3):
    """Centroid of every face plus a small barycentric grid inside it."""
    out = []
    for f in faces:
        ring = [Vector(verts[i]) for i in f]
        c = sum(ring, Vector((0.0, 0.0, 0.0))) / len(ring)
        out.append(c)
        for i in range(1, rows):
            t = i / rows
            for p in ring:
                out.append(c.lerp(p, t))
    return out


def inscribed_circle(verts, faces, normal, resolution=40, refinements=4):
    """Largest circle that fits inside a flat patch -> (centre, diameter).

    This is what sizes and places a connector once the cut surface is the model's real
    cross section: the biggest pin that still has material all around it, sitting where
    that material is thickest. The old estimate marched rays out from a guessed centre
    and then took the middle of their bounding box, which on any section that is not
    roughly convex walks the pin straight out of the thick part - a plane through a
    figure's chest catches the sword and the wing too, and the pin ends up a 3 mm stub
    out on the blade. A section knows its own shape, so ask it instead.

    Points sampled across every face seed the search - which is also all a curved
    patch (a curve cut's ribbon, a freehand membrane) ever gets, since a grid laid out
    on a plane lands nowhere near it. A flat section then gets a coarse grid over its
    own extent and a few rounds of refinement, which is what finds the middle of a
    large empty area that no single face centroid sits in.
    """
    if not verts or not faces:
        return None
    n = Vector(normal).normalized()
    u, v = surfaces.plane_basis(n)
    patch = mesh_utils.bvh_from_pydata(verts, faces)
    extent = section_extent(verts)
    wall = _boundary_wall(verts, faces, n, max(extent * 1e-3, 1e-6))
    if wall is None:
        return None
    origin = surfaces.patch_center(verts)
    us = [(Vector(p) - origin).dot(u) for p in verts]
    vs = [(Vector(p) - origin).dot(v) for p in verts]
    inside_eps = max(extent * 1e-4, 1e-7)

    def score(p):
        loc, _nor, _i, _d = patch.find_nearest(p)
        if loc is None or (loc - p).length > inside_eps:
            return -1.0
        loc, _nor, _i, _d = wall.find_nearest(p)
        return -1.0 if loc is None else (loc - p).length

    best, best_d = None, -1.0
    for p in _face_samples(verts, faces):  # always on the patch, whatever the grid does
        d = score(p)
        if d > best_d:
            best, best_d = p, d
    lo_u, hi_u, lo_v, hi_v = min(us), max(us), min(vs), max(vs)
    for _ in range(refinements + 1):
        step_u = (hi_u - lo_u) / max(1, resolution)
        step_v = (hi_v - lo_v) / max(1, resolution)
        for i in range(resolution + 1):
            for j in range(resolution + 1):
                p = origin + u * (lo_u + step_u * i) + v * (lo_v + step_v * j)
                d = score(p)
                if d > best_d:
                    best, best_d = p, d
        if best is None:
            return None
        # zoom in on the best sample; two cells wide, so the true optimum stays inside
        cu, cv = (best - origin).dot(u), (best - origin).dot(v)
        lo_u, hi_u = cu - step_u, cu + step_u
        lo_v, hi_v = cv - step_v, cv + step_v
        resolution = max(6, resolution // 3)
    if best is None or best_d <= 0.0:
        return None
    return best, best_d * 2.0


def section_extent(verts):
    """Longest edge of the section's bounding box - a scale for margins and messages."""
    if not verts:
        return 0.0
    mn = Vector((min(v[0] for v in verts), min(v[1] for v in verts), min(v[2] for v in verts)))
    mx = Vector((max(v[0] for v in verts), max(v[1] for v in verts), max(v[2] for v in verts)))
    return max(mx - mn)


# ----------------------------------------------------------------------------
# where the three tools stand
# ----------------------------------------------------------------------------
# Plane cuts section the model here; curve cuts get the same treatment from
# `plan.ribbon_surfaces`, which measures the runs of material under every column of
# the ribbon and hands them to `band_around` - the one dimensional `clip_rect`.
# Freehand loops need neither: the loop is drawn on the surface and pushed a hair
# outside it, so the membrane it spans already is the printed cut face and already
# has its rim in free space. All three now measure their connector with
# `inscribed_circle` on that face.
#
# What is still approximate, in one place only: a curve cut gives each ribbon column
# a single span, from the first entry to the last exit of the material under it. A
# column crossing a hollow limb therefore covers the cavity as well. That is right for
# the cutter and slightly generous for the preview, where a plane cut would show the
# cavity as a hole. Fixing it means letting one column carry several spans, which
# `surfaces.ribbon_patch` would have to grow a second index for.
