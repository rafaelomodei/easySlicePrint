# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""High level cut pipeline: split a mesh by one or two cut surfaces, add
connectors, optional remesh, create the result objects."""

import math
import time
from dataclasses import dataclass, field

import bpy
from mathutils import Matrix, Vector

from . import connectors, mesh_utils, surfaces


class CutError(Exception):
    pass


@dataclass
class ContactSpec:
    verts: list
    faces: list
    add_pin: bool = True
    pin_matrix: Matrix | None = None  # world; +Z points into the socket part
    shape: str = 'CYLINDER'
    custom_obj: object = None
    # The connector mesh as the plan shows it (unit space, edit-mode changes included).
    # When set it is the shape that gets built; `shape`/`custom_obj` only say how to
    # make one from scratch, which is all Quick mode has.
    pin_mesh: object = None
    regions_skipped: int = 0  # regions the plane crosses that this surface leaves uncut


@dataclass
class CutSpec:
    contacts: list[ContactSpec] = field(default_factory=list)
    gap: float = 0.0  # BU
    clearance: float = 0.0  # BU
    tip_extra: float = 0.0  # BU (socket depth extra at the tip)
    pin_side: str = 'A'  # 'A' -> part on the + side of the surface carries the pin
    solver: str = 'AUTO'
    remesh: bool = False
    remesh_voxel: float = 0.0  # BU
    remesh_adaptivity: float = 0.0
    remesh_smooth: bool = False


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def drain(generator):
    """Run a step generator to the end and return its value (synchronous callers)."""
    while True:
        try:
            next(generator)
        except StopIteration as stop:
            return stop.value


def side_sign(point, bvh):
    loc, nor, _idx, _dist = bvh.find_nearest(point)
    if loc is None:
        return 1
    return 1 if (point - loc).dot(nor) >= 0.0 else -1


def mesh_side(mesh, bvh, samples=600):
    """Which side of the cut surface a separated piece came off. -> +1 or -1

    One centroid test is enough for a plane cut, whose surface is flat and reaches past
    the whole model. It is not enough for a freehand membrane: a piece's centroid can
    sit well off the end of the membrane - a leg's centroid is half the model away from
    a loop drawn round its thigh - and out there the nearest facet's normal says nothing
    about which half the piece belongs to, so both halves come back on the same side and
    a cut that worked is reported as one that did not split the part.

    The vertices sitting ON the new cut face do know, and they are the ones closest to
    the surface, so every vertex votes with a weight that falls off with its distance.
    """
    verts = mesh.vertices
    n = len(verts)
    if n == 0:
        return 1
    step = max(1, n // samples)
    total = 0.0
    for i in range(0, n, step):
        p = verts[i].co
        loc, nor, _idx, dist = bvh.find_nearest(p)
        if loc is None:
            continue
        w = 1.0 / (dist * dist + 1e-6)
        total += w if (p - loc).dot(nor) >= 0.0 else -w
    if total == 0.0:
        return side_sign(mesh_utils.mesh_centroid(mesh), bvh)
    return 1 if total > 0.0 else -1


def still_joined_message(spec):
    """Why the boolean removed material and the part still came out in one piece.

    Almost always because the plane crosses the model somewhere the line did not: a
    wing, a sword, a cloak, the base under the feet. Those regions are left uncut on
    purpose - it is what keeps a cut across one leg from taking the other with it -
    but the two halves stay joined through them, so the split never happens. Saying
    how many were left out turns an unexplainable failure into one instruction.
    """
    skipped = max((c.regions_skipped for c in spec.contacts), default=0)
    if skipped:
        many = skipped > 1
        return (
            "The cut removed material but the part is still in one piece: the cut plane also crosses "
            f"{skipped} other region{'s' if many else ''} of the model (a wing, a base, an arm) that your "
            f"line did not run across, and the two halves stay joined through {'them' if many else 'it'}. "
            f"Draw the cut line across {'those regions' if many else 'that region'} too."
        )
    return "The cut surface does not split this part in two. Make the cut cross the whole part."


def side_labels(centroid_a, centroid_b):
    d = centroid_a - centroid_b
    ax = max(range(3), key=lambda i: abs(d[i]))
    if ax == 2:
        return ("UPPER", "LOWER") if d.z >= 0 else ("LOWER", "UPPER")
    if ax == 0:
        return ("RIGHT", "LEFT") if d.x >= 0 else ("LEFT", "RIGHT")
    return ("BACK", "FRONT") if d.y >= 0 else ("FRONT", "BACK")


def protrude_direction(surface_normal, pin_side):
    """Surface normal points to side A. The pin protrudes into the socket part."""
    n = Vector(surface_normal).normalized()
    return -n if pin_side == 'A' else n


# ----------------------------------------------------------------------------
# pin placement estimate (cheap, ray based; used for previews AND builds)
# ----------------------------------------------------------------------------
def estimate_pin_frame(obj, depsgraph, patch_bvh, diag, surface_point=None, through_dir=None, center_hint=None):
    """-> (center, surface_normal, inscribed_diameter) in world space.

    Either give `center_hint` (a point believed to be inside the part, e.g. the
    centroid of a freehand loop) or `surface_point` + `through_dir`: where the
    user's stroke touched the model and the direction that goes through it.
    The centre is refined with in-plane rays so it sits in the middle of the
    cross-section; the shortest ray gives the inscribed diameter.
    """
    if center_hint is not None:
        center = Vector(center_hint)
    else:
        d = Vector(through_dir).normalized()
        start = Vector(surface_point) + d * (diag * 1e-4)
        hit, loc, _n, _dist = mesh_utils.object_ray_cast(obj, start, d, depsgraph, max_dist=diag * 4.0)
        center = (Vector(surface_point) + loc) * 0.5 if hit else Vector(surface_point)
    loc_p, nor_p, _i, _d = patch_bvh.find_nearest(center)
    if loc_p is None:
        return center, Vector((0.0, 0.0, 1.0)), diag * 0.1
    center = loc_p
    normal = nor_p.normalized()
    inscribed = None
    for _ in range(2):
        u, v = surfaces.plane_basis(normal)
        hits = []
        for k in range(16):
            ang = 2.0 * math.pi * k / 16.0
            rd = (u * math.cos(ang) + v * math.sin(ang)).normalized()
            h, hl, _hn, _hd = mesh_utils.object_ray_cast(obj, center, rd, depsgraph, max_dist=diag * 2.0)
            if h:
                hits.append(hl)
        if len(hits) < 8:
            break
        mn = Vector((min(h.x for h in hits), min(h.y for h in hits), min(h.z for h in hits)))
        mx = Vector((max(h.x for h in hits), max(h.y for h in hits), max(h.z for h in hits)))
        new_center = (mn + mx) * 0.5
        loc_p, nor_p, _i, _d = patch_bvh.find_nearest(new_center)
        if loc_p is not None:
            center = loc_p
            normal = nor_p.normalized()
        inscribed = min((h - center).length for h in hits) * 2.0
    if inscribed is None or inscribed <= 1e-9:
        inscribed = diag * 0.1
    return center, normal, inscribed


# ----------------------------------------------------------------------------
# pipeline
# ----------------------------------------------------------------------------
def split_mesh_steps(context, mesh, spec):
    """Generator form of `split_mesh`.

    Yields a short label BEFORE each heavy step and returns (mesh_a, mesh_b).
    Every yield hands control back to Blender's event loop, which is what keeps
    the window answering the compositor's "are you alive?" pings during a cut.
    """
    work = mesh
    orphans = []  # intermediates to drop if the job is cancelled part way through
    total = len(spec.contacts)
    try:
        for i, c in enumerate(spec.contacts):
            yield f"cutting surface {i + 1}/{total}" if total > 1 else "cutting surface"
            slab_bm = surfaces.slab_from_patch(c.verts, c.faces, spec.gap)
            slab = mesh_utils.bmesh_to_mesh(slab_bm, "_esp_slab")
            slab_bm.free()
            res = mesh_utils.boolean_mesh(context, work, slab, 'DIFFERENCE', spec.solver)
            mesh_utils.remove_mesh(slab)
            mesh_utils.remove_mesh(work)
            work = res
        if len(work.polygons) == 0:
            raise CutError("Boolean failed (empty result). Check that the mesh is closed and manifold.")
        yield "separating the parts"
        orphans = mesh_utils.separate_loose_meshes(context, work)
        work = None
        c0 = spec.contacts[0]
        bvh = mesh_utils.bvh_from_pydata(c0.verts, c0.faces)
        side_a, side_b = [], []
        for p in orphans:
            (side_a if mesh_side(p, bvh) > 0 else side_b).append(p)
        if not side_a or not side_b:
            raise CutError(still_joined_message(spec))
        out = mesh_utils.join_meshes(side_a, "_esp_part_a"), mesh_utils.join_meshes(side_b, "_esp_part_b")
        orphans = []
        return out
    finally:
        mesh_utils.remove_mesh(work)
        for me in orphans:
            mesh_utils.remove_mesh(me)


def split_mesh(context, mesh, spec):
    """Consume `mesh`, return (mesh_a, mesh_b). Side A is the + side of contact 0."""
    return drain(split_mesh_steps(context, mesh, spec))


def apply_connectors_steps(context, mesh_a, mesh_b, spec):
    total = sum(1 for c in spec.contacts if c.add_pin and c.pin_matrix is not None)
    n = 0
    half = None  # first half finished; dropped if the job is cancelled between the two booleans
    try:
        for c in spec.contacts:
            if not c.add_pin or c.pin_matrix is None:
                continue
            n += 1
            yield f"adding connector {n}/{total}" if total > 1 else "adding the connector"
            pin = connectors.connector_mesh(c.shape, c.custom_obj, c.pin_matrix, "_esp_pin", unit_mesh=c.pin_mesh)
            socket = connectors.connector_mesh(
                c.shape,
                c.custom_obj,
                c.pin_matrix,
                "_esp_socket",
                radial_extra=spec.clearance,
                tip_extra=spec.tip_extra,
                unit_mesh=c.pin_mesh,
            )
            pin_target, socket_target = (mesh_a, mesh_b) if spec.pin_side == 'A' else (mesh_b, mesh_a)
            half = mesh_utils.boolean_mesh(context, pin_target, pin, 'UNION', spec.solver)
            yield f"carving socket {n}/{total}" if total > 1 else "carving the socket"
            carved = mesh_utils.boolean_mesh(context, socket_target, socket, 'DIFFERENCE', spec.solver)
            new_a, new_b = (half, carved) if spec.pin_side == 'A' else (carved, half)
            half = None
            for m in (pin, socket, mesh_a, mesh_b):
                mesh_utils.remove_mesh(m)
            mesh_a, mesh_b = new_a, new_b
        return mesh_a, mesh_b
    finally:
        mesh_utils.remove_mesh(half)


def apply_connectors(context, mesh_a, mesh_b, spec):
    return drain(apply_connectors_steps(context, mesh_a, mesh_b, spec))


def remesh_mesh(context, mesh, voxel, adaptivity, smooth):
    scene = context.scene
    obj = mesh_utils.new_temp_object(scene, mesh, "_esp_remesh")
    mod = obj.modifiers.new("esp_remesh", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = max(voxel, 1e-5)
    mod.adaptivity = adaptivity
    mod.use_smooth_shade = smooth
    context.view_layer.update()
    out = mesh_utils.evaluated_mesh_copy(context, obj, mesh.name + "_rm")
    mesh_utils.remove_object(obj)
    return out


def perform_cut_steps(context, target_obj, spec, names, out_collection):
    """Generator form of `perform_cut`: yields a label before every heavy step.

    A single boolean can take seconds; run through a modal driver (see `jobs.py`)
    so Blender gets back to its event loop between steps instead of looking hung.
    """
    t0 = time.time()
    yield "preparing the mesh"
    mesh = mesh_utils.world_mesh_copy(context, target_obj, "_esp_work")
    made = []
    try:
        mesh_a, mesh_b = yield from split_mesh_steps(context, mesh, spec)
        made = [mesh_a, mesh_b]
        mesh_a, mesh_b = yield from apply_connectors_steps(context, mesh_a, mesh_b, spec)
        made = [mesh_a, mesh_b]
        if spec.remesh and spec.remesh_voxel > 0.0:
            yield "remeshing part 1/2"
            mesh_a = remesh_mesh(context, mesh_a, spec.remesh_voxel, spec.remesh_adaptivity, spec.remesh_smooth)
            made = [mesh_a, mesh_b]
            yield "remeshing part 2/2"
            mesh_b = remesh_mesh(context, mesh_b, spec.remesh_voxel, spec.remesh_adaptivity, spec.remesh_smooth)
            made = [mesh_a, mesh_b]
        made = []
    finally:
        mesh_utils.cleanup_temp(context.scene)
        # cancelled or failed part way through: drop the half finished meshes
        for me in made:
            mesh_utils.remove_mesh(me)
    mats = [m for m in target_obj.data.materials] if target_obj.type == 'MESH' else []
    result = []
    for me, name, side in ((mesh_a, names[0], 'A'), (mesh_b, names[1], 'B')):
        me.name = name
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        obj["esp_part"] = True
        obj["esp_side"] = side
        obj["esp_source"] = target_obj.name
        out_collection.objects.link(obj)
        result.append(obj)
    return result[0], result[1], time.time() - t0


def perform_cut(context, target_obj, spec, names, out_collection):
    """Cut `target_obj` and create the two result objects.

    names: (name_a, name_b). Returns (obj_a, obj_b, seconds).
    """
    return drain(perform_cut_steps(context, target_obj, spec, names, out_collection))
