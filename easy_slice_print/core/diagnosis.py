# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Where a cut that did not split the part went wrong, as a map on the cut surface.

The boolean removed material and the part still came out in one piece. Somewhere the
two halves are still joined, and the user has to find that somewhere to fix the cut:
a rim segment that never left the surface, a membrane that stops inside the material,
a plane that ends half way through. `diagnose` finds it from what the boolean actually
produced, and `Diagnosis.score_points` then scores any point against it: 0 where the
halves stay joined, 1 well clear of it, so the cut surface can be painted in a
gradient from red through orange to green.

The halves are found from the slot itself. Every vertex of the result that sits on
one of the new cut faces - within the kerf of the cutter - is on a known side of the
cutter: the side its face looks at. Those are the seeds. Two fronts then flood the
result's edge graph, one from each side, and never cross the slot, since the slot
has no edges across it. Where the fronts meet is material that connects the two
halves without going through the cut, and that is the bridge to be painted red. A
slot that stops inside the material meets at its own end wall; a plane that also
crossed a sword meets on the sword; a rim that welded to the surface meets along the
weld.

A cutter that never carved a face on both sides of itself did not cut at all - it
missed the model, or only grazed it - and there is no bridge to find: `cut` is False
and the whole cut surface is the problem.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import mesh_utils

SEED_REACH = 0.75  # of the kerf: a slot wall sits half a kerf from the cutter
RADIUS_OF_CUT = 0.35  # the red blob, as a fraction of the size of the face that was cut ...
RADIUS_OF_DIAG = 0.06  # ... and never smaller than this fraction of the model
RADIUS_CAP = 0.25  # of the model: a blob larger than this says nothing


@dataclass
class Diagnosis:
    """One failed cut: where the halves stay joined, found on the mesh the boolean left (world space)."""

    bridge: list  # centres of the faces where the two halves meet without going through the cut
    radius: float  # distance over which a score goes from 0 to 1
    cut: bool  # the cutter carved a face on both of its sides
    seeds: tuple = (0, 0)  # vertices found on the cut faces, per side
    surface: tuple = ((), ())  # (verts, faces) to paint, world space: the cut surface the user sees
    _bvh: BVHTree | None = field(default=None, repr=False)  # the bridge faces

    def score_points(self, points):
        """0..1 for any point in world space: 0 on the bridge, 1 at `radius` from it and beyond.

        All 0 when nothing was cut: there is no bridge, and all of the cut surface is the problem.
        """
        if not self.cut or self._bvh is None:
            return [0.0] * len(points)
        return [_score(self._bvh, Vector(p), self.radius) for p in points]


def _score(bvh, point, radius):
    """0 on a bridge face, 1 at `radius` from the nearest one and beyond."""
    loc, _nor, _idx, dist = bvh.find_nearest(point, radius)
    return 1.0 if loc is None else min(1.0, dist / radius)


def nothing_cut(shown_verts, shown_faces):
    """The diagnosis of a boolean that produced nothing: all of the cut is the problem."""
    return Diagnosis([], 1e-6, False, (0, 0), (list(shown_verts), list(shown_faces)))


def _gather(meshes):
    """Every mesh as one vertex/edge/triangle set, indices offset per mesh."""
    coords, edges, tris = [], [], []
    base = 0
    for me in meshes:
        n = len(me.vertices)
        if n == 0:
            continue
        co = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        coords.append(co.reshape(n, 3))
        ne = len(me.edges)
        ed = np.empty(ne * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", ed)
        edges.append(ed.reshape(ne, 2) + base)
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        tr = np.empty(nt * 3, dtype=np.int64)
        me.loop_triangles.foreach_get("vertices", tr)
        tris.append(tr.reshape(nt, 3) + base)
        base += n
    if base == 0:
        return None
    return (
        np.concatenate(coords),
        np.concatenate(edges) if edges else np.empty((0, 2), dtype=np.int64),
        np.concatenate(tris) if tris else np.empty((0, 3), dtype=np.int64),
    )


def _seed_labels(coords, bvh, reach):
    """+1 / -1 for a vertex on a cut face, by the side of the cutter it looks at; else 0."""
    n = len(coords)
    labels = np.zeros(n, dtype=np.int8)
    for i in range(n):
        p = Vector(coords[i])
        loc, nor, _idx, _dist = bvh.find_nearest(p, reach)
        if loc is None:
            continue
        labels[i] = 1 if (p - loc).dot(nor) >= 0.0 else -1
    return labels


def _flood(labels, edges):
    """Grow every label over the edge graph, one hop per round, until it meets another.

    Multi-source breadth first: all the seeds start together, the fronts advance at the
    same pace, and a vertex takes the label of whichever front reaches it first. Where
    two fronts of different sign end up on the two ends of one edge is where they met.
    """
    n = len(labels)
    if n == 0 or len(edges) == 0:
        return labels
    both = np.concatenate((edges, edges[:, ::-1]))
    order = np.argsort(both[:, 0], kind='stable')
    nbr = both[order, 1].tolist()
    starts = np.searchsorted(both[order, 0], np.arange(n + 1)).tolist()
    lab = labels.tolist()
    queue = deque(i for i in range(n) if lab[i] != 0)
    while queue:
        v = queue.popleft()
        mine = lab[v]
        for j in nbr[starts[v] : starts[v + 1]]:
            if lab[j] == 0:
                lab[j] = mine
                queue.append(j)
    return np.asarray(lab, dtype=np.int8)


def blob_radius(cut_extent, diag):
    """How far from the bridge the red fades to green: sized to the cut, floored to the model.

    `cut_extent` is the size of the face the boolean did carve - the reach of the seed
    vertices - not the cutter's, which runs out past the model.
    """
    r = max(RADIUS_OF_CUT * cut_extent, RADIUS_OF_DIAG * diag)
    return max(min(r, RADIUS_CAP * diag), 1e-6)


def _bridge_faces(tris, labels):
    """The faces the two fronts share: material joining the halves without crossing the cut."""
    la, lb, lc = labels[tris[:, 0]], labels[tris[:, 1]], labels[tris[:, 2]]
    return tris[(la * lb < 0) | (lb * lc < 0) | (lc * la < 0)]


def _bridge_bvh(coords, faces):
    """A BVH over the bridge faces alone, for exact distances to them.

    Exact matters on a coarse mesh: a rod with one edge from end to end, a slot whose
    end wall is one quad. The whole face is bridge there, not just its corners.
    """
    used, local = np.unique(faces, return_inverse=True)
    verts = [Vector(v) for v in coords[used]]
    return BVHTree.FromPolygons(verts, [tuple(f) for f in local.reshape(-1, 3)])


def diagnose(meshes, cutter_verts, cutter_faces, gap, shown=None):
    """Find where a failed cut left the halves joined, against the cutter it was made with.

    `meshes` are the loose pieces of the boolean result, in world space; there is
    usually one. `shown` is the (verts, faces) the diagnosis is to be painted on - the
    surface the user sees - when that is not the cutter itself. Returns a `Diagnosis`,
    or None when the seeds sit on both sides of the cutter but never meet - the pieces
    are separate and the failure is elsewhere, so there is nothing to point at.
    """
    got = _gather(meshes)
    if got is None:
        return None
    coords, edges, tris = got
    mn, mx = coords.min(axis=0), coords.max(axis=0)
    diag = max(float(np.linalg.norm(mx - mn)), 1e-6)
    bvh = mesh_utils.bvh_from_pydata(cutter_verts, cutter_faces)
    reach = max(gap * SEED_REACH, diag * 1e-4)
    seeds = _seed_labels(coords, bvh, reach)
    on_a, on_b = int(np.sum(seeds > 0)), int(np.sum(seeds < 0))
    sv, sf = shown if shown is not None else (cutter_verts, cutter_faces)
    surface = (list(sv), list(sf))
    if on_a == 0 or on_b == 0:
        return Diagnosis([], blob_radius(0.0, diag), False, (on_a, on_b), surface)
    carved = coords[seeds != 0]
    radius = blob_radius(float(np.linalg.norm(carved.max(axis=0) - carved.min(axis=0))), diag)
    labels = _flood(seeds, edges)
    joined = _bridge_faces(tris, labels)
    if len(joined) == 0:
        return None
    bvh = _bridge_bvh(coords, joined)
    bridge = [Vector(c) for c in (coords[joined[:, 0]] + coords[joined[:, 1]] + coords[joined[:, 2]]) / 3.0]
    return Diagnosis(bridge, radius, True, (on_a, on_b), surface, bvh)
