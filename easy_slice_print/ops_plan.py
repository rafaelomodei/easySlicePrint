# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Plan mode operators: manage records, edit surfaces, build/approve."""

import time

import bpy
from bpy.props import IntProperty
from bpy_extras import view3d_utils
from mathutils import Vector

from . import draw, jobs, plan
from .core import cutting, mesh_utils
from .ops_tools import CURSOR_DRAW, NAV_EVENTS, dist2d, restore_cursor, set_cursor, window_region


def active_record(context):
    s = context.scene.esp
    if 0 <= s.active_cut < len(s.cuts):
        return s.cuts[s.active_cut]
    return None


class ESP_OT_new_cut(bpy.types.Operator):
    bl_idname = "esp.new_cut"
    bl_label = "New Cut"
    bl_description = "Start the last used cut tool"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and plan.resolve_target(context) is not None

    def invoke(self, context, event):
        tool = context.scene.esp.tool
        op = {
            'STRAIGHT': bpy.ops.esp.cut_straight,
            'CURVED': bpy.ops.esp.cut_curved,
            'FREEHAND': bpy.ops.esp.cut_freehand,
        }[tool]
        return op('INVOKE_DEFAULT')


class ESP_OT_delete_cut(bpy.types.Operator):
    bl_idname = "esp.delete_cut"
    bl_label = "Delete Cut"
    bl_description = "Remove this planned cut and its preview"
    bl_options = {'REGISTER', 'UNDO'}
    index: IntProperty(default=-1)

    def execute(self, context):
        s = context.scene.esp
        idx = self.index if self.index >= 0 else s.active_cut
        if not (0 <= idx < len(s.cuts)):
            return {'CANCELLED'}
        name = s.cuts[idx].name
        plan.remove_record(context, idx)
        self.report({'INFO'}, f"Removed '{name}'")
        return {'FINISHED'}


class ESP_OT_swap_pin_side(bpy.types.Operator):
    bl_idname = "esp.swap_pin_side"
    bl_label = "Swap Pin Side"
    bl_description = "Move the pin to the other part (the socket goes to this one)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return active_record(context) is not None

    def execute(self, context):
        rec = active_record(context)
        rec.pin_side = 'B' if rec.pin_side == 'A' else 'A'
        return {'FINISHED'}


class ESP_OT_reset_pin(bpy.types.Operator):
    bl_idname = "esp.reset_pin"
    bl_label = "Reset Pin Transform"
    bl_description = "Put the connector back at the automatic position, orientation and size"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return active_record(context) is not None

    def execute(self, context):
        rec = active_record(context)
        plan.refresh_record_frames(context, rec)
        plan.reset_pins(context, rec)
        return {'FINISHED'}


class ESP_OT_select_pin(bpy.types.Operator):
    bl_idname = "esp.select_pin"
    bl_label = "Select Connector"
    bl_description = "Select the connector preview so you can move (G), rotate (R) or scale (S) it in the viewport"
    bl_options = {'REGISTER', 'UNDO'}
    index: IntProperty(default=0)

    @classmethod
    def poll(cls, context):
        return active_record(context) is not None and context.mode == 'OBJECT'

    def execute(self, context):
        rec = active_record(context)
        name = rec.pin_a if self.index == 0 else rec.pin_b
        pin = bpy.data.objects.get(name)
        if pin is None:
            self.report({'WARNING'}, "This cut has no connector preview")
            return {'CANCELLED'}
        for o in context.view_layer.objects:
            o.select_set(False)
        pin.hide_viewport = False
        pin.select_set(True)
        context.view_layer.objects.active = pin
        self.report({'INFO'}, "Connector selected: G move, R rotate, S scale. Reset Pin puts it back.")
        return {'FINISHED'}


class ESP_OT_refresh_pins(bpy.types.Operator):
    bl_idname = "esp.refresh_pins"
    bl_label = "Refresh Connectors"
    bl_description = "Re-estimate connector position and size from the current cut surfaces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for rec in context.scene.esp.cuts:
            plan.refresh_record_frames(context, rec)
        return {'FINISHED'}


# ----------------------------------------------------------------------------
class ESP_OT_edit_surface(bpy.types.Operator):
    bl_idname = "esp.edit_surface"
    bl_label = "Edit Cut Surface"
    bl_description = (
        "Plane cut: selects the cut plane (G/R/S). Curve/Freehand: drag the control points; "
        "Ctrl+LMB add, X delete, G slide all, R reset, Ctrl+Z undo, Enter/Esc finish"
    )
    bl_options = {'REGISTER', 'UNDO'}
    HOVER_PX = 12.0

    @classmethod
    def poll(cls, context):
        return active_record(context) is not None and context.mode == 'OBJECT'

    def invoke(self, context, event):
        rec = active_record(context)
        self.rec = rec
        sobj = bpy.data.objects.get(rec.surface_a)
        if sobj is None:
            self.report({'ERROR'}, "Preview surface not found")
            return {'CANCELLED'}
        rec.show = True
        if rec.cut_type == 'STRAIGHT' or rec.two_contact:
            for o in context.view_layer.objects:
                o.select_set(False)
            sobj.select_set(True)
            context.view_layer.objects.active = sobj
            self.report({'INFO'}, "Cut surface selected: G move, R rotate, S scale. The connector follows.")
            return {'FINISHED'}
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Run this from the 3D Viewport")
            return {'CANCELLED'}
        self.area = context.area
        self.window = context.window
        self.region = window_region(self.area)
        self.rv3d = self.region.data
        self.sobj = sobj
        self.kind = sobj.get("esp_kind", 'CURVED')
        self.closed = self.kind == 'FREEHAND'
        self.target = bpy.data.objects.get(rec.target) or bpy.data.objects.get(context.scene.esp.base_object)
        self.mw = sobj.matrix_world.copy()
        self.inv = self.mw.inverted_safe()
        self.points = plan.surface_points(sobj)
        self.orig = [p.copy() for p in self.points]
        self.history = [[p.copy() for p in self.points]]
        self.redo = []
        self.hover = None
        self.drag = None
        self.slide = None
        self.mouse = (0, 0)
        self.changed = False
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self._draw_cb, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        set_cursor(self.window, CURSOR_DRAW)
        context.workspace.status_text_set(
            "Drag point: LMB | Add: Ctrl+LMB | Delete: X | Slide all: G | Reset: R | Undo: Ctrl+Z | Finish: Enter / Esc"
        )
        return {'RUNNING_MODAL'}

    # -- helpers ----------------------------------------------------------------
    def world_points(self):
        return [self.mw @ p for p in self.points]

    def to2d(self, w):
        return view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, w)

    def surface_pos(self, context, coord, fallback_world):
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, coord).normalized()
        if self.target is not None:
            state = plan.ensure_evaluable(self.target)
            try:
                depsgraph = context.evaluated_depsgraph_get()
                hit, loc, nor, _d = mesh_utils.object_ray_cast(self.target, origin, direction, depsgraph)
            finally:
                plan.restore_visibility(self.target, state)
            if hit:
                if self.closed:
                    return loc + nor * float(self.sobj.get("esp_margin", 0.0))
                return loc
        return view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, coord, fallback_world)

    def commit(self, context, draft=False):
        plan.set_surface_points(self.sobj, self.points)
        plan.rebuild_surface(self.sobj, draft, context=context, target=self.target)
        self.changed = True

    def push_history(self):
        self.history.append([p.copy() for p in self.points])
        self.redo = []

    def nearest_point(self, coord):
        best, best_d = None, self.HOVER_PX
        for i, w in enumerate(self.world_points()):
            p = self.to2d(w)
            if p is None:
                continue
            d = dist2d(p, coord)
            if d < best_d:
                best, best_d = i, d
        return best

    def nearest_segment(self, coord):
        pts = [self.to2d(w) for w in self.world_points()]
        best, best_d = None, 1e9
        n = len(pts)
        rng = range(n) if self.closed else range(n - 1)
        for i in rng:
            a, b = pts[i], pts[(i + 1) % n]
            if a is None or b is None:
                continue
            ab = (b[0] - a[0], b[1] - a[1])
            l2 = ab[0] ** 2 + ab[1] ** 2
            t = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((coord[0] - a[0]) * ab[0] + (coord[1] - a[1]) * ab[1]) / l2))
            proj = (a[0] + ab[0] * t, a[1] + ab[1] * t)
            d = dist2d(proj, coord)
            if d < best_d:
                best, best_d = i, d
        return best

    def end(self, context):
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        restore_cursor(getattr(self, "window", None))
        context.workspace.status_text_set(None)
        self.area.tag_redraw()

    # -- modal ------------------------------------------------------------------
    def modal(self, context, event):
        self.mouse = (event.mouse_x - self.region.x, event.mouse_y - self.region.y)
        if event.type in NAV_EVENTS:
            return {'PASS_THROUGH'}
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            if self.slide is not None:
                self.points = self.slide[1]
                self.slide = None
                self.commit(context)
                return {'RUNNING_MODAL'}
            self.points = self.orig
            self.commit(context)
            self.end(context)
            plan.refresh_record_frames(context, self.rec)
            return {'CANCELLED'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            if self.slide is not None:
                self.slide = None
                self.commit(context)
                self.push_history()
                return {'RUNNING_MODAL'}
            self.end(context)
            plan.refresh_record_frames(context, self.rec)
            self.report({'INFO'}, "Cut surface updated")
            return {'FINISHED'}
        if event.type == 'MOUSEMOVE':
            if self.drag is not None:
                w = self.surface_pos(context, self.mouse, self.mw @ self.points[self.drag])
                self.points[self.drag] = self.inv @ w
                self.commit(context, draft=True)
            elif self.slide is not None:
                start, base = self.slide
                ref = self.mw @ base[0]
                delta = view3d_utils.region_2d_to_location_3d(
                    self.region, self.rv3d, self.mouse, ref
                ) - view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, start, ref)
                self.points = [self.inv @ ((self.mw @ p) + delta) for p in base]
                self.commit(context, draft=True)
            else:
                self.hover = self.nearest_point(self.mouse)
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if self.slide is not None:
                    self.slide = None
                    self.commit(context)
                    self.push_history()
                elif event.ctrl:
                    seg = self.nearest_segment(self.mouse)
                    if seg is not None:
                        w = self.surface_pos(context, self.mouse, self.mw @ self.points[seg])
                        self.points.insert(seg + 1, self.inv @ w)
                        self.drag = seg + 1
                        self.commit(context)
                elif self.hover is not None:
                    self.drag = self.hover
            elif event.value == 'RELEASE' and self.drag is not None:
                self.drag = None
                self.commit(context)  # drag over: rebuild at full resolution
                self.push_history()
        elif event.type in {'X', 'DEL'} and event.value == 'PRESS':
            min_pts = 3 if self.closed else 2
            if self.hover is not None and len(self.points) > min_pts:
                self.points.pop(self.hover)
                self.hover = None
                self.commit(context)
                self.push_history()
        elif event.type == 'G' and event.value == 'PRESS':
            self.slide = (self.mouse, [p.copy() for p in self.points])
        elif event.type == 'R' and event.value == 'PRESS':
            self.points = [p.copy() for p in self.orig]
            self.commit(context)
            self.push_history()
        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            if event.shift:
                if self.redo:
                    self.history.append(self.redo.pop())
                    self.points = [p.copy() for p in self.history[-1]]
                    self.commit(context)
            elif len(self.history) > 1:
                self.redo.append(self.history.pop())
                self.points = [p.copy() for p in self.history[-1]]
                self.commit(context)
        self.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _draw_cb(self, context):
        if bpy.context.region is None or bpy.context.region.as_pointer() != self.region.as_pointer():
            return
        pts = [self.to2d(w) for w in self.world_points()]
        pts2 = [p for p in pts if p is not None]
        if len(pts2) >= 2:
            draw.lines_2d(pts2, draw.GREEN, 2.0, closed=self.closed)
        draw.points_2d(pts2, draw.ORANGE, 8.0)
        idx = self.drag if self.drag is not None else self.hover
        if idx is not None and idx < len(pts) and pts[idx] is not None:
            draw.points_2d([pts[idx]], (1.0, 1.0, 0.2, 1.0), 12.0)


# ----------------------------------------------------------------------------
def _remove_built_parts(context):
    s = context.scene.esp
    col = bpy.data.collections.get(s.built_collection) if s.built_collection else None
    if col is not None:
        for obj in list(col.objects):
            mesh_utils.remove_object(obj)
        bpy.data.collections.remove(col)
    s.built_collection = ""
    s.built = False
    s.exploded = False
    for rec in s.cuts:
        rec.built = False


def _labelled(generator, prefix):
    """Forward a step generator, tagging each label with the cut it belongs to."""
    try:
        while True:
            try:
                label = next(generator)
            except StopIteration as stop:
                return stop.value
            yield f"{prefix} - {label}" if label else prefix
    finally:
        generator.close()


def _pick_target(parts, anchor):
    best, best_d = None, 1e30
    for p in parts:
        ok, _loc, _nor, d = mesh_utils.object_closest_point(p, anchor)
        if ok and d < best_d:
            best, best_d = p, d
    return best or parts[0]


class ESP_OT_build(jobs.JobMixin, bpy.types.Operator):
    bl_idname = "esp.build"
    bl_label = "Build Plan"
    bl_description = "Apply every ready cut to the model and create the final parts (the plan stays editable)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.esp
        return context.mode == 'OBJECT' and any(r.enabled for r in s.cuts)

    def build_steps(self, context):
        """Run the whole plan, yielding a label before each heavy step.

        Every cut is several seconds of boolean work; a three cut plan easily
        passes ten. Yielding lets the modal driver return to Blender's event
        loop so the window never looks frozen to the desktop.
        """
        s = context.scene.esp
        scene = context.scene
        t0 = time.time()
        base = bpy.data.objects.get(s.base_object)
        if base is None:
            raise cutting.CutError("The plan's source object no longer exists. Clear the plan.")
        if s.built:
            _remove_built_parts(context)
        # after an approve the cuts can sit on different parts: each one is a source
        sources = plan.plan_sources(context)
        for src in sources:
            plan.restore_from_backup(scene, src)
        plan.set_plan_hidden(context, False)
        col = plan.built_collection(scene, base.name)
        parts = list(sources)
        made = []
        counter = 0
        done = 0
        skipped = 0
        enabled = [r for r in s.cuts if r.enabled]
        for i, rec in enumerate(enabled, start=1):
            prefix = f"cut {i}/{len(enabled)}"
            yield f"{prefix} - preparing"
            plan.refresh_record_frames(context, rec)
            try:
                spec = plan.record_spec(context, rec, s)
                target = _pick_target(parts, Vector(rec.anchor))
                stem = target.get("esp_stem", target.name)
                counter += 2
                names = (f"{stem}_PART_{counter - 1:03d}", f"{stem}_PART_{counter:03d}")
                state = plan.ensure_evaluable(target)
                try:
                    a, b, _secs = yield from _labelled(
                        cutting.perform_cut_steps(context, target, spec, names, col), prefix
                    )
                finally:
                    plan.restore_visibility(target, state)
            except cutting.CutError as e:
                if s.skip_failed:
                    skipped += 1
                    self.report({'WARNING'}, f"'{rec.name}' skipped: {e}")
                    continue
                for o in made:
                    mesh_utils.remove_object(o)
                bpy.data.collections.remove(col)
                raise cutting.CutError(f"'{rec.name}' failed: {e}") from e
            parts.remove(target)
            if target not in sources:
                made.remove(target)
                mesh_utils.remove_object(target)
            for o in (a, b):
                o["esp_stem"] = stem
            parts.extend((a, b))
            made.extend((a, b))
            rec.built = True
            done += 1
        if not made:
            bpy.data.collections.remove(col)
            raise cutting.CutError("Nothing was cut")
        yield "finishing"
        numbers = {}
        for o in sorted(made, key=lambda o: o.name):
            stem = o.get("esp_stem", base.name)
            n = numbers[stem] = numbers.get(stem, 0) + 1
            o.name = f"{stem}_PART_{n:03d}"
            o.data.name = o.name
            o["esp_base"] = stem
            if "esp_stem" in o:
                del o["esp_stem"]
        for src in sources:
            if src not in parts:  # it was cut: the model itself goes out of the way
                plan.move_to_backup(scene, src)
        plan.set_plan_hidden(context, True)
        s.built = True
        s.built_collection = col.name
        s.exploded = False
        for o in context.view_layer.objects:
            o.select_set(False)
        for o in made:
            o.select_set(True)
        context.view_layer.objects.active = made[0]
        secs = time.time() - t0
        msg = f"Built {len(made)} part(s) from {done} cut(s) in {secs:.2f}s"
        if skipped:
            msg += f" ({skipped} skipped)"
        return msg

    # -- modal driver -------------------------------------------------------
    def invoke(self, context, event):
        if context.window is None:
            return self.execute(context)
        return self.job_start(context, self.build_steps(context), "Build", add_handler=True)

    def modal(self, context, event):
        state, payload = self.job_step(context, event)
        if state == jobs.RUNNING:
            return {'RUNNING_MODAL'}
        return self.job_done(context, state, payload)

    def cancel(self, context):
        """Blender aborted the modal: stop the timer and clear the status line."""
        self.job_stop(context)

    def job_done(self, context, state, payload):
        s = context.scene.esp
        if state == jobs.CANCELLED:
            s.last_message = "Build cancelled"
            self.report({'WARNING'}, "Build cancelled - the parts made so far were kept")
            return {'CANCELLED'}
        if state == jobs.ERROR:
            self.report({'ERROR'}, str(payload))
            return {'CANCELLED'}
        s.last_message = payload
        self.report({'INFO'}, payload + ". Plan preserved; use Back to Plan to edit.")
        return {'FINISHED'}

    def execute(self, context):
        """Blocking build, for scripts and background runs."""
        try:
            msg = cutting.drain(self.build_steps(context))
        except cutting.CutError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        context.scene.esp.last_message = msg
        self.report({'INFO'}, msg + ". Plan preserved; use Back to Plan to edit.")
        return {'FINISHED'}


class ESP_OT_return_to_plan(bpy.types.Operator):
    bl_idname = "esp.return_to_plan"
    bl_label = "Back to Plan"
    bl_description = "Remove the built parts, restore the source model and show the planned cuts again"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.esp.built

    def execute(self, context):
        s = context.scene.esp
        _remove_built_parts(context)
        sources = plan.plan_sources(context)
        for src in sources:
            plan.restore_from_backup(context.scene, src)
        if sources:
            context.view_layer.objects.active = sources[0]
        plan.set_plan_hidden(context, False)
        s.last_message = "Plan restored"
        self.report({'INFO'}, "Plan restored: cuts are editable again")
        return {'FINISHED'}


class ESP_OT_approve(bpy.types.Operator):
    bl_idname = "esp.approve"
    bl_label = "Approve"
    bl_description = (
        "Keep the built parts as final and clear the plan (the source stays in ESP_Backup when Keep Original is on)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.esp.built

    def execute(self, context):
        s = context.scene.esp
        # only what this build actually consumed - a source it cut is in the backup
        consumed = [o for o in plan.plan_sources(context) if o.get("esp_backup_home") is not None]
        plan.remove_all_records(context)
        if not s.keep_original:
            for o in consumed:
                mesh_utils.remove_object(o)
        s.built = False
        s.base_object = ""
        s.built_collection = ""
        s.last_message = "Parts approved"
        self.report({'INFO'}, "Parts approved. Use Export to write the files.")
        return {'FINISHED'}


class ESP_OT_clear_plan(bpy.types.Operator):
    bl_idname = "esp.clear_plan"
    bl_label = "Clear Plan"
    bl_description = "Delete every planned cut and preview (built parts are kept)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.esp.cuts) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s = context.scene.esp
        stashed = [o for o in plan.plan_sources(context) if o.get("esp_backup_home") is not None]
        plan.remove_all_records(context)
        if not s.built:
            for o in stashed:
                plan.restore_from_backup(context.scene, o)
            s.base_object = ""
        s.built = False
        s.built_collection = ""
        s.last_message = "Plan cleared"
        return {'FINISHED'}


CLASSES = (
    ESP_OT_new_cut,
    ESP_OT_delete_cut,
    ESP_OT_swap_pin_side,
    ESP_OT_reset_pin,
    ESP_OT_select_pin,
    ESP_OT_refresh_pins,
    ESP_OT_edit_surface,
    ESP_OT_build,
    ESP_OT_return_to_plan,
    ESP_OT_approve,
    ESP_OT_clear_plan,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
