# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Headless core tests.  Run:  blender -b --python tests/test_core.py"""

import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from easy_slice_print.core import connectors, cutting, mesh_utils, surfaces  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = 'MILLIMETERS'
    return sc


def make_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_cylinder(name="Cyl", radius=10.0, height=60.0, segments=48):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=True, segments=segments, radius1=radius, radius2=radius, depth=height
    )
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=3, use_grid_fill=True)
    return make_object(name, bm)


def is_closed_manifold(mesh):
    non, boundary, total = mesh_utils.manifold_report(mesh)
    return non == 0 and boundary == 0 and total > 0


def out_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


# ----------------------------------------------------------------------------
def test_straight_cut_with_pin():
    print("== straight cut with pin")
    reset_scene()
    obj = make_cylinder()
    vol0 = mesh_utils.mesh_volume(obj.data)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    diag = mesh_utils.object_world_diagonal(obj)
    # horizontal plane at z=5, normal +Z (side A = upper)
    verts, faces = surfaces.plane_patch(Vector((0, 0, 5.0)), Vector((0, 0, 1)), Vector((1, 0, 0)), diag * 1.2)
    bvh = mesh_utils.bvh_from_pydata(verts, faces)
    center, normal, inscribed = cutting.estimate_pin_frame(
        obj, depsgraph, bvh, diag, surface_point=Vector((10, 0, 5)), through_dir=Vector((-1, 0, 0))
    )
    check((center - Vector((0, 0, 5))).length < 0.5, f"pin center estimate {center}")
    check(abs(inscribed - 20.0) < 1.0, f"inscribed diameter estimate {inscribed:.2f} ~ 20")
    width = inscribed * 0.45
    height = width * 1.2
    pm = connectors.connector_matrix(center, cutting.protrude_direction(normal, 'A'), width, width * 1.2)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, 'CYLINDER', None)],
        gap=0.2,
        clearance=0.15,
        tip_extra=0.2,
        pin_side='A',
    )
    col = out_collection("out")
    a, b, secs = cutting.perform_cut(bpy.context, obj, spec, ("Cyl_UPPER", "Cyl_LOWER"), col)
    print(f"  cut took {secs:.2f}s, A faces={len(a.data.polygons)} B faces={len(b.data.polygons)}")
    check(is_closed_manifold(a.data), "part A closed manifold")
    check(is_closed_manifold(b.data), "part B closed manifold")
    ca, cb = mesh_utils.mesh_centroid(a.data), mesh_utils.mesh_centroid(b.data)
    check(ca.z > 5 > cb.z, f"A above / B below the cut ({ca.z:.1f} / {cb.z:.1f})")
    mn_a, mx_a = mesh_utils.mesh_bounds(a.data)
    mn_b, mx_b = mesh_utils.mesh_bounds(b.data)
    check(
        abs(mn_a.z - (5 - height)) < 0.05,
        f"pin protrudes below the cut: A min z {mn_a.z:.3f} (expected {5 - height:.3f})",
    )
    check(abs(mx_b.z - (5 - 0.1)) < 0.05, f"B top at cut minus half gap: {mx_b.z:.3f}")
    va, vb = mesh_utils.mesh_volume(a.data), mesh_utils.mesh_volume(b.data)
    pin_vol = math.pi * (width / 2) ** 2 * height
    check(abs((va + vb) - vol0) < pin_vol * 3, f"volume sanity: {va + vb:.0f} vs {vol0:.0f}")
    # socket exists: B volume smaller than plain lower half
    lower_plain = math.pi * 10**2 * (35 - 0.1)
    check(vb < lower_plain - pin_vol * 0.8, f"socket removed material from B ({lower_plain - vb:.0f} mm3)")
    check(cutting.side_labels(ca, cb) == ("UPPER", "LOWER"), "side labels")
    return obj


def test_ribbon_cut():
    print("== curved (ribbon) cut")
    reset_scene()
    obj = make_cylinder()
    diag = mesh_utils.object_world_diagonal(obj)
    # wavy stroke on the +X face, seen from +X (view dir = -X)
    pts = []
    for i in range(12):
        y = -14 + 28 * i / 11
        pts.append(Vector((10.0, y, 5.0 + 3.0 * math.sin(i / 11 * math.pi * 2))))
    pts = surfaces.resample_polyline(pts, 20)
    pts = surfaces.smooth_polyline(pts, 0.3)
    verts, faces = surfaces.ribbon_patch(pts, Vector((-1, 0, 0)), diag, diag * 0.5)
    n = surfaces.patch_normal(verts, faces)
    print(f"  ribbon normal {n}")
    bvh = mesh_utils.bvh_from_pydata(verts, faces)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    center, normal, inscribed = cutting.estimate_pin_frame(
        obj, depsgraph, bvh, diag, surface_point=pts[10], through_dir=Vector((-1, 0, 0))
    )
    pm = connectors.connector_matrix(center, cutting.protrude_direction(normal, 'A'), inscribed * 0.4, inscribed * 0.5)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, 'TAPERED', None)],
        gap=0.2,
        clearance=0.15,
        tip_extra=0.2,
        pin_side='A',
    )
    col = out_collection("out")
    a, b, secs = cutting.perform_cut(bpy.context, obj, spec, ("A", "B"), col)
    print(f"  cut took {secs:.2f}s")
    check(is_closed_manifold(a.data), "ribbon part A closed manifold")
    check(is_closed_manifold(b.data), "ribbon part B closed manifold")
    ca, cb = mesh_utils.mesh_centroid(a.data), mesh_utils.mesh_centroid(b.data)
    check(abs(ca.z - cb.z) > 10, f"ribbon separated top/bottom ({ca.z:.1f}/{cb.z:.1f})")


def test_loop_cut():
    print("== freehand loop cut")
    reset_scene()
    obj = make_cylinder()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    # loop around the cylinder at a slanted height, points slightly outside the surface
    pts = []
    for i in range(24):
        a = 2 * math.pi * i / 24
        pts.append(Vector((10.6 * math.cos(a), 10.6 * math.sin(a), 8.0 + 4.0 * math.cos(a))))
    verts, faces = surfaces.loop_patch(pts)
    n = surfaces.patch_normal(verts, faces)
    check(abs(n.z) > 0.9, f"loop patch normal mostly Z {n}")
    bvh = mesh_utils.bvh_from_pydata(verts, faces)
    diag = mesh_utils.object_world_diagonal(obj)
    center, normal, inscribed = cutting.estimate_pin_frame(obj, depsgraph, bvh, diag, center_hint=Vector((0, 0, 8)))
    pm = connectors.connector_matrix(center, cutting.protrude_direction(normal, 'B'), inscribed * 0.4, inscribed * 0.5)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, 'HEX', None)],
        gap=0.2,
        clearance=0.15,
        tip_extra=0.2,
        pin_side='B',
    )
    col = out_collection("out")
    a, b, secs = cutting.perform_cut(bpy.context, obj, spec, ("A", "B"), col)
    print(f"  cut took {secs:.2f}s")
    check(is_closed_manifold(a.data), "loop part A closed manifold")
    check(is_closed_manifold(b.data), "loop part B closed manifold")
    mn_b, mx_b = mesh_utils.mesh_bounds(b.data)
    check(mx_b.z > 8.0 + 0.5, "pin on side B protrudes upward into A's socket region")


def patch_edges(faces):
    """(boundary edges, non-manifold edges) of an open patch."""
    from collections import Counter

    count = Counter()
    for f in faces:
        k = len(f)
        for i in range(k):
            a, b = f[i], f[(i + 1) % k]
            count[(min(a, b), max(a, b))] += 1
    return sum(1 for c in count.values() if c == 1), sum(1 for c in count.values() if c > 2)


def worst_kink(verts, faces):
    """Largest angle in degrees between two triangles sharing an edge."""
    from collections import defaultdict

    share = defaultdict(list)
    for k, f in enumerate(faces):
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            share[(min(a, b), max(a, b))].append(k)

    def nor(f):
        return (verts[f[1]] - verts[f[0]]).cross(verts[f[2]] - verts[f[0]]).normalized()

    worst = 0.0
    for fs in share.values():
        if len(fs) == 2:
            d = max(-1.0, min(1.0, nor(faces[fs[0]]).dot(nor(faces[fs[1]]))))
            worst = max(worst, math.degrees(math.acos(d)))
    return worst


def test_smooth_surfaces():
    print("== smooth cut surfaces")
    # the spline must pass through every control point and take the corners out
    ctrl = [Vector((i, math.sin(i), 0.0)) for i in range(6)]
    sp = surfaces.spline_polyline(ctrl, 4)
    check(len(sp) == 5 * 4 + 1, f"spline sample count {len(sp)}")
    check(all(min((p - c).length for p in sp) < 1e-9 for c in ctrl), "spline passes through the control points")

    def max_turn(poly):
        m = 0.0
        for i in range(1, len(poly) - 1):
            a = (poly[i] - poly[i - 1]).normalized()
            b = (poly[i + 1] - poly[i]).normalized()
            m = max(m, math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b))))))
        return m

    stroke = [Vector((10.0, -14 + 28 * i / 11, 5.0 + 3.0 * math.sin(i / 11 * math.pi * 2))) for i in range(12)]
    check(max_turn(surfaces.spline_polyline(stroke, 3)) < max_turn(stroke) * 0.6, "spline flattens the polyline kinks")

    # a loop drawn from one viewpoint has to come out as flat as a plane cut
    flat = [
        Vector((10.6 * math.cos(a), 10.6 * math.sin(a), 8.0 + 4.0 * math.cos(a)))
        for a in (2 * math.pi * i / 24 for i in range(24))
    ]
    verts, faces = surfaces.loop_patch(flat)
    boundary, nonmanifold = patch_edges(faces)
    check(nonmanifold == 0, f"membrane fill is manifold ({nonmanifold} bad edges)")
    check(boundary > 0, "membrane fill has an open boundary")
    n = surfaces.patch_normal(verts, faces)
    c = surfaces.patch_center(verts)
    check(max(abs((v - c).dot(n)) for v in verts) < 1e-5, "planar loop is filled dead flat")

    # a loop drawn while orbiting must be a smooth saddle, not a cone
    saddle = [
        Vector((10.0 * math.cos(a), 10.0 * math.sin(a), 6.0 * math.sin(2 * a)))
        for a in (2 * math.pi * i / 32 for i in range(32))
    ]
    verts, faces = surfaces.loop_patch(saddle)
    _b, nonmanifold = patch_edges(faces)
    check(nonmanifold == 0, f"saddle fill is manifold ({nonmanifold} bad edges)")
    kink = worst_kink(verts, faces)
    check(kink < 25.0, f"saddle fill stays smooth (worst kink {kink:.1f} deg)")
    check(abs(verts[-1].z) < 0.5, f"no centroid spike (centre z {verts[-1].z:.2f})")

    # the drawn loop itself is never moved
    src = surfaces.dedupe_polyline(surfaces.spline_polyline(saddle, surfaces.SURFACE_DETAIL, closed=True), 1e-9)
    check(max((verts[i] - src[i]).length for i in range(len(src))) < 1e-9, "boundary vertices stay on the drawn loop")


def test_two_contacts():
    print("== two contact cut (base separate)")
    reset_scene()
    # a "figure": two legs on a base
    bm = bmesh.new()
    for x in (-15.0, 15.0):
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            cap_tris=True,
            segments=32,
            radius1=6,
            radius2=6,
            depth=40,
            matrix=Matrix.Translation((x, 0, 20)),
        )
    legs = make_object("legs", bm)
    bm2 = bmesh.new()
    bmesh.ops.create_cube(bm2, size=1.0)
    bmesh.ops.scale(bm2, vec=(60, 30, 8), verts=bm2.verts)
    bmesh.ops.translate(bm2, vec=(0, 0, -3.0), verts=bm2.verts)
    base = make_object("base", bm2)
    # union them into one closed mesh
    me = mesh_utils.boolean_mesh(
        bpy.context,
        mesh_utils.world_mesh_copy(bpy.context, legs, "l"),
        mesh_utils.world_mesh_copy(bpy.context, base, "b"),
        'UNION',
        'EXACT',
    )
    mesh_utils.cleanup_temp(bpy.context.scene)
    fig = bpy.data.objects.new("fig", me)
    bpy.context.scene.collection.objects.link(fig)
    check(is_closed_manifold(me), "figure is closed manifold")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    contacts = []
    for x in (-15.0, 15.0):
        verts, faces = surfaces.plane_patch(Vector((x, 0, 3.0)), Vector((0, 0, 1)), Vector((1, 0, 0)), 20.0)
        bvh = mesh_utils.bvh_from_pydata(verts, faces)
        c, n, d = cutting.estimate_pin_frame(
            fig, depsgraph, bvh, 80.0, surface_point=Vector((x + 6, 0, 3)), through_dir=Vector((-1, 0, 0))
        )
        check(abs(d - 12.0) < 1.0, f"contact inscribed {d:.2f} ~ 12")
        pm = connectors.connector_matrix(c, cutting.protrude_direction(n, 'A'), d * 0.4, d * 0.5)
        contacts.append(cutting.ContactSpec(verts, faces, True, pm, 'CYLINDER', None))
    spec = cutting.CutSpec(contacts=contacts, gap=0.2, clearance=0.15, tip_extra=0.2, pin_side='A')
    col = out_collection("out")
    a, b, secs = cutting.perform_cut(bpy.context, fig, spec, ("figure", "base"), col)
    print(f"  cut took {secs:.2f}s")
    check(is_closed_manifold(a.data), "two-contact part A closed manifold")
    check(is_closed_manifold(b.data), "two-contact part B closed manifold")
    ca, cb = mesh_utils.mesh_centroid(a.data), mesh_utils.mesh_centroid(b.data)
    check(ca.z > 10 and cb.z < 3, f"legs up / base down ({ca.z:.1f}/{cb.z:.1f})")
    # legs part must be ONE object containing both legs (joined by side)
    mn, mx = mesh_utils.mesh_bounds(a.data)
    check(mx.x - mn.x > 35, "both legs joined in part A")


def test_custom_connector_and_remesh():
    print("== custom connector + remesh")
    reset_scene()
    obj = make_cylinder()
    col, created = connectors.ensure_library(bpy.context)
    check(len(created) == 4, "library created 4 templates")
    items = connectors.shape_enum_items(None, bpy.context)
    check(any(i[0].startswith("OBJ:") for i in items), "custom shapes listed in enum")
    shape, custom = connectors.resolve_shape("OBJ:ESP_Connector_Box")
    check(shape == 'CUSTOM' and custom is not None, "resolve custom shape")
    verts, faces = surfaces.plane_patch(Vector((0, 0, 0)), Vector((0, 0, 1)), Vector((1, 0, 0)), 60)
    pm = connectors.connector_matrix(Vector((0, 0, 0)), Vector((0, 0, -1)), 6, 6)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, shape, custom)],
        gap=0.2,
        clearance=0.1,
        tip_extra=0.2,
        pin_side='A',
        remesh=True,
        remesh_voxel=0.5,
        remesh_adaptivity=0.0,
        remesh_smooth=False,
    )
    out = out_collection("out")
    a, b, secs = cutting.perform_cut(bpy.context, obj, spec, ("A", "B"), out)
    print(f"  cut+remesh took {secs:.2f}s, faces {len(a.data.polygons)}")
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "remeshed parts closed manifold")
    check(len(a.data.polygons) > 1000, "remesh produced dense geometry")


if __name__ == "__main__":
    t = time.time()
    test_straight_cut_with_pin()
    test_ribbon_cut()
    test_loop_cut()
    test_smooth_surfaces()
    test_two_contacts()
    test_custom_connector_and_remesh()
    print(f"\n{len(FAILS)} failure(s) in {time.time() - t:.1f}s")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)
