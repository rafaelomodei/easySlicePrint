# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Sidebar panels (3D Viewport > N panel > EasySlice tab)."""

import bpy

from . import plan
from .ops_plan import active_record

VERSION = "0.1.0"
CATEGORY = "EasySlice"
TYPE_ICON = {'STRAIGHT': 'MESH_PLANE', 'CURVED': 'CURVE_BEZCURVE', 'FREEHAND': 'GREASEPENCIL'}
TYPE_LABEL = {'STRAIGHT': "Plane", 'CURVED': "Curve", 'FREEHAND': "Freehand"}


class ESP_UL_cuts(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text="", icon=TYPE_ICON.get(item.cut_type, 'DOT'))
        row.prop(item, "name", text="", emboss=False)
        if item.two_contact:
            row.label(text="", icon='MOD_MIRROR')
        if item.built:
            row.label(text="", icon='CHECKMARK')
        row.prop(item, "enabled", text="")
        row.prop(item, "show", text="", icon='HIDE_OFF' if item.show else 'HIDE_ON', emboss=False)
        op = row.operator("esp.delete_cut", text="", icon='X', emboss=False)
        op.index = index


class ESPPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY


class ESP_PT_main(ESPPanel, bpy.types.Panel):
    bl_label = "EasySlice Print"
    bl_idname = "ESP_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        row = layout.row(align=True)
        row.label(text=f"EasySlice Print {VERSION}", icon='MOD_BOOLEAN')
        row.operator("esp.check_mesh", text="", icon='CHECKMARK')
        row.operator("esp.open_docs", text="", icon='QUESTION')
        col = layout.column(align=True)
        col.label(text="Mode")
        col.row(align=True).prop(s, "mode", expand=True)
        if s.mode == 'QUICK':
            col.label(text="Immediate final cut", icon='TIME')
        else:
            col.label(text="Non-destructive plan history", icon='RECOVER_LAST')
        target = plan.resolve_target(context)
        if target is None:
            layout.label(text="Select a mesh object to cut", icon='ERROR')
        else:
            layout.label(text=f"Target: {target.name}", icon='OBJECT_DATA')
        if s.last_message:
            layout.label(text=s.last_message, icon='INFO')


class ESP_PT_tools(ESPPanel, bpy.types.Panel):
    bl_label = "Cut Tools"
    bl_parent_id = "ESP_PT_main"

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("esp.cut_straight", text="Plane", icon='MESH_PLANE', depress=s.tool == 'STRAIGHT')
        row.operator("esp.cut_curved", text="Curve", icon='CURVE_BEZCURVE', depress=s.tool == 'CURVED')
        row.operator("esp.cut_freehand", text="Freehand", icon='GREASEPENCIL', depress=s.tool == 'FREEHAND')
        if s.tool == 'FREEHAND':
            layout.label(text="Orbit (MMB) between strokes to reach the far side", icon='INFO')
        col = layout.column(align=True)
        col.prop(s, "surface_margin", slider=True)
        if s.mode == 'PLAN':
            col.prop(s, "surface_origin", text="Origin")
        col.prop(s, "freehand_smoothing", slider=True)
        col.prop(s, "control_points")
        col.prop(s, "surface_detail")
        layout.prop(s, "two_contact", toggle=True, icon='MOD_MIRROR')
        if s.two_contact:
            layout.label(text="Draw contact 1, then contact 2 with any tool", icon='INFO')
        layout.prop(s, "chain_cuts")


def connector_source(context):
    s = context.scene.esp
    if s.mode == 'PLAN':
        rec = active_record(context)
        if rec is not None:
            return rec, True
    return s, False


class ESP_PT_connector(ESPPanel, bpy.types.Panel):
    bl_label = "Connector"
    bl_parent_id = "ESP_PT_main"

    def draw(self, context):
        layout = self.layout
        src, is_record = connector_source(context)
        if is_record:
            layout.label(text=f"Selected cut: {src.name}", icon='RESTRICT_SELECT_OFF')
        else:
            layout.label(text="Settings for the next cut", icon='SETTINGS')
        layout.prop(src, "add_pin")
        col = layout.column()
        col.active = src.add_pin
        row = col.row(align=True)
        row.prop(src, "shape", text="Shape")
        row.operator("esp.connector_library", text="", icon='ASSET_MANAGER')
        col.row(align=True).prop(src, "size_preset", expand=True)
        row = col.row(align=True)
        row.enabled = src.size_preset == 'CUSTOM'
        row.prop(src, "pin_width_mm")
        row.prop(src, "pin_height_mm")
        row = col.row(align=True)
        row.prop(src, "pin_side", expand=True)
        if is_record:
            row.operator("esp.swap_pin_side", text="", icon='ARROW_LEFTRIGHT')
        layout.prop(src, "cut_gap_mm")


class ESP_PT_fit(ESPPanel, bpy.types.Panel):
    bl_label = "Fit & Clearance"
    bl_parent_id = "ESP_PT_connector"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        src, _is_record = connector_source(context)
        layout.active = src.add_pin
        layout.label(text="How the printed parts go together")
        layout.row(align=True).prop(src, "fit_preset", expand=True)
        row = layout.row()
        row.enabled = src.fit_preset == 'CUSTOM'
        row.prop(src, "clearance_mm")
        widened = src.clearance_mm * 2.0
        layout.label(text=f"Socket comes out {widened:.2f} mm wider than the pin", icon='DRIVER_DISTANCE')
        if src.fit_preset != 'CUSTOM':
            layout.label(
                text=f"From Printer Clearance {plan.printer_clearance_mm(context):.2f} mm (Preferences)",
                icon='TOOL_SETTINGS',
            )
        layout.separator()
        layout.prop(src, "asymmetric")
        row = layout.row()
        row.active = src.asymmetric
        row.prop(src, "tip_extra_mm")


class ESP_PT_options(ESPPanel, bpy.types.Panel):
    bl_label = "Options"
    bl_parent_id = "ESP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        layout.prop(s, "keep_original")
        row = layout.row()
        row.active = s.mode == 'PLAN'
        row.prop(s, "skip_failed")


class ESP_PT_remesh(ESPPanel, bpy.types.Panel):
    bl_label = "Remesh (Plan Mode only)"
    bl_parent_id = "ESP_PT_options"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.prop(context.scene.esp, "remesh_enable", text="")

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        layout.active = s.remesh_enable and s.mode == 'PLAN'
        layout.prop(s, "remesh_voxel_mm")
        layout.prop(s, "remesh_adaptivity", slider=True)
        layout.prop(s, "remesh_smooth")


class ESP_PT_plan(ESPPanel, bpy.types.Panel):
    bl_label = "Planned Cuts"
    bl_parent_id = "ESP_PT_main"

    @classmethod
    def poll(cls, context):
        return context.scene.esp.mode == 'PLAN'

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        row = layout.row()
        row.template_list("ESP_UL_cuts", "", s, "cuts", s, "active_cut", rows=4)
        col = row.column(align=True)
        col.operator("esp.new_cut", text="", icon='ADD')
        col.operator("esp.delete_cut", text="", icon='REMOVE').index = s.active_cut
        col.separator()
        col.operator("esp.refresh_pins", text="", icon='FILE_REFRESH')
        row = layout.row()
        row.scale_y = 1.2
        row.operator("esp.new_cut", text="New Cut", icon='ADD')
        ready = sum(1 for r in s.cuts if r.enabled)
        if s.built:
            layout.label(text=f"Built. {ready} ready cut(s) in the plan.", icon='CHECKMARK')
        else:
            layout.label(text=f"{ready} ready cut(s); geometry is computed on Build.", icon='INFO')
        rec = active_record(context)
        if rec is not None:
            box = layout.box()
            box.label(text=f"Edit: {rec.name}", icon='GREASEPENCIL')
            box.prop(rec, "name")
            row = box.row(align=True)
            row.label(
                text=TYPE_LABEL.get(rec.cut_type, "") + (" (2 contacts)" if rec.two_contact else ""),
                icon=TYPE_ICON.get(rec.cut_type, 'DOT'),
            )
            row.prop(rec, "enabled")
            box.operator("esp.edit_surface", icon='EDITMODE_HLT')
            if rec.cut_type == 'STRAIGHT' or rec.two_contact:
                box.label(text="G move, R rotate, S scale the plane", icon='INFO')
            else:
                box.label(text="Drag points; G slides the whole cut", icon='INFO')
            row = box.row(align=True)
            row.operator("esp.select_pin", text="Select Connector", icon='RESTRICT_SELECT_OFF').index = 0
            if rec.two_contact:
                row.operator("esp.select_pin", text="2nd", icon='RESTRICT_SELECT_OFF').index = 1
            row.operator("esp.reset_pin", text="Reset", icon='LOOP_BACK')
        if s.built:
            row = layout.row(align=True)
            row.scale_y = 1.2
            row.operator("esp.return_to_plan", icon='LOOP_BACK')
            row.operator("esp.approve", icon='CHECKMARK')
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("esp.build", icon='MOD_BUILD')
        row.operator("esp.clear_plan", icon='TRASH')


class ESP_PT_pin_adjust(ESPPanel, bpy.types.Panel):
    bl_label = "Manual Connector Adjust"
    bl_parent_id = "ESP_PT_plan"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.esp.mode == 'PLAN' and active_record(context) is not None

    def draw(self, context):
        layout = self.layout
        rec = active_record(context)
        names = [rec.pin_a] + ([rec.pin_b] if rec.two_contact else [])
        for i, name in enumerate(names):
            pin = bpy.data.objects.get(name)
            if pin is None:
                layout.label(text="No connector preview", icon='ERROR')
                continue
            if len(names) > 1:
                layout.label(text=f"Contact {i + 1}")
            col = layout.column(align=True)
            col.prop(pin, "location")
            col.prop(pin, "rotation_euler", text="Rotation")
            col.prop(pin, "scale")


class ESP_PT_explode(ESPPanel, bpy.types.Panel):
    bl_label = "Exploded View"
    bl_parent_id = "ESP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        layout.prop(s, "explode_distance_mm")
        if s.exploded:
            layout.operator("esp.collapse", icon='FULLSCREEN_EXIT')
        else:
            layout.operator("esp.explode", icon='FULLSCREEN_ENTER')


class ESP_PT_export(ESPPanel, bpy.types.Panel):
    bl_label = "Export"
    bl_parent_id = "ESP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.esp
        layout.prop(s, "export_folder")
        layout.prop(s, "export_format")
        row = layout.row()
        row.scale_y = 1.2
        row.operator("esp.export_parts", icon='EXPORT')


CLASSES = (
    ESP_UL_cuts,
    ESP_PT_main,
    ESP_PT_tools,
    ESP_PT_connector,
    ESP_PT_fit,
    ESP_PT_options,
    ESP_PT_remesh,
    ESP_PT_plan,
    ESP_PT_pin_adjust,
    ESP_PT_explode,
    ESP_PT_export,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
