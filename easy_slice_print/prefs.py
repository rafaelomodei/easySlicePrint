# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from .core import mesh_utils


def _solver_items(self, context):
    ids = mesh_utils.available_solvers()
    items = [('AUTO', "Auto", "Manifold solver when available (fast), Exact as fallback")]
    labels = {
        'MANIFOLD': ("Manifold", "Fast solver for closed manifold meshes (Blender 4.5+)"),
        'EXACT': ("Exact", "Robust, slower"),
        'FLOAT': ("Float", "Fastest, least robust"),
        'FAST': ("Fast", "Fastest, least robust"),
    }
    for i in ids:
        if i in labels:
            items.append((i, labels[i][0], labels[i][1]))
    return items


class ESP_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    solver: EnumProperty(name="Boolean Solver", items=_solver_items)
    unit_mode: EnumProperty(
        name="Units",
        items=[
            (
                'SCENE',
                "Scene units",
                "Convert millimetres using the scene unit scale (recommended: a millimetre scene)",
            ),
            ('BU_IS_MM', "1 unit = 1 mm", "Treat one Blender unit as one millimetre regardless of the scene settings"),
        ],
        default='SCENE',
    )
    check_mesh: BoolProperty(name="Warn about non-manifold meshes before cutting", default=True)
    printer_clearance_mm: FloatProperty(
        name="Printer Clearance",
        description=(
            "How much room your printer needs between a pin and its socket for the printed parts "
            "to fit together, measured on each side of the pin. This is the number that decides "
            "whether a connector goes home firmly, rattles, or will not go in at all - it belongs "
            "to the printer and the filament, not to the model, which is why it lives here and is "
            "set once. 0.1 mm suits most FDM printers; raise it if your parts come out too tight. "
            "Each cut then picks how tight that joint should be with its Fit setting"
        ),
        default=0.10,
        min=0.0,
        soft_max=0.6,
        precision=3,
        step=1,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Printer profile", icon='TOOL_SETTINGS')
        box.prop(self, "printer_clearance_mm")
        box.label(text="Print a test joint once, then leave it alone.", icon='INFO')
        layout.prop(self, "solver")
        layout.prop(self, "unit_mode")
        layout.prop(self, "check_mesh")
        box = layout.box()
        box.label(text="EasySlice Print is free software (GNU GPL v3.0 or later).", icon='INFO')
        box.label(text="Use it, study it, modify it and share it - contributions welcome.")


def register():
    bpy.utils.register_class(ESP_Preferences)


def unregister():
    bpy.utils.unregister_class(ESP_Preferences)
