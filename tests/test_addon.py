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
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import easy_slice_print  # noqa: E402
from easy_slice_print import plan, ui  # noqa: E402
from easy_slice_print.core import mesh_utils, surfaces  # noqa: E402

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
    d.depth_range = (-2.0, 22.0)
    d.extend = diag * 0.5
    d.verts, d.faces = surfaces.ribbon_patch(pts, d.view_dir, 0.0, d.extend, depth_range=d.depth_range)
    d.hit = pts[10].copy()
    d.through = d.view_dir
    d.anchor = d.hit.copy()
    return d


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
    test_register()
    test_plan_workflow()
    test_quick_mode()
    test_unregister()
    print(f"\n{len(FAILS)} failure(s)")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)
