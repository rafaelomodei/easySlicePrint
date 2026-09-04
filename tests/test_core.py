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
import easy_slice_print  # noqa: E402
from easy_slice_print import plan  # noqa: E402
from easy_slice_print.core import connectors, cutting, mesh_utils, section, surfaces  # noqa: E402

easy_slice_print.register()  # the freehand tests read the addon's own settings

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


def _figure_with_limbs():
    """A body with a neck and two legs: the shape a freehand loop is drawn on."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(44.0, 16.0, 18.0), verts=bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=8, use_grid_fill=True)
    parts = [make_object("body", bm)]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=32, radius1=6.0, radius2=4.5, depth=30.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=8, use_grid_fill=True)
    neck = make_object("neck", bm)
    neck.location = (17.0, 0.0, 17.0)
    neck.rotation_euler = (0.0, math.radians(30.0), 0.0)
    parts.append(neck)
    for x in (-14.0, 14.0):
        for y in (-5.0, 5.0):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=20, radius1=3.5, radius2=3.0, depth=34.0)
            bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=6, use_grid_fill=True)
            leg = make_object(f"leg{x:.0f}_{y:.0f}", bm)
            leg.location = (x, y, -22.0)
            parts.append(leg)
    bpy.context.view_layer.update()
    me = mesh_utils.world_mesh_copy(bpy.context, parts[0], "w")
    for extra in parts[1:]:
        me = mesh_utils.boolean_mesh(
            bpy.context, me, mesh_utils.world_mesh_copy(bpy.context, extra, "e"), 'UNION', 'EXACT'
        )
    mesh_utils.cleanup_temp(bpy.context.scene)
    for o in parts:
        mesh_utils.remove_object(o)
    obj = bpy.data.objects.new("Fig", me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def _traced_loop(obj, centre, axis, radius, samples=100, wobble=0.05, shape=None):
    """The samples a freehand stroke records tracing a ring round a limb.

    `shape(angle) -> offset along the axis` replaces the default gentle wobble, for a
    stroke that traces a real detail: a step is what a 20 point resample cannot follow.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    diag = mesh_utils.object_world_diagonal(obj)
    u, v = surfaces.plane_basis(Vector(axis))
    if shape is None:

        def shape(a):
            return radius * wobble * math.sin(a * 3.0)

    out = []
    for k in range(samples):
        a = 2.0 * math.pi * k / samples
        d = u * math.cos(a) + v * math.sin(a)
        aim = Vector(centre) + Vector(axis).normalized() * shape(a) + d * radius
        hit, loc, nor, _i = mesh_utils.object_ray_cast(obj, aim + d * diag, -d, depsgraph, max_dist=diag * 4.0)
        if hit:
            out.append((loc, nor.normalized()))
    return out


def _freehand_patch(obj, loop, margin, smoothing=0.0, control_points=None, detail=3, clear=True):
    """The membrane `close_loop` builds from a recorded stroke.

    Defaults mirror the tool: no smoothing, and every drawn point kept. Pass
    `smoothing=0.35, control_points=20` to get the eroding pipeline this replaced.
    """
    diag = mesh_utils.object_world_diagonal(obj)
    pts = [loc + nor * margin for loc, nor in loop]
    pts = surfaces.dedupe_polyline(pts, diag * 0.002)
    pts = surfaces.smooth_polyline(pts, smoothing, closed=True)
    if control_points:
        pts = surfaces.resample_polyline(pts, control_points, closed=True)
    n = surfaces.newell_normal(pts)
    if n.z < -1e-6 or (abs(n.z) <= 1e-6 and n.x < 0):
        pts.reverse()
    rim = len(surfaces.loop_boundary(pts, detail))
    if not clear:
        verts, faces = surfaces.loop_patch(pts, detail=detail)
        return verts, faces, rim
    pts = plan.clear_of_model(bpy.context, obj, pts, margin)
    verts, faces = plan.loop_surface(bpy.context, obj, pts, detail, margin)
    return verts, faces, rim


def _rim_depth(obj, verts, count):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    out = []
    for p in verts[:count]:
        found, _loc, _nor, depth = mesh_utils.object_surface_depth(obj, p, depsgraph)
        if found:
            out.append(depth)
    return min(out) if out else 0.0


def test_freehand_loop_really_leaves_the_model():
    """A freehand membrane only cuts if its rim stands clear of the model.

    Unlike a plane section or a curve ribbon, the membrane stops on its own rim, so the
    single thing separating the two halves is how far that rim reaches past the surface.
    The stroke is pushed out along the surface normal when it is drawn, and the pipeline
    it then goes through can drag it back: measuring the finished rim against the model
    is the only check that survives every step of it.
    """
    print("== a freehand loop's rim has to leave the model")
    reset_scene()
    fig = _figure_with_limbs()
    diag = mesh_utils.object_world_diagonal(fig)
    loop = _traced_loop(fig, Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)), 14.0)
    check(len(loop) > 80, f"the stroke recorded a full ring ({len(loop)} samples)")

    # what the loop used to get: a fixed 0.6 mm push applied BEFORE a smoothing pass and
    # a resample down to 20 control points, both of which pull the rim back into the model
    verts, faces, rim = _freehand_patch(fig, loop, 0.6, smoothing=0.35, control_points=20, clear=False)
    sunk = _rim_depth(fig, verts, rim)
    check(sunk < 0.2, f"the old fixed push does not survive the pipeline (rim at {sunk:+.2f} mm)")
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(verts, faces, add_pin=False)], gap=0.2)
    failed = False
    try:
        cutting.perform_cut(bpy.context, fig, spec, ("A", "B"), out_collection("old"))
    except cutting.CutError:
        failed = True
    check(failed, "and a rim sitting on the surface leaves the part in one piece")

    reset_scene()
    fig = _figure_with_limbs()
    settings = bpy.context.scene.esp
    loop = _traced_loop(fig, Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)), 14.0)
    margin = plan.loop_margin(bpy.context, settings, [loc for loc, _n in loop], diag)
    check(margin > 0.5, f"the margin is scaled to the loop, not a fixed hair ({margin:.2f} mm)")
    verts, faces, rim = _freehand_patch(fig, loop, margin)
    clear = _rim_depth(fig, verts, rim)
    check(clear > margin * 0.5, f"the corrected rim really stands outside the model ({clear:+.2f} mm)")
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(verts, faces, add_pin=False)], gap=0.2)
    a, b, _s = cutting.perform_cut(bpy.context, fig, spec, ("A", "B"), out_collection("new"))
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "and the cut splits it into two solids")
    check(len(a.data.polygons) > 100 and len(b.data.polygons) > 100, "both halves carry real geometry")

    # The clearance is what costs a traced loop its detail, so it is kept as small as it
    # can be - and this is what decides how small. A loop round the top of a thigh, where
    # the leg runs into the body, separates the model cleanly at 0.8 mm but every loose
    # piece then votes to the same side of a membrane that local, and a cut that worked
    # comes back as one that never split the part. It holds from about 1.2 mm; the
    # clearance the tool picks has to stay clear of that, on this loop above all.
    reset_scene()
    fig = _figure_with_limbs()
    hip = _traced_loop(fig, Vector((-14.0, -5.0, -12.0)), Vector((0.0, 0.0, 1.0)), 4.5)
    margin = plan.loop_margin(bpy.context, settings, [loc for loc, _n in hip], diag)
    check(margin > 1.2, f"a loop at the hip junction gets more than the 1.2 mm it needs ({margin:.2f} mm)")
    verts, faces, _rim = _freehand_patch(fig, hip, margin)
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(verts, faces, add_pin=False)], gap=0.2)
    a, b, _s = cutting.perform_cut(bpy.context, fig, spec, ("A", "B"), out_collection("hip"))
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "and that cut is reported as the split it is")


def _dist_to_rim(p, rim):
    """Distance from `p` to the closed polyline `rim`."""
    best = 1e9
    m = len(rim)
    for i in range(m):
        a, b = rim[i], rim[(i + 1) % m]
        ab = b - a
        sq = ab.length_squared
        t = 0.0 if sq < 1e-12 else max(0.0, min(1.0, (p - a).dot(ab) / sq))
        best = min(best, (p - (a + ab * t)).length)
    return best


def test_freehand_keeps_the_points_it_was_drawn_through():
    """A traced loop is only worth drawing if the cut lands on the line you traced.

    Freehand is the tool for catching a detail - a groove, a shoulder, the line where two
    shapes meet - so what the stroke records has to reach the cut face. It used to be
    smoothed and then resampled down to Control Points, which is a Curve setting: a stroke
    of 200 samples became 20, and a step in the traced line came out rounded off by
    millimetres. Now the drawn points are the control points, and the rim runs through
    every one of them, pushed out by the clearance and nothing else.
    """
    print("== a freehand loop cuts on the line it was drawn on")
    reset_scene()
    fig = _figure_with_limbs()
    diag = mesh_utils.object_world_diagonal(fig)
    settings = bpy.context.scene.esp

    # a stroke that traces a stepped detail round the waist, not a gentle wobble: a
    # handful of control points can follow a sine, but not the corners of a step
    def stepped(a):
        return 4.0 * (1.0 if math.sin(a * 4.0) > 0.0 else -1.0)

    loop = _traced_loop(fig, Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)), 14.0, samples=200, shape=stepped)
    locs = [loc for loc, _n in loop]
    margin = plan.loop_margin(bpy.context, settings, locs, diag)
    # where every point of the rim belongs: the stroke, pushed clear along its own normal
    want = [loc + nor * margin for loc, nor in loop]

    kept = surfaces.dedupe_polyline(want, diag * 0.002)
    check(
        len(kept) >= len(loop) - 2,
        f"the loop keeps the points it was drawn through ({len(kept)} of {len(loop)} samples)",
    )
    check(
        len(kept) > settings.control_points * 3,
        f"and is not cut down to Control Points ({len(kept)} kept, the setting says {settings.control_points})",
    )

    def strayed(**kw):
        verts, _faces, rim = _freehand_patch(fig, loop, margin, **kw)
        edge = [Vector(v) for v in verts[:rim]]
        return max(_dist_to_rim(p, edge) for p in want)

    now = strayed()
    before = strayed(smoothing=0.35, control_points=20)
    print(f"  rim strays {now:.3f} mm from the drawn points, was {before:.3f} mm")
    check(now < 0.2, f"the rim runs through the drawn points ({now:.3f} mm off)")
    check(now < before / 4.0, f"a long way closer than the resampled rim ({before:.3f} mm off)")

    verts, faces, _rim = _freehand_patch(fig, loop, margin)
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(verts, faces, add_pin=False)], gap=0.2)
    a, b, _s = cutting.perform_cut(bpy.context, fig, spec, ("A", "B"), out_collection("traced"))
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "and the traced cut still splits the model")


def test_a_split_that_worked_is_not_reported_as_a_failure():
    """Which half a piece came off is decided by the geometry on the cut face.

    A freehand membrane is small and local, so a separated piece's centroid can sit far
    off the end of it - a leg's centroid is half the model away from a loop drawn round
    its thigh - and out there the nearest facet's normal means nothing. Classifying by
    the centroid put every piece on one side and reported a cut that had worked as one
    that never split the part, which is why `mesh_side` votes over the geometry instead.

    The centroid is only printed here now: the membrane this fixture builds is no longer
    the sprawling one that produced the original misclassification, and a premise that
    has stopped being true is not worth asserting. What has to hold is the outcome -
    both sides are found, and the offcut is not on the same side as the rest.
    """
    print("== a cut that did separate is not reported as a failure")
    reset_scene()
    fig = _figure_with_limbs()
    diag = mesh_utils.object_world_diagonal(fig)
    # a loop drawn slanted across one thigh, so the membrane is small, tilted and sits
    # a long way from the centroid of everything it cuts off
    axis = Vector((0.3, 0.2, 0.93))
    loop = _traced_loop(fig, Vector((-14.0, -5.0, -20.0)), axis, 6.0)
    settings = bpy.context.scene.esp
    margin = plan.loop_margin(bpy.context, settings, [loc for loc, _n in loop], diag)
    verts, faces, _rim = _freehand_patch(fig, loop, margin)
    bvh = mesh_utils.bvh_from_pydata(verts, faces)
    mesh = mesh_utils.world_mesh_copy(bpy.context, fig, "_w")
    slab_bm = surfaces.slab_from_patch(verts, faces, 0.2)
    slab = mesh_utils.bmesh_to_mesh(slab_bm, "_slab")
    slab_bm.free()
    work = mesh_utils.boolean_mesh(bpy.context, mesh, slab, 'DIFFERENCE', 'AUTO')
    mesh_utils.remove_mesh(slab)
    pieces = mesh_utils.separate_loose_meshes(bpy.context, work)
    check(len(pieces) > 1, f"the boolean did separate the model ({len(pieces)} pieces)")
    centroids = [cutting.side_sign(mesh_utils.mesh_centroid(p), bvh) for p in pieces]
    votes = [cutting.mesh_side(p, bvh) for p in pieces]
    print(f"  centroid says {centroids}, the vote says {votes}")
    check(any(v > 0 for v in votes) and any(v < 0 for v in votes), f"and both sides are found ({votes})")
    big = max(pieces, key=lambda m: len(m.polygons))
    small = min(pieces, key=lambda m: len(m.polygons))
    check(
        cutting.mesh_side(big, bvh) != cutting.mesh_side(small, bvh),
        "the offcut and the rest of the model land on opposite sides",
    )
    for p in pieces:
        mesh_utils.remove_mesh(p)


def test_edited_connector_is_the_one_built():
    """A connector reshaped in edit mode has to reach the boolean, not its template.

    The plan stores the shape by name, so a build that rebuilds from the name throws
    away everything the user did to the preview pin. The pin object's own mesh is the
    only record of that work, so the spec carries the mesh itself.
    """
    print("== an edited connector is the connector that gets built")
    reset_scene()

    # the preview pin as the plan makes it, then edited: twice as wide, half as tall
    bm = connectors.unit_connector_bmesh('CYLINDER')
    for v in bm.verts:
        v.co.x *= 2.0
        v.co.y *= 2.0
        v.co.z *= 0.5
    edited = mesh_utils.bmesh_to_mesh(bm, "ESP_Pin_edited")
    bm.free()

    pm = connectors.connector_matrix(Vector((0, 0, 0)), Vector((0, 0, -1)), 6.0, 8.0)
    plain = connectors.connector_mesh('CYLINDER', None, pm, "plain")
    mn, mx = mesh_utils.mesh_bounds(plain)
    check(abs((mx.x - mn.x) - 6.0) < 0.1, f"the template pin is 6 mm across ({mx.x - mn.x:.2f})")

    grown = connectors.connector_mesh('CYLINDER', None, pm, "grown", unit_mesh=edited)
    mn, mx = mesh_utils.mesh_bounds(grown)
    check(abs((mx.x - mn.x) - 12.0) < 0.1, f"the edited pin is 12 mm across ({mx.x - mn.x:.2f})")
    check(abs((mx.z - mn.z) - 8.0) < 0.1, f"and 8 mm tall, half of the template's 16 ({mx.z - mn.z:.2f})")

    # the socket clears the edited shape by the clearance, not by the template's
    socket = connectors.connector_mesh('CYLINDER', None, pm, "socket", radial_extra=0.5, unit_mesh=edited)
    smn, smx = mesh_utils.mesh_bounds(socket)
    check(abs((smx.x - mn.x - (mx.x - mn.x)) - 0.5) < 0.05, f"socket clears by 0.5 mm per side ({smx.x - mx.x:.3f})")

    # and the whole build honours it: the pin sticking out of part A is the wide one
    obj = make_cylinder()
    verts, faces = surfaces.plane_patch(Vector((0, 0, 0)), Vector((0, 0, 1)), Vector((1, 0, 0)), 60)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, 'CYLINDER', None, pin_mesh=edited)],
        gap=0.2,
        clearance=0.1,
        pin_side='A',
    )
    out = out_collection("out")
    a, b, _secs = cutting.perform_cut(bpy.context, obj, spec, ("A", "B"), out)
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "both parts closed manifold")
    mn_a, _mx_a = mesh_utils.mesh_bounds(a.data)
    check(abs(mn_a.z - -4.0) < 0.1, f"the pin on A is the edited 4 mm protrusion ({mn_a.z:.2f}, not -8)")
    # the socket in B is as wide as the edited pin: measure the hole at the cut face
    ring = [v.co for v in b.data.vertices if v.co.z > -0.3 and abs(v.co.x) < 9.0 and abs(v.co.y) < 1.0]
    check(ring and max(abs(v.x) for v in ring) > 5.5, "B was hollowed out to the edited pin's 12 mm width")


def test_stepped_cut():
    """The cut runs as a generator so Blender's event loop is never blocked for long."""
    print("== stepped cut (no long main thread block)")
    reset_scene()
    obj = make_cylinder()
    diag = mesh_utils.object_world_diagonal(obj)
    verts, faces = surfaces.plane_patch(Vector((0, 0, 0)), Vector((0, 0, 1)), Vector((1, 0, 0)), diag * 1.3)
    pm = connectors.connector_matrix(Vector((0, 0, 0)), Vector((0, 0, -1)), 6.0, 8.0)
    spec = cutting.CutSpec(
        contacts=[cutting.ContactSpec(verts, faces, True, pm, 'CYLINDER', None)], gap=0.2, clearance=0.1
    )
    out = out_collection("stepped")
    gen = cutting.perform_cut_steps(bpy.context, obj, spec, ("A", "B"), out)
    labels = []
    longest = 0.0
    while True:
        t = time.time()
        try:
            label = next(gen)
        except StopIteration as stop:
            longest = max(longest, time.time() - t)
            a, b, secs = stop.value
            break
        longest = max(longest, time.time() - t)
        labels.append(label)
    check(len(labels) >= 4, f"the cut is split into steps ({len(labels)} labels: {', '.join(labels)})")
    check(all(isinstance(x, str) and x for x in labels), "every step reports a label for the status bar")
    check(longest <= secs, f"no single step costs more than the whole cut ({longest:.3f}s of {secs:.3f}s)")
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "stepped cut gives closed manifold parts")

    # a cancelled job must not leave orphan meshes behind
    reset_scene()
    obj = make_cylinder()
    out = out_collection("cancelled")
    before = set(m.name for m in bpy.data.meshes)
    gen = cutting.perform_cut_steps(bpy.context, obj, spec, ("A", "B"), out)
    next(gen)
    next(gen)
    next(gen)
    gen.close()
    leaked = sorted(set(m.name for m in bpy.data.meshes) - before)
    check(not leaked, f"cancelling part way leaks nothing (leaked: {leaked})")
    check(bpy.data.collections.get(mesh_utils.TEMP_COLLECTION) is None, "cancelling removes the temp collection")


# ----------------------------------------------------------------------------
def patch_area(verts, faces):
    return surfaces.patch_area([Vector(v) for v in verts], faces)


def patch_extent(verts):
    return section.section_extent(verts)


def make_two_legs(name="Legs", at=(-30.0, 30.0), radius=10.0, height=60.0):
    """One object holding two separate cylinders: the two legs of the figure."""
    bm = bmesh.new()
    for x in at:
        leg = bmesh.new()
        bmesh.ops.create_cone(
            leg, cap_ends=True, cap_tris=True, segments=48, radius1=radius, radius2=radius, depth=height
        )
        bmesh.ops.translate(leg, verts=list(leg.verts), vec=Vector((x, 0, 0)))
        bm.from_mesh(mesh_utils.bmesh_to_mesh(leg, f"_leg{x}"))
        leg.free()
    obj = make_object(name, bm)
    bpy.context.view_layer.update()
    return obj


def test_cross_section():
    print("== cut surface is the model's own cross section")
    reset_scene()
    obj = make_cylinder(radius=10.0, height=60.0)
    dg = bpy.context.evaluated_depsgraph_get()

    res = section.plane_section(obj, Vector((0, 0, 5)), Vector((0, 0, 1)), depsgraph=dg)
    check(res is not None, "a plane through the cylinder gives a section")
    verts, faces = res
    area = patch_area(verts, faces)
    check(abs(area - math.pi * 100.0) / (math.pi * 100.0) < 0.02, f"section area {area:.0f} ~ {math.pi * 100:.0f}")
    check(abs(patch_extent(verts) - 20.0) < 0.5, f"section is as wide as the model ({patch_extent(verts):.2f} ~ 20)")
    check(all(abs(v.z - 5.0) < 1e-4 for v in verts), "section lies on the plane")

    # the whole point: two legs, a plane through both, only the one drawn on is cut
    reset_scene()
    legs = make_two_legs()
    dg = bpy.context.evaluated_depsgraph_get()

    both = section.plane_section(legs, Vector((0, 0, 5)), Vector((0, 0, 1)), depsgraph=dg)
    check(both is not None and patch_extent(both[0]) > 50.0, "with no reference the plane sections both legs")
    one = section.plane_section(legs, Vector((0, 0, 5)), Vector((0, 0, 1)), reference=Vector((-30, 0, 5)), depsgraph=dg)
    check(one is not None, "a reference point picks one leg")
    verts, faces = one
    check(
        abs(patch_extent(verts) - 20.0) < 0.5,
        f"only the referenced leg is sectioned (extent {patch_extent(verts):.2f} ~ 20)",
    )
    check(all(v.x < -10.0 for v in verts), "the section stays on the leg the stroke crossed")

    # growing the section pushes its rim off the model, but only by the margin asked for
    grown_v, grown_f = section.grow_section(verts, faces, 0.5, Vector((0, 0, 1)))
    check(
        abs(patch_extent(grown_v) - 21.0) < 0.2,
        f"grown section overshoots by the margin ({patch_extent(grown_v):.2f} ~ 21)",
    )

    # a hollow part sections into an annulus, not a filled disc
    reset_scene()
    outer = make_cylinder("Outer", radius=10.0, height=60.0, segments=64)
    bm = bmesh.new()
    bm.from_mesh(outer.data)
    inner = bmesh.new()
    bmesh.ops.create_cone(inner, cap_ends=True, cap_tris=True, segments=64, radius1=6.0, radius2=6.0, depth=80.0)
    bmesh.ops.reverse_faces(inner, faces=list(inner.faces))
    bm.from_mesh(mesh_utils.bmesh_to_mesh(inner, "_i"))
    inner.free()
    shell = make_object("Shell", bm)
    bpy.context.view_layer.update()
    res = section.plane_section(
        shell, Vector((0, 0, 0)), Vector((0, 0, 1)), depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    check(res is not None, "a hollow part still sections")
    area = patch_area(res[0], res[1])
    want = math.pi * (100.0 - 36.0)
    check(abs(area - want) / want < 0.05, f"hollow section is an annulus (area {area:.0f} ~ {want:.0f})")


def test_section_cut_leaves_the_other_leg():
    print("== a section sized cut only touches the leg it was drawn on")
    reset_scene()
    legs = make_two_legs()
    dg = bpy.context.evaluated_depsgraph_get()
    vol0 = mesh_utils.mesh_volume(legs.data)

    res = section.plane_section(
        legs, Vector((0, 0, 5)), Vector((0, 0, 1)), span=(Vector((1, 0, 0)), -45.0, -15.0), margin=0.4, depsgraph=dg
    )
    # what the boolean gets is a quad that runs out past the model, stopping in the
    # empty gap before the other leg - a rim in free space instead of one riding the
    # model's surface, which is what the exact solver can actually resolve
    check(res.cutter is not None, "the plane cut hands the boolean a quad")
    verts, faces = res.cutter
    check(max(v.x for v in verts) < 5.0, f"the quad stops short of the other leg (x <= {max(v.x for v in verts):.1f})")
    check(
        min(v.x for v in verts) < -40.0,
        f"and reaches out past the leg it does cut (x from {min(v.x for v in verts):.1f})",
    )
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(verts, faces, add_pin=False)], gap=0.2)
    a, b, _secs = cutting.perform_cut(bpy.context, legs, spec, ("A", "B"), out_collection("legs"))
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "both halves are closed manifold")
    kept = mesh_utils.mesh_volume(a.data) + mesh_utils.mesh_volume(b.data)
    check(abs(kept - vol0) / vol0 < 0.02, f"volume preserved ({kept:.0f} of {vol0:.0f})")
    # the untouched leg has to have stayed in one piece: whichever half holds it spans
    # the full 60 mm of height instead of being sliced at z=5 as well
    spans = []
    for part in (a, b):
        xs = [part.matrix_world @ v.co for v in part.data.vertices]
        right = [v for v in xs if v.x > 0]
        spans.append((max(v.z for v in right) - min(v.z for v in right)) if right else 0.0)
    check(
        abs(max(spans) - 60.0) < 0.5,
        f"the other leg came through whole (tallest right side piece {max(spans):.1f} ~ 60)",
    )


def make_saint(name="Saint"):
    """A torso with a sword alongside it, joined by a bar above and below the waist.

    The shape that broke the first version of the cross section: a plane through the
    waist crosses the torso AND the sword, and cutting only the torso leaves the two
    halves hanging off each other through the sword.
    """

    def cube(cx, cz, sx, sy, sz):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=list(bm.verts), vec=Vector((sx, sy, sz)))
        bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector((cx, 0.0, cz)))
        return bm

    def rod(r, h, cx):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=48, radius1=r, radius2=r, depth=h)
        bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector((cx, 0.0, 0.0)))
        return bm

    obj = make_object(name, rod(15.0, 100.0, 0.0))
    for part in (rod(4.0, 90.0, 35.0), cube(17.5, 40.0, 40.0, 6.0, 6.0), cube(17.5, -40.0, 40.0, 6.0, 6.0)):
        other = make_object("_tmp", part)
        mod = obj.modifiers.new("union", 'BOOLEAN')
        mod.operation = 'UNION'
        mod.object = other
        mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.update()
    return obj


def test_section_follows_the_stroke():
    print("== the stroke decides which regions are cut")
    reset_scene()
    legs = make_two_legs()
    dg = bpy.context.evaluated_depsgraph_get()
    co, no, x = Vector((0, 0, 5)), Vector((0, 0, 1)), Vector((1, 0, 0))

    # a line drawn across the left leg only, overshooting it by 5 mm on each side
    one = section.plane_section(legs, co, no, span=(x, -45.0, -15.0), depsgraph=dg)
    check(one.kept == 1 and one.islands == 2, f"one leg under the stroke, two crossed ({one.kept}/{one.islands})")
    check(all(v.x < -10.0 for v in one.verts), "only the leg the line ran across is sectioned")

    # a line dragged all the way across the figure takes both
    both = section.plane_section(legs, co, no, span=(x, -45.0, 45.0), depsgraph=dg)
    check(both.kept == 2, f"a line across the whole figure cuts both legs (kept {both.kept})")
    check(patch_extent(both.verts) > 50.0, "both legs are in the surface")


def test_section_reports_regions_it_left_out():
    print("== a cut that cannot separate says why")
    reset_scene()
    saint = make_saint()
    dg = bpy.context.evaluated_depsgraph_get()
    co, no, x = Vector((0, 0, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
    vol0 = mesh_utils.mesh_volume(saint.data)

    torso = section.plane_section(saint, co, no, span=(x, -18.0, 18.0), margin=0.3, depsgraph=dg)
    check(torso.islands == 2 and torso.kept == 1, f"the waist plane crosses torso and sword ({torso.islands})")

    cut = torso.cutter or (torso.verts, torso.faces)
    check(torso.cutter is not None, "a quad separates the torso from the sword")
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(cut[0], cut[1], add_pin=False, regions_skipped=1)], gap=0.17)
    try:
        cutting.perform_cut(bpy.context, saint, spec, ("A", "B"), out_collection("saint"))
        check(False, "cutting only the torso should not separate the saint")
    except cutting.CutError as e:
        check("1 other region" in str(e), f"the error names the region it left out: {e}")
        check("cross the whole part" not in str(e), "the old, misleading advice is gone")

    # dragging the line across the sword as well is what actually splits it
    reset_scene()
    saint = make_saint()
    dg = bpy.context.evaluated_depsgraph_get()
    full = section.plane_section(saint, co, no, span=(x, -18.0, 45.0), margin=0.3, depsgraph=dg)
    check(full.kept == 2, f"the longer line takes both regions (kept {full.kept})")
    cut = full.cutter or (full.verts, full.faces)
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(cut[0], cut[1], add_pin=False)], gap=0.17)
    a, b, _secs = cutting.perform_cut(bpy.context, saint, spec, ("A", "B"), out_collection("saint2"))
    check(is_closed_manifold(a.data) and is_closed_manifold(b.data), "both halves are closed manifold")
    kept = mesh_utils.mesh_volume(a.data) + mesh_utils.mesh_volume(b.data)
    check(abs(kept - vol0) / vol0 < 0.02, f"volume preserved ({kept:.0f} of {vol0:.0f})")


def test_connector_fits_the_section():
    print("== the connector is the biggest circle that fits in the section")
    reset_scene()
    saint = make_saint()
    dg = bpy.context.evaluated_depsgraph_get()
    both = section.plane_section(saint, Vector((0, 0, 0)), Vector((0, 0, 1)), depsgraph=dg)
    centre, diameter = section.inscribed_circle(both.verts, both.faces, Vector((0, 0, 1)))
    # the torso is 30 mm across, the sword 8 mm: the pin belongs in the torso
    check(centre.length < 1.0, f"the pin sits in the thick region, not out on the sword ({centre})")
    check(abs(diameter - 30.0) < 0.6, f"pin sized to the torso, not the sword ({diameter:.2f} ~ 30)")

    # a hollow part: the circle has to sit in the wall, never in the hole
    reset_scene()
    outer = make_cylinder("Outer", radius=20.0, height=60.0, segments=64)
    bm = bmesh.new()
    bm.from_mesh(outer.data)
    inner = bmesh.new()
    bmesh.ops.create_cone(inner, cap_ends=True, cap_tris=True, segments=64, radius1=14.0, radius2=14.0, depth=80.0)
    bmesh.ops.reverse_faces(inner, faces=list(inner.faces))
    bm.from_mesh(mesh_utils.bmesh_to_mesh(inner, "_i"))
    inner.free()
    shell = make_object("Shell", bm)
    bpy.context.view_layer.update()
    res = section.plane_section(
        shell, Vector((0, 0, 0)), Vector((0, 0, 1)), depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    centre, diameter = section.inscribed_circle(res.verts, res.faces, Vector((0, 0, 1)))
    check(abs(centre.length - 17.0) < 0.6, f"the circle sits in the wall ({centre.length:.2f} ~ 17)")
    check(abs(diameter - 6.0) < 0.4, f"and is as wide as the wall ({diameter:.2f} ~ 6)")


def test_runs_and_bands():
    print("== a curve cut only spans the material it was drawn on")
    # three slabs of material along one axis, the stroke standing on the middle one
    runs = [(-50.0, -30.0), (-5.0, 5.0), (30.0, 50.0)]
    band = section.band_around(runs, 0.0, pad=100.0)
    check(abs(band[0] + 17.5) < 1e-6 and abs(band[1] - 17.5) < 1e-6, f"the band stops in both gaps ({band})")

    # nothing on either side: the band just reaches out by the pad
    band = section.band_around([(-5.0, 5.0)], 0.0, pad=3.0)
    check(band == (-8.0, 8.0), f"an isolated run is padded out into free space ({band})")

    # a hollow limb: two runs a hair apart are one piece of material to cut through
    band = section.band_around([(0.0, 2.0), (2.0, 18.0), (18.0, 20.0)], 1.0, pad=1.0)
    check(band == (-1.0, 21.0), f"touching runs merge ({band})")

    # the anchor decides, not the size
    band = section.band_around([(-50.0, -30.0), (0.0, 4.0)], 2.0, pad=100.0)
    check(abs(band[0] - -15.0) < 1e-6, f"the run under the stroke wins over the bigger one ({band})")


def test_ribbon_follows_a_silhouette():
    print("== a ribbon can run to a different depth in every column")
    pts = [Vector((-10.0 + 20.0 * i / 9, 0.0, 0.0)) for i in range(10)]
    view = Vector((0, 1, 0))
    cols = surfaces.ribbon_samples(pts, 2.0, detail=3)
    check(len(cols) > len(pts), f"the stroke is splined into more columns ({len(cols)})")

    # a bulge in the middle, nothing at all under the two tails
    ranges = []
    for i, c in enumerate(cols):
        if i < 2 or i > len(cols) - 3:
            ranges.append(None)
        else:
            ranges.append((-1.0, 4.0 - abs(c.x) * 0.2))
    verts, faces = surfaces.ribbon_patch(pts, view, 0.0, 2.0, detail=3, depth_ranges=ranges)
    ys = [v.y for v in verts]
    check(max(ys) < 4.01, f"the surface stops at the silhouette ({max(ys):.2f} <= 4)")
    check(len(verts) == 2 * (len(cols) - 4), f"columns with nothing under them are dropped ({len(verts)})")
    xs = [v.x for v in verts]
    check(min(xs) > -12.0 and max(xs) < 12.0, "and the dropped tails take their vertices with them")

    # the connector works on a ribbon too, not only on a flat section
    plain = surfaces.ribbon_samples(pts, 0.0, detail=3)
    verts, faces = surfaces.ribbon_patch(pts, view, 0.0, 0.0, detail=3, depth_ranges=[(-6.0, 6.0)] * len(plain))
    centre, diameter = section.inscribed_circle(verts, faces, surfaces.patch_normal(verts, faces))
    check(abs(diameter - 12.0) < 0.8, f"a 12 mm deep ribbon takes a 12 mm pin ({diameter:.2f})")
    check(abs(centre.y) < 0.6 and abs(centre.x) < 4.5, f"placed where the whole circle fits ({centre})")


if __name__ == "__main__":
    t = time.time()
    test_straight_cut_with_pin()
    test_ribbon_cut()
    test_loop_cut()
    test_smooth_surfaces()
    test_two_contacts()
    test_custom_connector_and_remesh()
    test_freehand_loop_really_leaves_the_model()
    test_freehand_keeps_the_points_it_was_drawn_through()
    test_a_split_that_worked_is_not_reported_as_a_failure()
    test_edited_connector_is_the_one_built()
    test_stepped_cut()
    test_cross_section()
    test_section_cut_leaves_the_other_leg()
    test_section_follows_the_stroke()
    test_section_reports_regions_it_left_out()
    test_connector_fits_the_section()
    test_runs_and_bands()
    test_ribbon_follows_a_silhouette()
    print(f"\n{len(FAILS)} failure(s) in {time.time() - t:.1f}s")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)
