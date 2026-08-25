import bpy
from bpy.props import BoolProperty, EnumProperty

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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "solver")
        layout.prop(self, "unit_mode")
        layout.prop(self, "check_mesh")
        box = layout.box()
        box.label(text="EasySlice Print is free and open source (PolyForm Noncommercial 1.0.0).", icon='INFO')
        box.label(text="Use it, modify it and contribute - but it may not be sold or used commercially.")


def register():
    bpy.utils.register_class(ESP_Preferences)


def unregister():
    bpy.utils.unregister_class(ESP_Preferences)
