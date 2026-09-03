# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Headless add-on tests: registration, plan workflow, build/return/approve, explode, export, panel drawing.
Run:  blender -b --python tests/test_addon.py
"""

import math
import os
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import easy_slice_print  # noqa: E402
from easy_slice_print import plan, ui  # noqa: E402
from easy_slice_print.core import cutting, mesh_utils, surfaces  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


class DummyLayout:
    """Records UI calls; raises on unknown properties like Blender would."""

    def __init__(self):
        self.active = True
        self.enabled = True
        self.scale_y = 1.0

    def __getattr__(self, name):
        def call(*args, **kwargs):
            if name in ("prop",):
                data, prop = args[0], args[1]
                if not hasattr(data, prop) and prop not in data.bl_rna.properties:
                    raise AttributeError(f"layout.prop: {data} has no property '{prop}'")
            if name == "operator":
                idname = args[0]
                mod, op = idname.split('.')
                if not hasattr(getattr(bpy.ops, mod), op):
                    raise AttributeError(f"layout.operator: unknown operator '{idname}'")
                return DummyOp()
            return DummyLayout()

        return call


class DummyOp:
    def __setattr__(self, k, v):
        pass


def draw_all_panels(context):
    for cls in ui.CLASSES:
        if not hasattr(cls, "draw"):
            continue
        if hasattr(cls, "poll") and not cls.poll(context):
            continue
        fake = type("P", (), {})()
        fake.layout = DummyLayout()
        cls.draw(fake, context)
        if hasattr(cls, "draw_header"):
            cls.draw_header(fake, context)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = 'MILLIMETERS'
    return sc


def make_cylinder(name="Figure", radius=10.0, height=60.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=48, radius1=radius, radius2=radius, depth=height)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=3, use_grid_fill=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def plane_contact(z, diag, hit_x=10.0):
    d = plan.ContactData('STRAIGHT')
    d.verts, d.faces = surfaces.plane_patch(Vector((0, 0, z)), Vector((0, 0, 1)), Vector((1, 0, 0)), diag * 1.3)
    d.view_dir = Vector((-1, 0, 0))
    d.hit = Vector((hit_x, 0, z))
    d.through = Vector((-1, 0, 0))
    d.anchor = d.hit.copy()
    return d


def curve_contact(obj, diag):
    pts = [Vector((10.0, -14 + 28 * i / 19, 15.0 + 3.0 * math.sin(i / 19 * math.pi * 2))) for i in range(20)]
    d = plan.ContactData('CURVED')
    d.points = pts
    d.view_dir = Vector((-1, 0, 0))
    d.extend = diag * 0.1
    built = plan.ribbon_surfaces(bpy.context, obj, pts, d.view_dir, d.extend, d.detail)
    if built is not None:
        preview, cutter, band = built
        d.verts, d.faces = preview
        d.cutter = cutter
        d.depth_range = band
        d.is_cut_face = True
    else:
        d.depth_range = (-2.0, 22.0)
        d.verts, d.faces = surfaces.ribbon_patch(pts, d.view_dir, 0.0, d.extend, depth_range=d.depth_range)
    d.hit = pts[10].copy()
    d.through = d.view_dir
    d.anchor = d.hit.copy()
    return d


def make_two_legs(name="Legs", at=(-30.0, 30.0), radius=10.0, height=60.0):
    bm = bmesh.new()
    for x in at:
        leg = bmesh.new()
        bmesh.ops.create_cone(
            leg, cap_ends=True, cap_tris=True, segments=48, radius1=radius, radius2=radius, depth=height
        )
        bmesh.ops.translate(leg, verts=list(leg.verts), vec=Vector((x, 0, 0)))
        bm.from_mesh(mesh_utils.bmesh_to_mesh(leg, f"_leg{x}"))
        leg.free()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.context.view_layer.update()
    return obj


def world_bounds(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def test_plane_section_preview():
    """A plane cut's preview is the model's cross section, and it follows the plane."""
    print("== plane cut surface tracks the model's cross section")
    reset_scene()
    legs = make_two_legs()

    ref = Vector((-30.0, 0.0, 5.0))
    span = (Vector((1, 0, 0)), -45.0, -15.0)
    patch = plan.straight_section(bpy.context, legs, Vector((0, 0, 5)), Vector((0, 0, 1)), span, ref)
    check(patch is not None, "the plane sections the model")
    d = plan.ContactData('STRAIGHT')
    d.verts, d.faces = patch
    d.cutter = patch.cutter
    d.span = span
    d.is_cut_face = True
    d.view_dir = Vector((-1, 0, 0))
    d.plane_co = Vector((0, 0, 5))
    d.plane_no = Vector((0, 0, 1))
    d.hit = Vector((-20.0, 0.0, 5.0))
    d.through = Vector((1, 0, 0))
    d.anchor = ref.copy()
    rec = plan.add_record(bpy.context, legs, 'STRAIGHT', [d])

    sobj = bpy.data.objects.get(rec.surface_a)
    check(sobj is not None, "the preview surface was created")
    mn, mx = world_bounds(sobj)
    check(abs((mx.x - mn.x) - 20.2) < 0.6, f"preview is one leg wide, not the whole model ({mx.x - mn.x:.1f} ~ 20)")
    check(mx.x < -10.0, "preview sits on the leg the cut was drawn on")
    check(abs(mn.z - 5.0) < 0.1 and abs(mx.z - 5.0) < 0.1, "preview sits on the cut plane")

    cverts, _cfaces = plan.cutter_world_patch(sobj)
    check(len(cverts) == 4, f"the boolean is handed a quad, not the section ({len(cverts)} verts)")
    check(max(v.x for v in cverts) < 5.0, "and the quad stops in the gap before the other leg")

    # G on the preview: the plane moves, so the section is taken again where it landed
    sobj.matrix_world = Matrix.Translation(Vector((0.0, 0.0, 12.0))) @ sobj.matrix_world
    bpy.context.view_layer.update()
    plan.refresh_record_frames(bpy.context, rec)
    mn, mx = world_bounds(sobj)
    check(abs(mn.z - 17.0) < 0.1 and abs(mx.z - 17.0) < 0.1, f"moved preview re-sections at z=17 (got {mn.z:.1f})")
    check(abs((mx.x - mn.x) - 20.2) < 0.6, f"moved preview is still one leg wide ({mx.x - mn.x:.1f} ~ 20)")
    check(mx.x < -10.0, "moved preview stayed on the same leg")
    cverts, _cfaces = plan.cutter_world_patch(sobj)
    check(all(abs(v.z - 17.0) < 0.1 for v in cverts), "the quad followed the plane to z=17")
    check(max(v.x for v in cverts) < 5.0, "and still spares the other leg")

    centre = Vector(rec.center_a)
    check(abs(centre.z - 17.0) < 0.5 and centre.x < -10.0, f"the pin followed the section (centre {centre})")


def make_two_rods(name="Rods", at=(-40.0, 40.0), radius=10.0, height=80.0):
    """Two cylinders one behind the other along +Y - the far one must survive a cut."""
    bm = bmesh.new()
    for y in at:
        rod = bmesh.new()
        bmesh.ops.create_cone(
            rod, cap_ends=True, cap_tris=True, segments=48, radius1=radius, radius2=radius, depth=height
        )
        bmesh.ops.translate(rod, verts=list(rod.verts), vec=Vector((0.0, y, 0.0)))
        bm.from_mesh(mesh_utils.bmesh_to_mesh(rod, f"_rod{y}"))
        rod.free()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()
    return obj


def test_curve_cut_stops_at_the_model():
    """A curve drawn over the near rod must not reach through to the one behind it."""
    print("== curve cut follows the model instead of one flat depth")
    reset_scene()
    rods = make_two_rods()
    view = Vector((0, 1, 0))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for i in range(20):
        probe = Vector((-14.0 + 28.0 * i / 19, -80.0, 4.0 * math.sin(i / 19 * math.pi)))
        hit, loc, _n, _d = mesh_utils.object_ray_cast(rods, probe, view, depsgraph, max_dist=400.0)
        pts.append(loc if hit else probe)

    built = plan.ribbon_surfaces(bpy.context, rods, pts, view, 6.0, 3)
    check(built is not None, "the stroke finds material to follow")
    preview, cutter, band = built
    check(max(v.y for v in cutter[0]) < 25.0, "the surface the boolean gets stops in the gap, not on the far rod")
    check(min(v.y for v in cutter[0]) < -50.0, "which still reaches out past the near rod")
    py = [v.y for v in preview[0]]
    check(max(py) < -25.0, f"the preview stops on the near rod's own back ({max(py):.1f} < -25)")

    vol0 = mesh_utils.mesh_volume(rods.data)
    spec = cutting.CutSpec(contacts=[cutting.ContactSpec(cutter[0], cutter[1], add_pin=False)], gap=0.17)
    a, b, _secs = cutting.perform_cut(bpy.context, rods, spec, ("A", "B"), bpy.context.scene.collection)
    check(
        mesh_utils.manifold_report(a.data)[:2] == (0, 0) and mesh_utils.manifold_report(b.data)[:2] == (0, 0),
        "both halves are closed manifold",
    )
    kept = mesh_utils.mesh_volume(a.data) + mesh_utils.mesh_volume(b.data)
    check(abs(kept - vol0) / vol0 < 0.02, f"volume preserved ({kept:.0f} of {vol0:.0f})")
    spans = []
    for part in (a, b):
        far = [part.matrix_world @ v.co for v in part.data.vertices if (part.matrix_world @ v.co).y > 20.0]
        spans.append((max(p.z for p in far) - min(p.z for p in far)) if far else 0.0)
    check(abs(max(spans) - 80.0) < 0.5, f"the far rod came through whole ({max(spans):.1f} ~ 80)")


def test_freehand_connector_fits_the_loop():
    """The pin on a freehand cut is measured from the loop, not from a bundle of rays."""
    print("== freehand connector is measured from the loop it was drawn on")
    reset_scene()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=64, radius1=12.0, radius2=12.0, depth=100.0)
    me = bpy.data.meshes.new("Rod")
    bm.to_mesh(me)
    bm.free()
    rod = bpy.data.objects.new("Rod", me)
    bpy.context.scene.collection.objects.link(rod)
    bpy.context.view_layer.update()

    margin = 0.6  # what the tool pushes the drawn loop out by, so its rim clears the model
    pts = []
    for i in range(40):
        ang = 2.0 * math.pi * i / 40
        nrm = Vector((math.cos(ang), math.sin(ang), 0.0))
        pts.append(nrm * (12.0 + margin) + Vector((0.0, 0.0, 6.0 * math.cos(ang))))
    verts, faces = surfaces.loop_patch(pts, detail=3)

    centre, _normal, inscribed = plan.contact_frame(
        bpy.context, rod, verts, faces, center_hint=Vector((0, 0, 0)), is_cut_face=True, shrink=margin * 2.0
    )
    check(abs(inscribed - 24.0) < 1.0, f"pin sized to the rod, not to the loop's clearance ({inscribed:.2f} ~ 24)")
    check(centre.xy.length < 1.0, f"and placed in the middle of the cut face ({centre})")


def test_printer_fit():
    """The Fit preset must decide how much wider the socket comes out than the pin."""
    print("== printer fit / clearance")
    from easy_slice_print.core import connectors

    sc = reset_scene()
    base = plan.printer_clearance_mm(bpy.context)
    check(abs(base - 0.10) < 1e-9, f"printer clearance defaults to 0.10 mm (got {base})")
    check(sc.esp.fit_preset == 'SNUG', f"new cuts start on the Snug fit (got {sc.esp.fit_preset})")

    expected = {'PRESS': 0.05, 'SNUG': 0.10, 'EASY': 0.15, 'LOOSE': 0.25}
    for preset, want in expected.items():
        got = plan.preset_clearance_mm(bpy.context, preset)
        check(abs(got - want) < 1e-9, f"{preset} fit -> {want:.2f} mm per side (got {got:.3f})")

    # the preset has to land in the field the panel shows and the build reads
    for preset, want in expected.items():
        sc.esp.fit_preset = preset
        check(abs(sc.esp.clearance_mm - want) < 1e-6, f"{preset} written into the gap field")
    sc.esp.fit_preset = 'CUSTOM'
    sc.esp.clearance_mm = 0.42
    plan.apply_fit(bpy.context, sc.esp)
    check(abs(sc.esp.clearance_mm - 0.42) < 1e-6, "Custom fit keeps the typed gap")

    # what actually gets printed: the socket cavity against the pin, same call the build makes
    matrix = connectors.connector_matrix(Vector((0, 0, 0)), Vector((0, 0, 1)), 6.0, 7.0)
    for gap in (0.05, 0.10, 0.25):
        pin = connectors.connector_mesh('CYLINDER', None, matrix, "pin")
        socket = connectors.connector_mesh('CYLINDER', None, matrix, "socket", radial_extra=gap)
        pmn, pmx = mesh_utils.mesh_bounds(pin)
        smn, smx = mesh_utils.mesh_bounds(socket)
        widened = (smx.x - smn.x) - (pmx.x - pmn.x)
        check(abs(widened - 2.0 * gap) < 1e-4, f"gap {gap:.2f} -> socket {widened:.3f} mm wider (want {2 * gap:.2f})")
        # the pin itself must never change: only the socket opens up
        check(abs((pmx.x - pmn.x) - 6.0) < 1e-4, f"pin stays {pmx.x - pmn.x:.3f} mm across at gap {gap:.2f}")
        for m in (pin, socket):
            mesh_utils.remove_mesh(m)


def test_version():
    """The sidebar must never show a version other than the one Blender installed."""
    print("== version")
    import tomllib

    from easy_slice_print import version as ver

    with open(os.path.join(ROOT, "easy_slice_print", "blender_manifest.toml"), "rb") as fh:
        manifest = tomllib.load(fh)
    check(manifest["version"] == ver.VERSION, f"version {ver.VERSION} == manifest {manifest['version']}")
    check(manifest["version"] == ui.VERSION, "the panel reads the manifest version")
    check(ver.STAGE in ("", "alpha", "beta"), f"stage {ver.STAGE!r}")


def test_register():
    print("== register")
    easy_slice_print.register()
    check(hasattr(bpy.types.Scene, "esp"), "scene.esp registered")
    check(hasattr(bpy.ops.esp, "cut_straight") and hasattr(bpy.ops.esp, "build"), "operators registered")


def test_plan_workflow():
    print("== plan workflow")
    sc = reset_scene()
    obj = make_cylinder()
    s = sc.esp
    s.mode = 'PLAN'
    diag = mesh_utils.object_world_diagonal(obj)
    ctx = bpy.context
    rec1 = plan.add_record(ctx, obj, 'STRAIGHT', [plane_contact(-10.0, diag)])
    rec2 = plan.add_record(ctx, obj, 'CURVED', [curve_contact(obj, diag)])
    check(len(s.cuts) == 2 and s.active_cut == 1, "two records added")
    check(
        bpy.data.objects.get(rec1.surface_a) is not None and bpy.data.objects.get(rec1.pin_a) is not None,
        "preview objects exist",
    )
    check(abs(rec1.inscribed_a - 20.0) < 1.0, f"record inscribed diameter {rec1.inscribed_a:.2f}")
    check(abs(rec1.pin_width_mm - 9.0) < 0.5, f"preset width from inscribed: {rec1.pin_width_mm:.2f} mm")
    # change settings on the record -> preview follows
    pin = bpy.data.objects.get(rec1.pin_a)
    old_scale = pin.scale.copy()
    rec1.size_preset = 'LARGE'
    check(pin.scale.x > old_scale.x, "preset change rescaled the pin preview")
    rec1.pin_side = 'B'
    check(pin.matrix_world.col[2].xyz.z > 0.5, "swap side flipped the pin direction (+Z now up)")
    rec1.shape = 'HEX'
    check(pin.get("esp_shape") == 'HEX' and len(pin.data.polygons) == 8, "shape change rebuilt the pin mesh")
    # user moves the pin -> delta preserved on later changes
    pin.location.x += 2.0
    rec1.size_preset = 'SMALL'
    check(abs(pin.location.x - 2.0) < 1e-3, "user offset preserved through size change")
    plan.reset_pins(ctx, rec1)
    check(abs(pin.location.x) < 1e-3, "reset pin transform")
    draw_all_panels(ctx)
    check(True, "panels draw (plan mode, with record)")
    # disable the curve cut, build
    rec2.enabled = False
    res = bpy.ops.esp.build()
    check(res == {'FINISHED'} and s.built, "build finished")
    col = bpy.data.collections.get(s.built_collection)
    check(col is not None and len(col.objects) == 2, f"built collection has 2 parts ({len(col.objects) if col else 0})")
    check(
        obj.hide_get() and obj.name in bpy.data.collections[plan.BACKUP_COLLECTION].objects, "original hidden in backup"
    )
    for o in col.objects:
        non, boundary, _t = mesh_utils.manifold_report(o.data)
        check(non == 0 and boundary == 0, f"{o.name} closed manifold")
    # add the curve cut back and rebuild -> 3 parts
    rec2.enabled = True
    res = bpy.ops.esp.build()
    col = bpy.data.collections.get(s.built_collection)
    check(res == {'FINISHED'} and len(col.objects) == 3, f"rebuild with 2 cuts -> 3 parts ({len(col.objects)})")
    names = sorted(o.name for o in col.objects)
    check(names == ["Figure_PART_001", "Figure_PART_002", "Figure_PART_003"], f"part names {names}")
    draw_all_panels(ctx)
    # explode / collapse
    s.explode_distance_mm = 5.0
    res = bpy.ops.esp.explode()
    check(res == {'FINISHED'} and s.exploded, "exploded")
    moved = [o for o in col.objects if o.location.length > 1e-6]
    check(len(moved) >= 2, "parts moved apart")
    res = bpy.ops.esp.collapse()
    check(all(o.location.length < 1e-6 for o in col.objects), "collapsed back")
    # export
    tmp = tempfile.mkdtemp(prefix="esp_export_")
    s.export_folder = tmp
    for fmt in ('STL', 'OBJ', 'FBX'):
        s.export_format = fmt
        res = bpy.ops.esp.export_parts()
        files = [f for f in os.listdir(tmp) if f.lower().endswith(fmt.lower())]
        check(res == {'FINISHED'} and len(files) == 3, f"exported 3 {fmt} files")
    # return to plan
    res = bpy.ops.esp.return_to_plan()
    check(
        res == {'FINISHED'} and not s.built and bpy.data.collections.get("ESP_Built_Figure") is None, "returned to plan"
    )
    check(not obj.hide_get(), "original visible again")
    # build & approve without keeping the original
    s.keep_original = False
    bpy.ops.esp.build()
    res = bpy.ops.esp.approve()
    check(
        res == {'FINISHED'} and len(s.cuts) == 0 and bpy.data.objects.get("Figure") is None,
        "approve cleared plan and removed original",
    )
    check(len(bpy.data.collections["ESP_Built_Figure"].objects) == 3, "parts survived approve")
    draw_all_panels(ctx)


def test_cut_after_approve():
    """A cut drawn on an approved part cuts that part, not the model it came from."""
    print("== cutting an approved part")
    sc = reset_scene()
    obj = make_cylinder("Chain")  # z from -30 to 30
    s = sc.esp
    s.mode = 'PLAN'
    s.keep_original = True
    diag = mesh_utils.object_world_diagonal(obj)
    ctx = bpy.context
    plan.add_record(ctx, obj, 'STRAIGHT', [plane_contact(-10.0, diag)])
    bpy.ops.esp.build()
    bpy.ops.esp.approve()
    parts = sorted(bpy.data.collections["ESP_Built_Chain"].objects, key=lambda o: world_bounds(o)[0].z)
    check(len(parts) == 2 and obj.hide_get(), "approved 2 parts, original stashed")
    upper = parts[1]  # -10 .. 30
    ctx.view_layer.objects.active = upper
    plan.add_record(ctx, upper, 'STRAIGHT', [plane_contact(10.0, diag)])
    check(s.base_object == upper.name, f"plan rooted at the approved part ({s.base_object})")
    res = bpy.ops.esp.build()
    col = bpy.data.collections.get(s.built_collection)
    check(res == {'FINISHED'} and col is not None and len(col.objects) == 2, "second build made 2 parts")
    # the part starts at z=-10 and its connector hangs a little below that; the whole
    # model would reach z=-30, so a bottom near -30 means the original got cut instead
    low = min(world_bounds(o)[0].z for o in col.objects)
    check(low > -25.0, f"cut the approved part, not the whole model (lowest z {low:.1f})")
    check(upper.hide_get(), "the cut part went to the backup")
    check(bpy.data.objects.get("Chain") is not None, "the original is untouched")
    check(bpy.data.objects.get(parts[0].name) is not None, "the other approved part survived")
    draw_all_panels(ctx)
    res = bpy.ops.esp.return_to_plan()
    check(res == {'FINISHED'} and not upper.hide_get(), "back to plan restored the approved part")


def test_quick_mode():
    print("== quick mode")
    sc = reset_scene()
    obj = make_cylinder("Quick")
    s = sc.esp
    s.mode = 'QUICK'
    s.size_preset = 'MEDIUM'
    diag = mesh_utils.object_world_diagonal(obj)
    from easy_slice_print.ops_tools import quick_cut

    a, b, secs = quick_cut(bpy.context, obj, [plane_contact(0.0, diag)])
    check({a.name, b.name} == {"Quick_UPPER", "Quick_LOWER"}, f"quick names {a.name}/{b.name}")
    check(obj.hide_get(), "original kept hidden")
    upper = a if a.name.endswith("UPPER") else b
    mn, _mx = mesh_utils.mesh_bounds(upper.data)
    check(mn.z < -3.0, f"upper part carries the pin (min z {mn.z:.2f})")
    draw_all_panels(bpy.context)
    # two contacts in quick mode with skip of original
    s.keep_original = False
    s.two_contact = True
    obj2 = make_cylinder("Quick2")
    a, b, secs = quick_cut(bpy.context, obj2, [plane_contact(-20.0, diag), plane_contact(-20.0, diag)])
    check(bpy.data.objects.get("Quick2") is None, "original deleted when Keep Original is off")


def test_unregister():
    print("== unregister")
    easy_slice_print.unregister()
    check(not hasattr(bpy.types.Scene, "esp"), "scene.esp removed")


if __name__ == "__main__":
    test_version()
    test_register()
    test_plan_workflow()
    test_cut_after_approve()
    test_quick_mode()
    test_printer_fit()
    test_curve_cut_stops_at_the_model()
    test_freehand_connector_fits_the_loop()
    test_plane_section_preview()
    test_unregister()
    print(f"\n{len(FAILS)} failure(s)")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)
