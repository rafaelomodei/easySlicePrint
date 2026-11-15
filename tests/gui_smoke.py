# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Drive the real Blender UI: the cut tools with simulated mouse and keys, and the panels.

The headless suites call the add-on's functions; this runs the modal tools the way a
person does - a drag in the viewport, Ctrl+Z, Enter - and takes screenshots of what
they leave on screen. It needs a display:

    blender --factory-startup --enable-event-simulate --python tests/gui_smoke.py -- <out_dir>

Real input is ignored while it runs. Screenshots and `report.json` land in <out_dir>.
"""

import json
import os
import sys
import traceback

import bmesh
import bpy
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(ROOT, "tmp", "gui")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, ROOT)

import easy_slice_print  # noqa: E402
from easy_slice_print import ui  # noqa: E402
from easy_slice_print.core import mesh_utils  # noqa: E402

# every sub-panel open, so the screenshots show all of them
for cls in ui.CLASSES:
    opts = set(getattr(cls, "bl_options", set()))
    if 'DEFAULT_CLOSED' in opts:
        cls.bl_options = opts - {'DEFAULT_CLOSED'}
easy_slice_print.register()

RESULTS = []


def check(ok, msg):
    RESULTS.append({"ok": bool(ok), "msg": msg})
    print(("  PASS " if ok else "  FAIL ") + msg, flush=True)


# ----------------------------------------------------------------------------
# scene
# ----------------------------------------------------------------------------
def view3d():
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return win, area, region


def override():
    win, area, region = view3d()
    return bpy.context.temp_override(window=win, area=area, region=region)


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    s = bpy.context.scene.esp
    s.cuts.clear()
    s.active_cut = -1
    s.built = False
    s.base_object = ""
    s.built_collection = ""
    s.exploded = False


def solid(name, build):
    bm = bmesh.new()
    build(bm)
    obj = bpy.data.objects.new(name, mesh_utils.bmesh_to_mesh(bm, name))
    bm.free()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box(bm, centre, size):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(centre) @ Matrix.Diagonal((*size, 1.0)))


def cyl(bm, centre, radius, depth):
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=True,
        segments=32,
        radius1=radius,
        radius2=radius,
        depth=depth,
        matrix=Matrix.Translation(centre),
    )


def table(name, legs, top=(70, 40, 10)):
    """A slab on legs: [(kind, x, y, size)], kind 'BOX' (side) or 'CYL' (radius)."""
    ctx = bpy.context
    parts = [solid(f"{name}_top", lambda bm: box(bm, (0, 0, 45), top))]
    for i, (kind, x, y, size) in enumerate(legs):
        if kind == 'BOX':
            parts.append(solid(f"_l{i}", lambda bm, x=x, y=y, k=size: box(bm, (x, y, 20), (k, k, 42))))
        else:
            parts.append(solid(f"_l{i}", lambda bm, x=x, y=y, r=size: cyl(bm, (x, y, 20), r, 42)))
    me = mesh_utils.world_mesh_copy(ctx, parts[0], "_f0")
    for i, o in enumerate(parts[1:]):
        me = mesh_utils.boolean_mesh(ctx, me, mesh_utils.world_mesh_copy(ctx, o, f"_f{i + 1}"), 'UNION', 'EXACT')
    for o in parts:
        mesh_utils.remove_object(o)
    mesh_utils.cleanup_temp(ctx.scene)
    obj = bpy.data.objects.new(name, me)
    ctx.scene.collection.objects.link(obj)
    ctx.view_layer.update()
    for o in ctx.scene.objects:
        if o is not None and o != obj:
            o.select_set(False)
    ctx.view_layer.objects.active = obj
    obj.select_set(True)
    ctx.view_layer.update()
    return obj


def front_view(obj, persp=False):
    _win, area, _region = view3d()
    space = area.spaces.active
    space.show_region_ui = True
    space.overlay.show_floor = True
    with override():
        bpy.ops.view3d.view_axis(type='FRONT', align_active=False)
        bpy.ops.view3d.view_selected()
    rv3d = space.region_3d
    rv3d.view_perspective = 'ORTHO'
    rv3d.view_distance *= 1.6
    if persp:
        rv3d.view_rotation = (Matrix.Rotation(0.5, 4, 'Z') @ Matrix.Rotation(1.15, 4, 'X')).to_quaternion()
        rv3d.view_perspective = 'PERSP'
    try:
        for r in area.regions:
            if r.type == 'UI':
                r.active_panel_category = ui.CATEGORY
    except Exception as e:  # read-only before 4.x: the tab stays where it was
        print("panel category:", e)


# ----------------------------------------------------------------------------
# input
# ----------------------------------------------------------------------------
def to_window(world):
    win, area, region = view3d()
    p = view3d_utils.location_3d_to_region_2d(region, area.spaces.active.region_3d, Vector(world))
    return int(region.x + p.x), int(region.y + p.y)


def ev(type, value, xy=None, **mods):
    win, _a, _r = view3d()
    if xy is None:
        win.event_simulate(type, value, **mods)
    else:
        win.event_simulate(type, value, x=xy[0], y=xy[1], **mods)


def key(type, **mods):
    ev(type, 'PRESS', **mods)
    ev(type, 'RELEASE', **mods)


def drag(points):
    """Press at the first world point, move through the rest, release at the last."""
    pts = [to_window(p) for p in points]
    ev('MOUSEMOVE', 'NOTHING', pts[0])
    yield 0.1
    ev('LEFTMOUSE', 'PRESS', pts[0])
    yield 0.1
    for p in pts[1:]:
        ev('MOUSEMOVE', 'NOTHING', p)
        yield 0.03
    ev('LEFTMOUSE', 'RELEASE', pts[-1])
    yield 0.4


def shot(name):
    win, _a, _r = view3d()
    path = os.path.join(OUT, f"{name}.png")
    with bpy.context.temp_override(window=win):
        bpy.ops.screen.screenshot(filepath=path)
    print("  shot", path, flush=True)


def tool(idname):
    with override():
        getattr(bpy.ops.esp, idname)('INVOKE_DEFAULT')


def built_parts():
    s = bpy.context.scene.esp
    col = bpy.data.collections.get(s.built_collection) if s.built_collection else None
    return list(col.objects) if col else []


def pins_under(part, below_z, legs):
    pts = [part.matrix_world @ v.co for v in part.data.vertices]
    pts = [p for p in pts if p.z < below_z]
    hit = [any((p.xy - Vector((x, y))).length < size for p in pts) for _k, x, y, size in legs]
    stray = [p for p in pts if all((p.xy - Vector((x, y))).length >= size for _k, x, y, size in legs)]
    return hit, stray


# ----------------------------------------------------------------------------
# scenarios
# ----------------------------------------------------------------------------
def scenario_plane_three_legs():
    print("== Plan Mode: one Plane stroke across three legs", flush=True)
    clear_scene()
    s = bpy.context.scene.esp
    s.mode = 'PLAN'
    s.multi_contact = True
    legs = [('BOX', x, 0, 10) for x in (-25, 0, 25)]
    obj = table("Stool", legs)
    front_view(obj)
    yield 0.5
    shot("01_stool_setup")
    tool("cut_straight")
    yield 0.3
    yield from drag([(-42, 0, 15), (42, 0, 15)])
    shot("02_stool_stroke_drawn")
    check(len(s.cuts) == 0, "nothing is cut before Enter")
    key('RET')
    yield 1.0
    check(len(s.cuts) == 1, f"Enter adds one cut ({len(s.cuts)})")
    if not s.cuts:
        return
    rec = s.cuts[0]
    check(len(rec.contacts) == 3, f"one stroke across three legs -> {len(rec.contacts)} contacts")
    xs = sorted(round(Vector(c.center).x) for c in rec.contacts)
    check(all(abs(a - b) <= 2 for a, b in zip(xs, (-25, 0, 25))), f"a connector on each leg (x {xs})")
    check(all(bpy.data.objects.get(c.pin) for c in rec.contacts), "three connector previews")
    shot("03_stool_three_pins")
    rec.active_contact = 2
    with override():
        bpy.ops.esp.select_pin()
    active = bpy.context.view_layer.objects.active
    check(active is not None and active.name == rec.contacts[1].pin, "Contact 2 + Select Connector selects pin B")
    yield 0.3
    shot("04_plan_panel_contact_picker")
    with override():
        res = bpy.ops.esp.build()
    yield 0.5
    parts = built_parts()
    check(res == {'FINISHED'} and len(parts) == 4, f"Build -> the top and three feet, each a part ({len(parts)})")
    if len(parts) == 4:
        top = max(parts, key=lambda o: mesh_utils.mesh_centroid(o.data).z)
        hit, stray = pins_under(top, 14.5, legs)
        check(all(hit) and not stray, f"the top carries a pin into every leg ({sum(hit)}/3)")
        for o in parts:
            non, boundary, _t = mesh_utils.manifold_report(o.data)
            check(non == 0 and boundary == 0, f"{o.name} closed manifold")
    s.explode_distance_mm = 18.0
    with override():
        bpy.ops.esp.explode()
    front_view(obj, persp=True)
    with override():
        bpy.ops.view3d.view_all()
    yield 0.5
    shot("05_stool_built_exploded")


def scenario_quick_grid_undo():
    print("== Quick Mode: two strokes, Ctrl+Z, Enter", flush=True)
    clear_scene()
    s = bpy.context.scene.esp
    s.mode = 'QUICK'
    s.multi_contact = True
    s.keep_original = True
    legs = [('BOX', x, y, 9) for x in (-22, 22) for y in (-12, 12)]
    obj = table("Grid", legs)
    front_view(obj)
    yield 0.5
    tool("cut_straight")
    yield 0.3
    yield from drag([(-36, 0, 15), (-8, 0, 15)])  # the left pair: two legs, one behind the other
    yield from drag([(8, 0, 15), (36, 0, 15)])
    shot("06_grid_two_strokes")
    key('Z', ctrl=True)
    yield 0.3
    shot("07_grid_after_ctrl_z")
    yield from drag([(8, 0, 15), (36, 0, 15)])
    key('RET')
    for _ in range(40):  # the quick cut runs as a job, a step per timer tick
        yield 0.25
        if bpy.data.objects.get("Grid_UPPER"):
            break
    up = bpy.data.objects.get("Grid_UPPER")
    feet = [bpy.data.objects.get(f"Grid_LOWER_{k}") for k in range(1, 5)]
    check(up is not None and all(feet), "Quick cut made Grid_UPPER and Grid_LOWER_1..4, a part per foot")
    if up is not None:
        hit, stray = pins_under(up, 14.5, legs)
        check(all(hit) and not stray, f"after Ctrl+Z and redraw: a pin in each of the 4 legs ({sum(hit)}/4)")
    front_view(up or obj, persp=True)
    if up is not None:
        up.location.z += 15.0
    for k, foot in enumerate(f for f in feet if f):
        foot.location.x += (-1) ** k * 4.0
    with override():
        bpy.ops.view3d.view_all()
    yield 0.5
    shot("08_grid_quick_cut")


def scenario_curve_two_contacts():
    print("== Curve tool: one contact per leg, Enter", flush=True)
    clear_scene()
    s = bpy.context.scene.esp
    s.mode = 'PLAN'
    s.multi_contact = True
    legs = [('CYL', -22, 0, 5), ('CYL', 22, 0, 9)]
    obj = table("Pair", legs)
    front_view(obj)
    yield 0.5
    tool("cut_curved")
    yield 0.3
    for x, r in ((-22, 5), (22, 9)):
        pts = [(x - r - 6 + (2 * r + 12) * i / 12, 0, 15 + 2.0 * (i % 2)) for i in range(13)]
        yield from drag(pts)
    shot("09_curve_two_strokes")
    key('RET')
    yield 1.0
    rec = s.cuts[0] if s.cuts else None
    check(rec is not None and len(rec.contacts) == 2, "two curve contacts, one record")
    if rec is not None:
        check(rec.cut_type == 'CURVED' and rec.name.startswith("Base Split"), f"record {rec.name} ({rec.cut_type})")
    yield 0.3
    shot("10_curve_record_panel")
    with override():
        res = bpy.ops.esp.build()
    yield 0.5
    check(all(len(o.data.vertices) for o in built_parts()), "no part comes out empty")
    if built_parts():
        front_view(built_parts()[0], persp=True)
        with override():
            bpy.ops.view3d.view_all()
        yield 0.4
        shot("10b_curve_built")
    check(
        res == {'FINISHED'} and len(built_parts()) == 3,
        f"curve base split: the top and two feet ({len(built_parts())})",
    )


def scenario_panels():
    """The sidebar from top to bottom, with a multi-contact cut selected (left by the curve scenario)."""
    print("== Sidebar panels", flush=True)
    s = bpy.context.scene.esp
    s.mode = 'PLAN'
    if bpy.context.scene.esp.built:
        with override():
            bpy.ops.esp.return_to_plan()
    if len(s.cuts):
        s.active_cut = 0
    _win, area, _region = view3d()
    ui_region = next(r for r in area.regions if r.type == 'UI')
    at = (ui_region.x + ui_region.width // 2, ui_region.y + ui_region.height // 2)
    ev('MOUSEMOVE', 'NOTHING', at)
    yield 0.3
    for i in range(4):
        shot(f"11_sidebar_{i}")
        for _ in range(8):
            ev('WHEELDOWNMOUSE', 'PRESS', at)
        yield 0.3


def run():
    for scenario in (
        scenario_plane_three_legs,
        scenario_quick_grid_undo,
        scenario_curve_two_contacts,
        scenario_panels,
    ):
        try:
            yield from scenario()
        except Exception:
            traceback.print_exc()
            check(False, f"{scenario.__name__} raised")


def main():
    gen = run()

    def step():
        try:
            return next(gen)
        except StopIteration:
            fails = [r for r in RESULTS if not r["ok"]]
            with open(os.path.join(OUT, "report.json"), "w") as f:
                json.dump(RESULTS, f, indent=1)
            print(f"\n{len(fails)} failure(s)", flush=True)
            bpy.ops.wm.quit_blender()
            return None
        except Exception:
            traceback.print_exc()
            bpy.ops.wm.quit_blender()
            return None

    bpy.app.timers.register(step, first_interval=1.0)


bpy.context.preferences.view.show_splash = False
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = 'MILLIMETERS'
main()
