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
def side_sign(point, bvh):
    loc, nor, _idx, _dist = bvh.find_nearest(point)
    if loc is None:
        return 1
    return 1 if (point - loc).dot(nor) >= 0.0 else -1


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
def split_mesh(context, mesh, spec):
    """Consume `mesh`, return (mesh_a, mesh_b). Side A is the + side of contact 0."""
    work = mesh
    for c in spec.contacts:
        slab_bm = surfaces.slab_from_patch(c.verts, c.faces, spec.gap)
        slab = mesh_utils.bmesh_to_mesh(slab_bm, "_esp_slab")
        slab_bm.free()
        res = mesh_utils.boolean_mesh(context, work, slab, 'DIFFERENCE', spec.solver)
        mesh_utils.remove_mesh(slab)
        mesh_utils.remove_mesh(work)
        work = res
    if len(work.polygons) == 0:
        mesh_utils.remove_mesh(work)
        raise CutError("Boolean failed (empty result). Check that the mesh is closed and manifold.")
    parts = mesh_utils.separate_loose_meshes(context, work)
    c0 = spec.contacts[0]
    bvh = mesh_utils.bvh_from_pydata(c0.verts, c0.faces)
    side_a, side_b = [], []
    for p in parts:
        (side_a if side_sign(mesh_utils.mesh_centroid(p), bvh) > 0 else side_b).append(p)
    if not side_a or not side_b:
        for p in parts:
            mesh_utils.remove_mesh(p)
        raise CutError("The cut surface does not split this part in two. Make the cut cross the whole part.")
    return mesh_utils.join_meshes(side_a, "_esp_part_a"), mesh_utils.join_meshes(side_b, "_esp_part_b")


def apply_connectors(context, mesh_a, mesh_b, spec):
    for c in spec.contacts:
        if not c.add_pin or c.pin_matrix is None:
            continue
        pin = connectors.connector_mesh(c.shape, c.custom_obj, c.pin_matrix, "_esp_pin")
        socket = connectors.connector_mesh(
            c.shape, c.custom_obj, c.pin_matrix, "_esp_socket", radial_extra=spec.clearance, tip_extra=spec.tip_extra
        )
        if spec.pin_side == 'A':
            new_a = mesh_utils.boolean_mesh(context, mesh_a, pin, 'UNION', spec.solver)
            new_b = mesh_utils.boolean_mesh(context, mesh_b, socket, 'DIFFERENCE', spec.solver)
        else:
            new_b = mesh_utils.boolean_mesh(context, mesh_b, pin, 'UNION', spec.solver)
            new_a = mesh_utils.boolean_mesh(context, mesh_a, socket, 'DIFFERENCE', spec.solver)
        for m in (pin, socket, mesh_a, mesh_b):
            mesh_utils.remove_mesh(m)
        mesh_a, mesh_b = new_a, new_b
    return mesh_a, mesh_b


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


def perform_cut(context, target_obj, spec, names, out_collection):
    """Cut `target_obj` and create the two result objects.

    names: (name_a, name_b). Returns (obj_a, obj_b, seconds).
    """
    t0 = time.time()
    mesh = mesh_utils.world_mesh_copy(context, target_obj, "_esp_work")
    try:
        mesh_a, mesh_b = split_mesh(context, mesh, spec)
        mesh_a, mesh_b = apply_connectors(context, mesh_a, mesh_b, spec)
        if spec.remesh and spec.remesh_voxel > 0.0:
            mesh_a = remesh_mesh(context, mesh_a, spec.remesh_voxel, spec.remesh_adaptivity, spec.remesh_smooth)
            mesh_b = remesh_mesh(context, mesh_b, spec.remesh_voxel, spec.remesh_adaptivity, spec.remesh_smooth)
    finally:
        mesh_utils.cleanup_temp(context.scene)
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
