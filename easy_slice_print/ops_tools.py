"""Interactive cut tools (modal operators): plane, curve and freehand cuts."""

import math

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from . import draw, plan
from .core import cutting, mesh_utils, surfaces

NAV_EVENTS = {
    'MIDDLEMOUSE',
    'WHEELUPMOUSE',
    'WHEELDOWNMOUSE',
    'WHEELINMOUSE',
    'WHEELOUTMOUSE',
    'TRACKPADPAN',
    'TRACKPADZOOM',
    'MOUSEROTATE',
    'MOUSESMARTZOOM',
    'NUMPAD_0',
    'NUMPAD_1',
    'NUMPAD_2',
    'NUMPAD_3',
    'NUMPAD_4',
    'NUMPAD_5',
    'NUMPAD_6',
    'NUMPAD_7',
    'NUMPAD_8',
    'NUMPAD_9',
    'NUMPAD_PERIOD',
    'NUMPAD_PLUS',
    'NUMPAD_MINUS',
    'HOME',
    'LEFT_SHIFT',
    'RIGHT_SHIFT',
    'LEFT_CTRL',
    'RIGHT_CTRL',
    'LEFT_ALT',
    'RIGHT_ALT',
}


def window_region(area):
    for r in area.regions:
        if r.type == 'WINDOW':
            return r
    return None


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def schedule_chain(idname, window, area):
    """Start the same tool again after the current one finished (Chain Cuts)."""

    def cb():
        region = window_region(area)
        try:
            with bpy.context.temp_override(window=window, area=area, region=region):
                mod, op = idname.split('.')
                getattr(getattr(bpy.ops, mod), op)('INVOKE_DEFAULT')
        except Exception:
            pass
        return None

    bpy.app.timers.register(cb, first_interval=0.1)


def quick_cut(context, target, contacts):
    settings = context.scene.esp
    scene = context.scene
    spec = plan.quick_spec(context, target, contacts)
    base_name = target.get("esp_base", target.name) if target.get("esp_part") else target.name
    col = plan.built_collection(scene, base_name)
    state = plan.ensure_evaluable(target)
    try:
        a, b, secs = cutting.perform_cut(context, target, spec, ("_esp_new_a", "_esp_new_b"), col)
    finally:
        plan.restore_visibility(target, state)
    la, lb = cutting.side_labels(mesh_utils.mesh_centroid(a.data), mesh_utils.mesh_centroid(b.data))
    a.name = f"{target.name}_{la}"
    b.name = f"{target.name}_{lb}"
    a.data.name = a.name
    b.data.name = b.name
    for o in (a, b):
        o["esp_base"] = base_name
    if settings.keep_original:
        plan.move_to_backup(scene, target)
    else:
        mesh_utils.remove_object(target)
    for o in context.view_layer.objects:
        o.select_set(False)
    a.select_set(True)
    b.select_set(True)
    context.view_layer.objects.active = a
    return a, b, secs


class CutToolBase:
    bl_options = {'REGISTER', 'UNDO'}
    kind = 'STRAIGHT'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and plan.resolve_target(context) is not None

    # -- lifecycle ----------------------------------------------------------
    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Run the cut tools from the 3D Viewport")
            return {'CANCELLED'}
        self.area = context.area
        self.window = context.window
        self.region = window_region(self.area)
        if self.region is None:
            return {'CANCELLED'}
        self.rv3d = self.region.data
        self.target = plan.resolve_target(context)
        settings = context.scene.esp
        settings.tool = self.kind
        if plan.pref(context, "check_mesh", True):
            non, boundary, total = mesh_utils.manifold_report(self.target.data, limit=200000)
            if non or boundary:
                self.report(
                    {'WARNING'},
                    f"'{self.target.name}' is not a closed manifold mesh "
                    f"({boundary} boundary / {non} non-manifold edges). Results may be wrong.",
                )
        self.diag = mesh_utils.object_world_diagonal(self.target)
        mn, mx = mesh_utils.object_world_bounds(self.target)
        self.bcenter = (mn + mx) * 0.5
        self.contacts_needed = 2 if settings.two_contact else 1
        self.contacts = []
        self.mouse = (0, 0)
        self.reset_stroke()
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self._draw_cb, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        self.update_status(context)
        return {'RUNNING_MODAL'}

    def reset_stroke(self):
        self.stroke = []
        self.drawing = False
        self.start2d = None
        self.click_mode = False
        self.loop = []
        self.loop2d = []

    def end(self, context):
        if getattr(self, "_handle", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        context.workspace.status_text_set(None)
        try:
            self.area.header_text_set(None)
        except Exception:
            pass
        self.area.tag_redraw()

    def coord(self, event):
        return (event.mouse_x - self.region.x, event.mouse_y - self.region.y)

    def modal(self, context, event):
        self.mouse = self.coord(event)
        if event.type in NAV_EVENTS:
            return {'PASS_THROUGH'}
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self.end(context)
            self.report({'INFO'}, "Cut cancelled")
            return {'CANCELLED'}
        result = None
        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            result = self.on_confirm(context)
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                result = self.on_press(context, self.mouse)
            elif event.value == 'RELEASE':
                result = self.on_release(context, self.mouse)
        elif event.type == 'MOUSEMOVE':
            result = self.on_move(context, self.mouse)
        self.area.tag_redraw()
        if result is not None:
            return result
        return {'RUNNING_MODAL'}

    def _draw_cb(self, context):
        if bpy.context.region is None or bpy.context.region.as_pointer() != self.region.as_pointer():
            return
        try:
            self.draw(context)
        except Exception:
            pass

    # -- helpers --------------------------------------------------------------
    def view_dir(self, coord):
        return view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, coord).normalized()

    def at_depth(self, coord, depth_point):
        return view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, coord, depth_point)

    def cast(self, context, coord):
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, coord)
        direction = self.view_dir(coord)
        depsgraph = context.evaluated_depsgraph_get()
        return mesh_utils.object_ray_cast(self.target, origin, direction, depsgraph)

    def to2d(self, world):
        return view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, world)

    def contact_label(self):
        if self.contacts_needed == 1:
            return ""
        return f" [contact {len(self.contacts) + 1}/{self.contacts_needed}]"

    def update_status(self, context):
        context.workspace.status_text_set(self.status_text() + "  |  RMB / Esc: cancel  |  MMB: orbit")
        try:
            self.area.header_text_set(f"EasySlice: {self.header_text()}{self.contact_label()}")
        except Exception:
            pass

    def contact_done(self, context, data):
        self.contacts.append(data)
        if len(self.contacts) >= self.contacts_needed:
            return self.finish(context)
        self.reset_stroke()
        self.update_status(context)
        return None

    def finish(self, context):
        self.end(context)
        settings = context.scene.esp
        try:
            if settings.mode == 'PLAN':
                rec = plan.add_record(context, self.target, self.kind, self.contacts)
                settings.last_message = f"'{rec.name}' added to the plan"
                self.report({'INFO'}, f"'{rec.name}' added to the plan. Select it in the list to edit its connector.")
            else:
                a, b, secs = quick_cut(context, self.target, self.contacts)
                settings.last_message = f"Cut done in {secs:.2f}s"
                self.report({'INFO'}, f"Cut completed in {secs:.2f}s: {a.name} / {b.name}. Ctrl+Z to undo.")
        except cutting.CutError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        if settings.chain_cuts:
            schedule_chain(self.bl_idname, self.window, self.area)
        return {'FINISHED'}

    # -- overridable ------------------------------------------------------------
    def on_press(self, context, c):
        return None

    def on_release(self, context, c):
        return None

    def on_move(self, context, c):
        return None

    def on_confirm(self, context):
        return None

    def draw(self, context):
        pass

    def status_text(self):
        return ""

    def header_text(self):
        return ""


# ----------------------------------------------------------------------------
class ESP_OT_cut_straight(CutToolBase, bpy.types.Operator):
    bl_idname = "esp.cut_straight"
    bl_label = "Plane Cut"
    bl_description = "Drag a line across the model: a flat cut perpendicular to the view goes through it"
    kind = 'STRAIGHT'

    def status_text(self):
        return "LMB drag (or click, click): draw the cut line"

    def header_text(self):
        return "Plane Cut - drag a line across the model"

    def on_press(self, context, c):
        if self.click_mode and self.start2d is not None:
            return self.make_contact(context, self.start2d, c)
        self.start2d = c
        self.drawing = True
        return None

    def on_release(self, context, c):
        if not self.drawing or self.start2d is None:
            return None
        self.drawing = False
        if dist2d(c, self.start2d) < 4.0:
            self.click_mode = True
            return None
        return self.make_contact(context, self.start2d, c)

    def make_contact(self, context, p0, p1):
        q0 = self.at_depth(p0, self.bcenter)
        q1 = self.at_depth(p1, self.bcenter)
        mid = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5)
        d = self.view_dir(mid)
        u = q1 - q0
        if u.length < 1e-9:
            self.reset_stroke()
            return None
        n = u.cross(d).normalized()
        if n.z < -1e-6 or (abs(n.z) <= 1e-6 and n.x < 0):
            n = -n
        c = self.bcenter - n * (self.bcenter - q0).dot(n)
        data = plan.ContactData('STRAIGHT')
        data.verts, data.faces = surfaces.plane_patch(c, n, u, self.diag * 1.3)
        data.view_dir = d
        hit, loc, _nor, _dist = self.cast(context, mid)
        if hit:
            data.hit = loc
            data.through = d
            data.anchor = loc
        else:
            data.center_hint = c
            data.anchor = c
        return self.contact_done(context, data)

    def draw(self, context):
        if self.start2d is None:
            return
        draw.lines_2d([self.start2d, self.mouse], draw.GREEN, 2.5)
        draw.points_2d([self.start2d, self.mouse], draw.WHITE, 7.0)


# ----------------------------------------------------------------------------
class ESP_OT_cut_curved(CutToolBase, bpy.types.Operator):
    bl_idname = "esp.cut_curved"
    bl_label = "Curve Cut"
    bl_description = "Draw a curved line over the model; the cut follows the line straight through the model"
    kind = 'CURVED'

    def status_text(self):
        return "LMB drag: draw the curve across the model (cross the whole silhouette)"

    def header_text(self):
        return "Curve Cut - draw a line over the model"

    def on_press(self, context, c):
        self.stroke = [c]
        self.drawing = True
        return None

    def on_move(self, context, c):
        if self.drawing and (not self.stroke or dist2d(c, self.stroke[-1]) >= 2.0):
            self.stroke.append(c)
        return None

    def on_release(self, context, c):
        if not self.drawing:
            return None
        self.drawing = False
        if len(self.stroke) < 2:
            self.reset_stroke()
            return None
        return self.make_contact(context, self.stroke)

    def make_contact(self, context, stroke):
        settings = context.scene.esp
        pts = []
        hits = []
        ref = self.bcenter
        for s in stroke:
            hit, loc, _n, _d = self.cast(context, s)
            if hit:
                pts.append(loc)
                hits.append((len(pts) - 1, loc))
                ref = loc
            else:
                pts.append(self.at_depth(s, ref))
        mid2d = stroke[len(stroke) // 2]
        d = self.view_dir(mid2d)
        pts = surfaces.dedupe_polyline(pts, self.diag * 0.002)
        if len(pts) < 2:
            self.reset_stroke()
            return None
        pts = surfaces.resample_polyline(pts, settings.control_points)
        pts = surfaces.smooth_polyline(pts, 0.15, iterations=1)
        avg = Vector((0.0, 0.0, 0.0))
        for i in range(len(pts) - 1):
            avg += (pts[i + 1] - pts[i]).cross(d)
        if avg.z < -1e-6 or (abs(avg.z) <= 1e-6 and avg.x < 0):
            pts.reverse()
        # depth range: cover the whole model along the view direction
        mn, mx = mesh_utils.object_world_bounds(self.target)
        mean = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
        ts = []
        for cx in (mn.x, mx.x):
            for cy in (mn.y, mx.y):
                for cz in (mn.z, mx.z):
                    ts.append((Vector((cx, cy, cz)) - mean).dot(d))
        margin = self.diag * 0.05
        data = plan.ContactData('CURVED')
        data.points = pts
        data.view_dir = d
        data.depth_range = (min(ts) - margin, max(ts) + margin)
        data.extend = self.diag * 0.5
        data.verts, data.faces = surfaces.ribbon_patch(pts, d, 0.0, data.extend, depth_range=data.depth_range)
        if hits:
            mid_i = len(stroke) // 2
            _idx, loc = min(hits, key=lambda h: abs(h[0] - mid_i))
            data.hit = loc
            data.through = d
            data.anchor = loc
        else:
            data.center_hint = self.at_depth(mid2d, self.bcenter)
            data.anchor = data.center_hint
        return self.contact_done(context, data)

    def draw(self, context):
        if len(self.stroke) >= 2:
            draw.lines_2d(self.stroke, draw.GREEN, 2.5)
        if self.stroke:
            draw.points_2d([self.stroke[0]], draw.WHITE, 7.0)


# ----------------------------------------------------------------------------
class ESP_OT_cut_freehand(CutToolBase, bpy.types.Operator):
    bl_idname = "esp.cut_freehand"
    bl_label = "Freehand Cut"
    bl_description = (
        "Draw a closed loop on the model surface (several strokes allowed, orbit with MMB); "
        "the loop is filled and used as the cut surface"
    )
    kind = 'FREEHAND'
    CLOSE_PX = 12.0

    def status_text(self):
        return "LMB draw on the surface | release to pause | return to the green start (or Enter) to close the loop"

    def header_text(self):
        n = len(self.loop)
        return f"Freehand Cut - draw a closed loop around the model ({n} samples)"

    def on_press(self, context, c):
        self.drawing = True
        return self.on_move(context, c)

    def on_move(self, context, c):
        if not self.drawing:
            return None
        hit, loc, nor, _d = self.cast(context, c)
        if not hit:
            return None
        if self.loop and (loc - self.loop[-1][0]).length < self.diag * 0.004:
            return None
        self.loop.append((loc, nor))
        self.loop2d.append(c)
        if len(self.loop) > 8:
            start2d = self.to2d(self.loop[0][0])
            if start2d is not None and dist2d(c, start2d) <= self.CLOSE_PX:
                self.drawing = False
                return self.close_loop(context)
        return None

    def on_release(self, context, c):
        self.drawing = False
        self.update_status(context)
        return None

    def on_confirm(self, context):
        if len(self.loop) >= 3:
            return self.close_loop(context)
        return None

    def close_loop(self, context):
        settings = context.scene.esp
        src = (
            settings.cuts[settings.active_cut]
            if (settings.mode == 'PLAN' and 0 <= settings.active_cut < len(settings.cuts))
            else settings
        )
        u = plan.mm(context)
        margin = max(0.6 * u, src.cut_gap_mm * u * 3.0)
        locs = [l for l, _n in self.loop]
        centroid = sum(locs, Vector((0.0, 0.0, 0.0))) / len(locs)
        pts = [l + n * margin for l, n in self.loop]
        pts = surfaces.dedupe_polyline(pts, self.diag * 0.002)
        if len(pts) < 3:
            self.report({'WARNING'}, "Loop too small")
            self.reset_stroke()
            return None
        pts = surfaces.smooth_polyline(pts, settings.freehand_smoothing, closed=True)
        pts = surfaces.resample_polyline(pts, settings.control_points, closed=True)
        n = surfaces.newell_normal(pts)
        if n.z < -1e-6 or (abs(n.z) <= 1e-6 and n.x < 0):
            pts.reverse()
        try:
            verts, faces = surfaces.loop_patch(pts)
        except ValueError as e:
            self.report({'WARNING'}, f"Could not fill the loop: {e}")
            self.reset_stroke()
            return None
        data = plan.ContactData('FREEHAND')
        data.points = pts
        data.margin = margin
        data.verts, data.faces = verts, faces
        data.center_hint = centroid
        data.anchor = locs[0]
        return self.contact_done(context, data)

    def draw(self, context):
        pts2d = []
        for loc, _n in self.loop:
            p = self.to2d(loc)
            if p is not None:
                pts2d.append(p)
        if len(pts2d) >= 2:
            draw.lines_2d(pts2d, draw.RED, 2.5)
            if self.drawing:
                draw.lines_2d([pts2d[-1], self.mouse], draw.DIM, 1.0)
        if pts2d:
            draw.points_2d([pts2d[0]], draw.GREEN, 10.0)
            draw.circle_2d(pts2d[0], self.CLOSE_PX, draw.GREEN)


CLASSES = (ESP_OT_cut_straight, ESP_OT_cut_curved, ESP_OT_cut_freehand)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
