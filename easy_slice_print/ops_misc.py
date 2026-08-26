# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Exploded view, export, connector library, mesh check."""

import os
import re

import bpy
from mathutils import Vector

from . import plan
from .core import connectors, mesh_utils

DOCS_URL = "https://github.com/rafaelomodei/easySlicePrint#readme"


def part_objects(context):
    """Selected parts, else every part of the last build, else selected meshes."""
    sel = [o for o in context.selected_objects if o.type == 'MESH' and o.get("esp_part")]
    if sel:
        return sel
    s = context.scene.esp
    col = bpy.data.collections.get(s.built_collection) if s.built_collection else None
    if col is not None and len(col.objects):
        return [o for o in col.objects if o.type == 'MESH']
    parts = [o for o in context.scene.objects if o.type == 'MESH' and o.get("esp_part") and o.visible_get()]
    if parts:
        return parts
    return [o for o in context.selected_objects if o.type == 'MESH']


def explode(context, parts, distance_bu):
    centers = []
    for p in parts:
        home = Vector(p["esp_home"]) if "esp_home" in p else p.location.copy()
        p["esp_home"] = list(home)
        c = p.matrix_world @ mesh_utils.mesh_centroid(p.data)
        c = c - p.location + home
        centers.append(c)
    if not centers:
        return
    gc = sum(centers, Vector((0.0, 0.0, 0.0))) / len(centers)
    for p, c in zip(parts, centers):
        d = c - gc
        home = Vector(p["esp_home"])
        p.location = home if d.length < 1e-9 else home + d.normalized() * distance_bu


def collapse(parts):
    for p in parts:
        if "esp_home" in p:
            p.location = Vector(p["esp_home"])
            del p["esp_home"]


class ESP_OT_explode(bpy.types.Operator):
    bl_idname = "esp.explode"
    bl_label = "Explode"
    bl_description = "Move the parts apart so you can inspect the connectors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.esp
        parts = part_objects(context)
        if len(parts) < 2:
            self.report({'WARNING'}, "Need at least two parts")
            return {'CANCELLED'}
        explode(context, parts, s.explode_distance_mm * plan.mm(context))
        s.exploded = True
        self.report({'INFO'}, f"Exploded {len(parts)} object(s)")
        return {'FINISHED'}


class ESP_OT_collapse(bpy.types.Operator):
    bl_idname = "esp.collapse"
    bl_label = "Collapse"
    bl_description = "Put the exploded parts back in place"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.esp
        parts = [o for o in context.scene.objects if "esp_home" in o]
        collapse(parts)
        s.exploded = False
        return {'FINISHED'}


def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9._-]+', "_", name).strip("_") or "part"


class ESP_OT_export(bpy.types.Operator):
    bl_idname = "esp.export_parts"
    bl_label = "Export Parts"
    bl_description = "Write one file per part (selected parts, or every part of the last build) to the folder"
    bl_options = {'REGISTER'}

    def execute(self, context):
        s = context.scene.esp
        parts = part_objects(context)
        if not parts:
            self.report({'ERROR'}, "No parts to export. Select the parts or build first.")
            return {'CANCELLED'}
        folder = bpy.path.abspath(s.export_folder)
        if not folder:
            self.report({'ERROR'}, "Choose an export folder")
            return {'CANCELLED'}
        os.makedirs(folder, exist_ok=True)
        unit_mode = plan.pref(context, "unit_mode", 'SCENE')
        bu_to_mm = 1.0 if unit_mode == 'BU_IS_MM' else (context.scene.unit_settings.scale_length or 1.0) * 1000.0
        prev_sel = [o for o in context.selected_objects]
        prev_active = context.view_layer.objects.active
        exploded = [o for o in parts if "esp_home" in o]
        if exploded:
            collapse(exploded)
        written = []
        try:
            for p in parts:
                for o in context.view_layer.objects:
                    o.select_set(False)
                p.select_set(True)
                context.view_layer.objects.active = p
                ext = s.export_format.lower()
                path = os.path.join(folder, safe_filename(p.name) + "." + ext)
                if s.export_format == 'STL':
                    bpy.ops.wm.stl_export(
                        filepath=path,
                        export_selected_objects=True,
                        global_scale=bu_to_mm,
                        use_scene_unit=False,
                        apply_modifiers=True,
                    )
                elif s.export_format == 'OBJ':
                    bpy.ops.wm.obj_export(
                        filepath=path,
                        export_selected_objects=True,
                        global_scale=bu_to_mm,
                        apply_modifiers=True,
                        export_materials=False,
                    )
                else:
                    bpy.ops.export_scene.fbx(
                        filepath=path, use_selection=True, apply_unit_scale=True, object_types={'MESH'}
                    )
                written.append(path)
        finally:
            if exploded:
                explode(context, exploded, s.explode_distance_mm * plan.mm(context))
            for o in context.view_layer.objects:
                o.select_set(False)
            for o in prev_sel:
                try:
                    o.select_set(True)
                except RuntimeError:
                    pass
            if prev_active is not None:
                context.view_layer.objects.active = prev_active
        s.last_message = f"Exported {len(written)} file(s)"
        self.report({'INFO'}, f"Exported {len(written)} {s.export_format} file(s) to {folder}")
        return {'FINISHED'}


class ESP_OT_connector_library(bpy.types.Operator):
    bl_idname = "esp.connector_library"
    bl_label = "Connector Library"
    bl_description = (
        "Create the ESP_Connectors collection with editable template shapes. Any mesh you add "
        "there (fitting x/y in -0.5..0.5 and z in -1..1, +z = the pin tip) becomes a custom connector"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        col, created = connectors.ensure_library(context)
        col.hide_viewport = False
        self.report(
            {'INFO'}, f"Connector library ready ({len(col.objects)} shapes). Edit or add meshes in '{col.name}'."
        )
        return {'FINISHED'}


class ESP_OT_check_mesh(bpy.types.Operator):
    bl_idname = "esp.check_mesh"
    bl_label = "Check Mesh"
    bl_description = "Report boundary and non-manifold edges of the active object"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        non, boundary, total = mesh_utils.manifold_report(obj.data)
        if non == 0 and boundary == 0:
            self.report({'INFO'}, f"'{obj.name}' is closed and manifold ({total} edges). Good to cut.")
        else:
            self.report(
                {'WARNING'},
                f"'{obj.name}': {boundary} boundary edge(s), {non} non-manifold edge(s). "
                "Fix them (3D-Print Toolbox / Mesh > Clean Up) before cutting.",
            )
        return {'FINISHED'}


class ESP_OT_open_docs(bpy.types.Operator):
    bl_idname = "esp.open_docs"
    bl_label = "Help"
    bl_description = "Open the EasySlice Print documentation"

    def execute(self, context):
        bpy.ops.wm.url_open(url=DOCS_URL)
        return {'FINISHED'}


CLASSES = (
    ESP_OT_explode,
    ESP_OT_collapse,
    ESP_OT_export,
    ESP_OT_connector_library,
    ESP_OT_check_mesh,
    ESP_OT_open_docs,
)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
