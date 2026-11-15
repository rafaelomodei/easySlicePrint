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
    try:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
    except ReferenceError:
        return
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
    if mesh is None:
        return
    try:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    except ReferenceError:
        # already gone (a cancelled cut cleans up meshes the pipeline consumed)
        pass


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


def _shells(bm):
    """Face index lists, one per edge-connected shell of `bm`."""
    bm.faces.ensure_lookup_table()
    seen = [False] * len(bm.faces)
    out = []
    for f in bm.faces:
        if seen[f.index]:
            continue
        seen[f.index] = True
        stack = [f]
        comp = []
        while stack:
            cf = stack.pop()
            comp.append(cf.index)
            for e in cf.edges:
                for lf in e.link_faces:
                    if not seen[lf.index]:
                        seen[lf.index] = True
                        stack.append(lf)
        out.append(comp)
    return out


# not along an axis, so a ray from a grid-aligned point does not graze an edge or a face
_INSIDE_DIR = Vector((0.5773, 0.5779, 0.5767)).normalized()


def _crossings(tree, point, limit=10000):
    """How many times a ray from `point` crosses the surface in `tree` (odd: inside)."""
    n = 0
    origin = Vector(point)
    for _ in range(limit):
        hit, _nor, _i, _d = tree.ray_cast(origin, _INSIDE_DIR)
        if hit is None:
            break
        n += 1
        origin = hit + _INSIDE_DIR * 1e-5
    return n


def part_groups(mesh):
    """Face index groups, one per part that prints on its own.

    Each edge-connected shell is a part, except a shell lying inside another: that is
    the wall of a cavity, and it belongs to the part around it. Nesting alternates - a
    shell inside a cavity wall is a loose part again (a ship in a bottle) - so a shell
    goes with its enclosing shell when it sits an odd number of shells deep.
    """
    bm = bmesh.new()
    bm.from_mesh(mesh)
    try:
        shells = _shells(bm)
        if len(shells) < 2:
            return [sorted(i for comp in shells for i in comp)]
        trees, boxes, probes = [], [], []
        for comp in shells:
            remap, coords, polys = {}, [], []
            for fi in comp:
                poly = []
                for v in bm.faces[fi].verts:
                    if v.index not in remap:
                        remap[v.index] = len(coords)
                        coords.append(v.co.copy())
                    poly.append(remap[v.index])
                polys.append(poly)
            trees.append(BVHTree.FromPolygons(coords, polys))
            mn = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
            mx = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
            boxes.append((mn, mx))
            probes.append(coords[0])
        n = len(shells)

        def within(j, i):
            (amn, amx), (bmn, bmx) = boxes[i], boxes[j]
            if any(bmn[k] < amn[k] or bmx[k] > amx[k] for k in range(3)):
                return False
            return _crossings(trees[i], probes[j]) % 2 == 1

        def volume(i):
            d = boxes[i][1] - boxes[i][0]
            return d.x * d.y * d.z

        parent = []
        for j in range(n):
            around = [i for i in range(n) if i != j and within(j, i)]
            parent.append(min(around, key=volume) if around else -1)

        def depth(j):
            d = 0
            while parent[j] >= 0 and d < n:
                j = parent[j]
                d += 1
            return d

        owner = list(range(n))
        for j in sorted(range(n), key=depth):
            if depth(j) % 2 == 1:
                owner[j] = owner[parent[j]]
        groups = {}
        for j, comp in enumerate(shells):
            groups.setdefault(owner[j], []).extend(comp)
        return [sorted(g) for g in groups.values()]
    finally:
        bm.free()


def separate_parts(context, obj):
    """Split `obj` into one object per part (`part_groups`). -> [obj, new objects...]

    `obj` keeps the first part; the others are copies of it - same collections, same
    transform, same custom properties - each holding one part's geometry. Sorted along
    x, then y, then z, so part numbers follow the model from left to right.
    """
    groups = part_groups(obj.data)
    if len(groups) < 2:
        return [obj]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    meshes = []
    try:
        for g in groups:
            sub = bm.copy()
            sub.faces.ensure_lookup_table()
            keep = set(g)
            drop = [f for f in sub.faces if f.index not in keep]
            bmesh.ops.delete(sub, geom=drop, context='FACES')
            loose = [v for v in sub.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(sub, geom=loose, context='VERTS')
            meshes.append(bmesh_to_mesh(sub, obj.data.name))
            sub.free()
    finally:
        bm.free()
    meshes.sort(key=lambda me: tuple(round(c, 4) for c in mesh_centroid(me)))
    old = obj.data
    out = []
    for k, me in enumerate(meshes):
        if k == 0:
            obj.data = me
            target = obj
        else:
            target = obj.copy()
            target.data = me
            for col in obj.users_collection:
                col.objects.link(target)
        out.append(target)
    remove_mesh(old)
    return out


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


def bvh_from_pydata(verts, faces):
    return BVHTree.FromPolygons([Vector(v) for v in verts], [tuple(f) for f in faces])


# ----------------------------------------------------------------------------
# object ray helpers (C accelerated, work on the evaluated object)
# ----------------------------------------------------------------------------
def object_surface_depth(obj, point_w, depsgraph=None):
    """Where `point_w` sits relative to the object's surface, in WORLD space.

    -> (found, surface_point_w, outward_normal_w, signed_depth); the depth is positive
    outside the model and negative inside it, which is what tells a cut surface whether
    its rim actually leaves the material or is still buried in it.
    """
    ev = obj.evaluated_get(depsgraph) if depsgraph is not None else obj
    mw = ev.matrix_world
    inv = mw.inverted_safe()
    found, loc, nor, _idx = ev.closest_point_on_mesh(inv @ Vector(point_w))
    if not found:
        return False, None, None, 0.0
    loc_w = mw @ loc
    nor_w = (mw.to_3x3().inverted_safe().transposed() @ nor).normalized()
    return True, loc_w, nor_w, (Vector(point_w) - loc_w).dot(nor_w)


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
