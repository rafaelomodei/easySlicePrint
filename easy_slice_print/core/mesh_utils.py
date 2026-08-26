# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Low level mesh helpers: temp objects, booleans, loose parts, centroids."""

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TEMP_COLLECTION = "_ESP_TEMP"


# ----------------------------------------------------------------------------
# temp objects
# ----------------------------------------------------------------------------
def temp_collection(scene):
    col = bpy.data.collections.get(TEMP_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(TEMP_COLLECTION)
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def new_temp_object(scene, mesh, name):
    obj = bpy.data.objects.new(name, mesh)
    temp_collection(scene).objects.link(obj)
    return obj


def remove_object(obj, remove_data=True):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if remove_data and data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
        bpy.data.meshes.remove(data)


def cleanup_temp(scene):
    col = bpy.data.collections.get(TEMP_COLLECTION)
    if col is None:
        return
    for obj in list(col.objects):
        remove_object(obj)
    bpy.data.collections.remove(col)


def remove_mesh(mesh):
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


# ----------------------------------------------------------------------------
# evaluated copies
# ----------------------------------------------------------------------------
def evaluated_mesh_copy(context, obj, name):
    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    me = bpy.data.meshes.new_from_object(eval_obj, preserve_all_data_layers=False, depsgraph=depsgraph)
    me.name = name
    return me


def world_mesh_copy(context, obj, name):
    """Evaluated mesh of `obj` with the world matrix applied."""
    me = evaluated_mesh_copy(context, obj, name)
    me.transform(obj.matrix_world)
    return me


def mesh_from_pydata(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    return me


def bmesh_to_mesh(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.update()
    return me


# ----------------------------------------------------------------------------
# booleans
# ----------------------------------------------------------------------------
def available_solvers():
    try:
        prop = bpy.types.BooleanModifier.bl_rna.properties['solver']
        return [e.identifier for e in prop.enum_items]
    except Exception:
        return ['EXACT']


def resolve_solver(requested):
    ids = available_solvers()
    if requested == 'AUTO':
        return 'MANIFOLD' if 'MANIFOLD' in ids else 'EXACT'
    return requested if requested in ids else 'EXACT'


def boolean_mesh(context, base_mesh, cutter_mesh, operation, solver='AUTO'):
    """Return a NEW mesh = base_mesh <operation> cutter_mesh (both in the same space).

    operation: 'DIFFERENCE' | 'UNION' | 'INTERSECT'
    With solver AUTO the manifold solver is tried first and EXACT is used as a
    fallback when the result comes back empty.
    """
    scene = context.scene
    base = new_temp_object(scene, base_mesh, "_esp_bool_base")
    cutter = new_temp_object(scene, cutter_mesh, "_esp_bool_cutter")
    result = None
    try:
        chain = [resolve_solver(solver)]
        if solver == 'AUTO' and chain[0] != 'EXACT':
            chain.append('EXACT')
        for sv in chain:
            mod = base.modifiers.new("esp_bool", 'BOOLEAN')
            mod.operation = operation
            mod.object = cutter
            mod.solver = sv
            context.view_layer.update()
            me = evaluated_mesh_copy(context, base, base_mesh.name + "_bool")
            base.modifiers.remove(mod)
            unchanged = len(me.polygons) == len(base_mesh.polygons) and len(me.vertices) == len(base_mesh.vertices)
            if (len(me.polygons) > 0 and not unchanged) or (operation == 'INTERSECT' and not unchanged):
                result = me
                break
            # empty result, or the solver refused to run (mesh returned untouched): try the next solver
            remove_mesh(me)
        if result is None:
            result = bpy.data.meshes.new(base_mesh.name + "_bool")
    finally:
        remove_object(base, remove_data=False)
        remove_object(cutter, remove_data=False)
    return result


# ----------------------------------------------------------------------------
# loose parts / join
# ----------------------------------------------------------------------------
def separate_loose_meshes(context, mesh):
    """Split `mesh` into loose shells. Returns a list of NEW meshes (mesh itself is consumed)."""
    scene = context.scene
    obj = new_temp_object(scene, mesh, "_esp_sep")
    view_layer = context.view_layer
    # make sure the object is visible/selectable for the operator
    obj.hide_set(False, view_layer=view_layer)
    obj.hide_viewport = False
    for o in view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    before = set(o.name for o in scene.objects)
    try:
        with context.temp_override(
            active_object=obj,
            object=obj,
            selected_objects=[obj],
            selected_editable_objects=[obj],
            view_layer=view_layer,
            scene=scene,
        ):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError:
        # fallback: pure python flood fill
        return _separate_loose_python(mesh, obj)
    new_objs = [o for o in scene.objects if o.name not in before] + [obj]
    meshes = []
    for o in new_objs:
        me = o.data
        remove_object(o, remove_data=False)
        if len(me.polygons) == 0:
            remove_mesh(me)
            continue
        meshes.append(me)
    return meshes


def _separate_loose_python(mesh, obj):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    seen = np.zeros(len(bm.faces), dtype=bool)
    comps = []
    for f in bm.faces:
        if seen[f.index]:
            continue
        seen[f.index] = True
        stack = [f]
        comp = []
        while stack:
            cf = stack.pop()
            comp.append(cf)
            for e in cf.edges:
                for lf in e.link_faces:
                    if not seen[lf.index]:
                        seen[lf.index] = True
                        stack.append(lf)
        comps.append(comp)
    meshes = []
    for comp in comps:
        sub = bm.copy()
        sub.faces.ensure_lookup_table()
        keep = {f.index for f in comp}
        bmesh.ops.delete(sub, geom=[f for f in sub.faces if f.index not in keep], context='FACES')
        meshes.append(bmesh_to_mesh(sub, mesh.name + "_part"))
        sub.free()
    bm.free()
    remove_object(obj)
    return meshes


def join_meshes(meshes, name):
    """Join several meshes into one NEW mesh (inputs are removed)."""
    bm = bmesh.new()
    for me in meshes:
        bm.from_mesh(me)
    out = bmesh_to_mesh(bm, name)
    bm.free()
    for me in meshes:
        remove_mesh(me)
    return out


# ----------------------------------------------------------------------------
# measurements
# ----------------------------------------------------------------------------
def mesh_vertex_array(mesh):
    n = len(mesh.vertices)
    arr = np.empty(n * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', arr)
    return arr.reshape(n, 3)


def mesh_centroid(mesh):
    if len(mesh.vertices) == 0:
        return Vector((0.0, 0.0, 0.0))
    arr = mesh_vertex_array(mesh)
    return Vector(arr.mean(axis=0).tolist())


def mesh_bounds(mesh):
    arr = mesh_vertex_array(mesh)
    if len(arr) == 0:
        z = Vector((0, 0, 0))
        return z, z
    return Vector(arr.min(axis=0).tolist()), Vector(arr.max(axis=0).tolist())


def object_world_bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def object_world_diagonal(obj):
    mn, mx = object_world_bounds(obj)
    return max((mx - mn).length, 1e-6)


def mesh_volume(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    v = bm.calc_volume(signed=False)
    bm.free()
    return v


def manifold_report(mesh, limit=None):
    """Return (non_manifold_edges, boundary_edges, total_edges)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non = 0
    boundary = 0
    for i, e in enumerate(bm.edges):
        if limit is not None and i >= limit:
            break
        if e.is_boundary:
            boundary += 1
        elif not e.is_manifold:
            non += 1
    total = len(bm.edges)
    bm.free()
    return non, boundary, total


def bvh_from_mesh(mesh):
    verts = [v.co.copy() for v in mesh.vertices]
    polys = [tuple(p.vertices) for p in mesh.polygons]
    return BVHTree.FromPolygons(verts, polys)


def bvh_from_pydata(verts, faces):
    return BVHTree.FromPolygons([Vector(v) for v in verts], [tuple(f) for f in faces])


# ----------------------------------------------------------------------------
# object ray helpers (C accelerated, work on the evaluated object)
# ----------------------------------------------------------------------------
def object_ray_cast(obj, origin_w, direction_w, depsgraph=None, max_dist=1e30):
    """Ray cast against a single object in WORLD space -> (hit, loc_w, normal_w, dist)."""
    inv = obj.matrix_world.inverted_safe()
    o = inv @ origin_w
    d = inv.to_3x3() @ direction_w
    if d.length == 0:
        return False, None, None, 0.0
    d.normalize()
    if depsgraph is not None:
        hit, loc, nor, idx = obj.ray_cast(o, d, distance=max_dist, depsgraph=depsgraph)
    else:
        hit, loc, nor, idx = obj.ray_cast(o, d, distance=max_dist)
    if not hit:
        return False, None, None, 0.0
    loc_w = obj.matrix_world @ loc
    nor_w = (obj.matrix_world.to_3x3().inverted_safe().transposed() @ nor).normalized()
    return True, loc_w, nor_w, (loc_w - origin_w).length


def object_ray_hits(obj, origin_w, direction_w, eps, depsgraph=None, max_dist=1e30, limit=64):
    """Distance of EVERY surface crossing along a ray, in world space.

    `object_ray_cast` stops at the first hit; this marches `eps` past each hit to
    collect the whole set, which is what "how deep does the model go here" needs.
    """
    o = Vector(origin_w)
    d = Vector(direction_w).normalized()
    out = []
    start = o
    for _ in range(limit):
        travelled = (start - o).length
        if travelled >= max_dist:
            break
        hit, loc, _n, _dist = object_ray_cast(obj, start, d, depsgraph, max_dist=max_dist - travelled)
        if not hit:
            break
        out.append((loc - o).length)
        start = loc + d * eps
    return out


def object_closest_point(obj, point_w, depsgraph=None):
    inv = obj.matrix_world.inverted_safe()
    p = inv @ point_w
    if depsgraph is not None:
        ok, loc, nor, idx = obj.closest_point_on_mesh(p, depsgraph=depsgraph)
    else:
        ok, loc, nor, idx = obj.closest_point_on_mesh(p)
    if not ok:
        return False, None, None, 0.0
    loc_w = obj.matrix_world @ loc
    nor_w = (obj.matrix_world.to_3x3().inverted_safe().transposed() @ nor).normalized()
    return True, loc_w, nor_w, (loc_w - point_w).length
