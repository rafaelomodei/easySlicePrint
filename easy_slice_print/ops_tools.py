# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Interactive cut tools (modal operators): plane, curve and freehand cuts."""

import math

import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from . import draw, jobs, plan
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


# Blender has no pencil cursor of its own: PAINT_BRUSH is the one grease pencil and the
# paint modes use, and it reads as a pencil over the model. KNIFE is the real blade.
CURSOR_DRAW = 'PAINT_BRUSH'
CURSOR_CUT = 'KNIFE'


def set_cursor(window, cursor):
    """Swap the pointer for the tool's own cursor; an unknown name falls back to a crosshair."""
    if window is None:
        return
    try:
        window.cursor_modal_set(cursor)
    except (TypeError, ValueError):
        try:
            window.cursor_modal_set('CROSSHAIR')
        except Exception:
            pass


def restore_cursor(window):
    if window is None:
        return
    try:
        window.cursor_modal_restore()
    except Exception:
        pass


def window_region(area):
    for r in area.regions:
        if r.type == 'WINDOW':
            return r
    return None


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def sample_segment(p0, p1, count):
    """`count` evenly spaced 2D points from p0 to p1, both ends included."""
    return [
        (p0[0] + (p1[0] - p0[0]) * i / (count - 1), p0[1] + (p1[1] - p0[1]) * i / (count - 1)) for i in range(count)
    ]


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


def quick_cut_steps(context, target, contacts):
    """Generator form of `quick_cut` for the modal job driver (see `jobs.py`)."""
    settings = context.scene.esp
    scene = context.scene
    spec = plan.quick_spec(context, target, contacts)
    base_name = target.get("esp_base", target.name) if target.get("esp_part") else target.name
    col = plan.built_collection(scene, base_name)
    state = plan.ensure_evaluable(target)
    try:
        a, b, secs = yield from cutting.perform_cut_steps(context, target, spec, ("_esp_new_a", "_esp_new_b"), col)
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


def quick_cut(context, target, contacts):
    """Blocking Quick mode cut. The UI goes through `quick_cut_steps` instead."""
    return cutting.drain(quick_cut_steps(context, target, contacts))


class CutToolBase(jobs.JobMixin):
    bl_options = {'REGISTER', 'UNDO'}
    kind = 'STRAIGHT'
    cursor = CURSOR_CUT

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
        set_cursor(self.window, self.cursor)
        self.update_status(context)
        return {'RUNNING_MODAL'}

    def reset_stroke(self):
        self.stroke = []
        self.drawing = False
        self.start2d = None
        self.click_mode = False
        self.loop = []
        self.loop2d = []
        self.view_at_press = None

    def end(self, context):
        if getattr(self, "_handle", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        restore_cursor(getattr(self, "window", None))
        context.workspace.status_text_set(None)
        try:
            self.area.header_text_set(None)
        except Exception:
            pass
        self.area.tag_redraw()

    def coord(self, event):
        return (event.mouse_x - self.region.x, event.mouse_y - self.region.y)

    def nav_drag(self, context, event):
        """With 'Emulate 3 Button Mouse' on, Alt+LMB is orbit - give it to the view."""
        return event.alt and context.preferences.inputs.use_mouse_emulate_3_button

    def view_key(self):
        """Fingerprint of the current view, to detect an orbit in the middle of a stroke."""
        return tuple(round(v, 5) for row in self.rv3d.view_matrix for v in row)

    def view_moved(self):
        return self.view_at_press is not None and self.view_key() != self.view_at_press

    def modal(self, context, event):
        if self.job_running():
            state, payload = self.job_step(context, event)
            if state == jobs.RUNNING:
                return {'RUNNING_MODAL'}
            return self.job_done(context, state, payload)
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
            if self.nav_drag(context, event):
                return {'PASS_THROUGH'}
            if event.value == 'PRESS':
                result = self.on_press(context, self.mouse)
            elif event.value == 'RELEASE':
                result = self.on_release(context, self.mouse)
        elif event.type == 'MOUSEMOVE':
            result = self.on_move(context, self.mouse)
        elif event.value == 'PRESS':
            result = self.on_key(context, event)
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

    # -- patch sizing ---------------------------------------------------------
    def surface_margin(self, context, span):
        """How far the patch may reach past the drawn region (a fraction of it)."""
        return max(span * context.scene.esp.surface_margin, self.diag * 0.002)

    def model_span(self, context, samples2d, ref, axis):
        """Extent of the model along `axis`, measured under the drawn stroke.

        Every crossing of the model is collected along the view ray at each sample,
        so the cut surface only spans the depth the model actually occupies where it
        was drawn - not the whole bounding box. -> (min, max) or None if nothing hit.
        """
        depsgraph = context.evaluated_depsgraph_get()
        eps = self.diag * 1e-4
        lo = hi = None
        for c in samples2d:
            origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, c)
            d = self.view_dir(c)
            for dist in mesh_utils.object_ray_hits(self.target, origin, d, eps, depsgraph, max_dist=self.diag * 4.0):
                t = (origin + d * dist - ref).dot(axis)
                lo = t if lo is None else min(lo, t)
                hi = t if hi is None else max(hi, t)
        return None if lo is None else (lo, hi)

    def bbox_span(self, ref, axis):
        """Fallback for a stroke drawn off the model: the whole bounding box."""
        mn, mx = mesh_utils.object_world_bounds(self.target)
        ts = [
            (Vector((cx, cy, cz)) - ref).dot(axis) for cx in (mn.x, mx.x) for cy in (mn.y, mx.y) for cz in (mn.z, mx.z)
        ]
        return min(ts), max(ts)

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
        if settings.mode == 'PLAN':
            try:
                rec = plan.add_record(context, self.target, self.kind, self.contacts)
            except cutting.CutError as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}
            settings.last_message = f"'{rec.name}' added to the plan"
            self.report({'INFO'}, f"'{rec.name}' added to the plan. Select it in the list to edit its connector.")
            return self.chain_or_finish(context)
        # Quick mode: the booleans take seconds, so run them a step per timer tick
        # and stay modal. Blocking here is what makes the desktop call Blender dead.
        return self.job_start(context, quick_cut_steps(context, self.target, self.contacts), "Cut")

    def chain_or_finish(self, context):
        if context.scene.esp.chain_cuts:
            schedule_chain(self.bl_idname, self.window, self.area)
        return {'FINISHED'}

    def cancel(self, context):
        """Blender aborted the modal (file load, quit): drop the timer and the overlay."""
        self.job_stop(context)
        self.end(context)

    def job_done(self, context, state, payload):
        settings = context.scene.esp
        if state == jobs.CANCELLED:
            settings.last_message = "Cut cancelled"
            self.report({'WARNING'}, "Cut cancelled")
            return {'CANCELLED'}
        if state == jobs.ERROR:
            self.report({'ERROR'}, str(payload))
            return {'CANCELLED'}
        a, b, secs = payload
        settings.last_message = f"Cut done in {secs:.2f}s"
        self.report({'INFO'}, f"Cut completed in {secs:.2f}s: {a.name} / {b.name}. Ctrl+Z to undo.")
        return self.chain_or_finish(context)

    # -- overridable ------------------------------------------------------------
    def on_press(self, context, c):
        return None

    def on_release(self, context, c):
        return None

    def on_move(self, context, c):
        return None

    def on_confirm(self, context):
        return None

    def on_key(self, context, event):
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
        self.view_at_press = self.view_key()
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
        if self.view_moved():
            self.reset_stroke()
            self.report({'WARNING'}, "View orbited mid-stroke - draw the plane cut from a single view")
            return None
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
        c = (q0 + q1) * 0.5
        data = plan.ContactData('STRAIGHT')
        data.view_dir = d
        data.plane_co = c
        data.plane_no = n
        hit, loc, _nor, _dist = self.cast(context, mid)
        if hit:
            data.hit = loc
            data.through = d
            data.anchor = loc
        else:
            data.center_hint = c
            data.anchor = c
        # the cut surface is the model's own cross section on this plane - the area the
        # print is really cut through - taken over every region the line ran across.
        # The line picks the plane and says which regions to cut; it does not decide
        # how big the surface is. Drag across one leg and the other is left alone; drag
        # across the whole figure and the sword and the wings come with it, which is
        # what stops a cut from removing material without separating anything.
        half = u.length * 0.5
        span = (u.normalized(), -half, half)
        patch = plan.straight_section(context, self.target, c, n, span, loc if hit else c)
        if patch is not None:
            plan.fill_straight_contact(data, patch, span)
        else:
            # nothing to section (open or non manifold mesh): fall back to the old
            # rectangle around the stroke rather than leaving the user without a cut
            margin = self.surface_margin(context, u.length)
            depth_axis = n.cross(u.normalized()).normalized()
            depth = self.model_span(context, sample_segment(p0, p1, 17), c, depth_axis) or self.bbox_span(c, depth_axis)
            data.verts, data.faces = surfaces.rect_patch(c, n, u, half + margin, (depth[0] - margin, depth[1] + margin))
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
    cursor = CURSOR_DRAW

    def status_text(self):
        return "LMB drag: draw the curve across the model (cross the whole silhouette)"

    def header_text(self):
        return "Curve Cut - draw a line over the model"

    def on_press(self, context, c):
        self.stroke = [c]
        self.drawing = True
        self.view_at_press = self.view_key()
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
        if self.view_moved():
            self.reset_stroke()
            self.report({'WARNING'}, "View orbited mid-stroke - draw the curve from a single view")
            return None
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
        pts = surfaces.smooth_polyline(pts, settings.stroke_smoothing)
        avg = Vector((0.0, 0.0, 0.0))
        for i in range(len(pts) - 1):
            avg += (pts[i + 1] - pts[i]).cross(d)
        if avg.z < -1e-6 or (abs(avg.z) <= 1e-6 and avg.x < 0):
            pts.reverse()
        margin = self.surface_margin(context, surfaces.polyline_length(pts))
        data = plan.ContactData('CURVED')
        data.points = pts
        data.view_dir = d
        data.extend = margin
        data.detail = settings.surface_detail
        # the surface follows the model: every column of the ribbon runs exactly as deep
        # as the material under it, and only over the run of material the stroke is
        # standing on - a curve across the near leg no longer reaches through the far
        # one. The boolean gets the same ribbon at one depth, reaching past the model.
        built = plan.ribbon_surfaces(context, self.target, pts, d, margin, data.detail)
        if built is not None:
            preview, cutter, band = built
            data.verts, data.faces = preview
            data.cutter = cutter
            data.depth_range = band
            data.is_cut_face = True
        else:
            # nothing under the stroke to measure: one depth for the whole ribbon
            mean = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
            step = max(1, len(stroke) // 24)
            span = self.model_span(context, stroke[::step], mean, d) or self.bbox_span(mean, d)
            data.depth_range = (span[0] - margin, span[1] + margin)
            data.verts, data.faces = surfaces.ribbon_patch(
                pts, d, 0.0, data.extend, depth_range=data.depth_range, detail=data.detail
            )
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
        "Draw a closed loop on the model surface. Release the button, orbit with MMB to reach "
        "the far side, then keep drawing: the loop is filled and used as the cut surface"
    )
    kind = 'FREEHAND'
    cursor = CURSOR_DRAW
    CLOSE_PX = 12.0
    MIN_STROKE = 3  # samples the current stroke must have before it may snap the loop closed

    def reset_stroke(self):
        CutToolBase.reset_stroke(self)
        self.breaks = set()  # loop indices where a new stroke (usually a new view) starts
        self.stroke_start = 0

    def status_text(self):
        return (
            "LMB draw on the surface | release + MMB orbit to reach the far side, then draw again | "
            "green start / Enter / C: close | Ctrl+Z: undo stroke"
        )

    def header_text(self):
        strokes = len(self.breaks) + (1 if self.loop else 0)
        return f"Freehand Cut - loop around the model ({len(self.loop)} samples, {strokes} strokes)"

    # -- view helpers ---------------------------------------------------------
    def eye_dir(self):
        """Approximate view direction, cheap enough to call for every drawn point."""
        return self.rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))

    def facing_camera(self, nor, tol=0.2):
        """Front facing, with slack so a start point on the silhouette still counts."""
        return nor.dot(self.eye_dir()) < tol

    def start_visible(self, context):
        """True when the loop start is really the surface under that screen position.

        After orbiting to the far side the start point still projects somewhere over
        the model, so a plain screen-distance test would snap the loop closed against
        a point the user cannot even see.
        """
        loc, nor = self.loop[0]
        p = self.to2d(loc)
        if p is None or not self.facing_camera(nor):
            return False
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, p)
        depth = (loc - origin).length
        hit, _loc, _n, dist = self.cast(context, p)
        return (not hit) or dist >= depth - self.diag * 0.02

    # -- input ----------------------------------------------------------------
    def on_press(self, context, c):
        self.drawing = True
        self.stroke_start = len(self.loop)
        if self.loop:
            # the segment joining the previous stroke to this one bridges two views
            self.breaks.add(self.stroke_start)
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
        if len(self.loop) > 8 and len(self.loop) - self.stroke_start > self.MIN_STROKE:
            start2d = self.to2d(self.loop[0][0])
            if start2d is not None and dist2d(c, start2d) <= self.CLOSE_PX and self.start_visible(context):
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
        self.report({'WARNING'}, "Draw at least a few points before closing the loop")
        return None

    def on_key(self, context, event):
        if event.type == 'C':
            return self.on_confirm(context)
        if event.type == 'BACK_SPACE' or (event.type == 'Z' and event.ctrl):
            self.undo_stroke(context)
        return None

    def undo_stroke(self, context):
        """Drop the last stroke - a stroke drawn from a bad angle is easy to redo."""
        if not self.loop:
            return
        starts = [b for b in self.breaks if 0 < b < len(self.loop)]
        cut = max(starts) if starts else 0
        del self.loop[cut:]
        del self.loop2d[cut:]
        self.breaks = {b for b in self.breaks if b < cut}
        self.drawing = False
        self.stroke_start = len(self.loop)
        self.update_status(context)

    # -- result ---------------------------------------------------------------
    def close_loop(self, context):
        settings = context.scene.esp
        src = (
            settings.cuts[settings.active_cut]
            if (settings.mode == 'PLAN' and 0 <= settings.active_cut < len(settings.cuts))
            else settings
        )
        locs = [l for l, _n in self.loop]
        centroid = sum(locs, Vector((0.0, 0.0, 0.0))) / len(locs)
        margin = plan.loop_margin(context, src, locs, self.diag)
        pts = [l + n * margin for l, n in self.loop]
        pts = surfaces.dedupe_polyline(pts, self.diag * 0.002)
        if len(pts) < 3:
            self.report({'WARNING'}, "Loop too small")
            self.reset_stroke()
            return None
        # No resample to a fixed count and no smoothing by default. A freehand loop is
        # the tool for tracing a detail - a groove, an ear, the line where two shapes
        # meet - so its control points are the points that were drawn: 50 samples stay
        # 50, 300 stay 300, and the cut face runs through them. Control Points sizes a
        # Curve cut; forcing a loop down to 20 of them moved the rim by millimetres and
        # rounded off the very detail the loop was drawn to catch.
        pts = surfaces.smooth_polyline(pts, settings.loop_smoothing, closed=True)
        n = surfaces.newell_normal(pts)
        if n.z < -1e-6 or (abs(n.z) <= 1e-6 and n.x < 0):
            pts.reverse()
        # the spline between the points can still cut a corner back into the material;
        # the membrane is built on a rim measured against the model after it
        pts = plan.clear_of_model(context, self.target, pts, margin)
        try:
            verts, faces = plan.loop_surface(context, self.target, pts, settings.surface_detail, margin)
        except ValueError as e:
            self.report({'WARNING'}, f"Could not fill the loop: {e}")
            self.reset_stroke()
            return None
        data = plan.ContactData('FREEHAND')
        data.points = pts
        data.margin = margin
        data.detail = settings.surface_detail
        data.verts, data.faces = verts, faces
        # the loop was drawn on the model and pushed a hair outside it, so the membrane
        # it spans is the printed cut face: its own outline is where the material ends,
        # which is exactly what the connector needs to be measured against
        data.is_cut_face = True
        data.center_hint = centroid
        data.anchor = locs[0]
        return self.contact_done(context, data)

    # -- overlay ---------------------------------------------------------------
    def draw(self, context):
        eye = self.eye_dir()
        pts2d = [(self.to2d(loc), nor.dot(eye) > 0.0) for loc, nor in self.loop]
        run = []
        style = None
        for i in range(1, len(pts2d)):
            (a, a_back), (b, b_back) = pts2d[i - 1], pts2d[i]
            if a is None or b is None:
                if len(run) >= 2:
                    draw.lines_2d(run, style[0], style[1])
                run, style = [], None
                continue
            if i in self.breaks:
                s = (draw.DIM, 1.0)  # bridge between two strokes / two viewpoints
            elif a_back or b_back:
                s = (draw.RED_BACK, 1.5)  # running behind the model
            else:
                s = (draw.RED, 2.5)
            if s != style:
                if len(run) >= 2:
                    draw.lines_2d(run, style[0], style[1])
                run, style = [a], s
            run.append(b)
        if len(run) >= 2:
            draw.lines_2d(run, style[0], style[1])
        if not self.loop:
            return
        last2d = pts2d[-1][0]
        if last2d is not None:
            if self.drawing:
                draw.lines_2d([last2d, self.mouse], draw.DIM, 1.0)
            else:
                draw.points_2d([last2d], draw.WHITE, 7.0)  # where the next stroke picks up
        start2d = pts2d[0][0]
        if start2d is not None:
            if len(pts2d) >= 3 and not self.drawing and last2d is not None:
                draw.lines_2d([last2d, start2d], draw.DIM, 1.0)  # how the loop would close now
            color = draw.GREEN if self.facing_camera(self.loop[0][1]) else draw.DIM
            draw.points_2d([start2d], color, 10.0)
            draw.circle_2d(start2d, self.CLOSE_PX, color)


CLASSES = (ESP_OT_cut_straight, ESP_OT_cut_curved, ESP_OT_cut_freehand)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
