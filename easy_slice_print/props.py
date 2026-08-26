# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Scene level settings and the planned-cut records."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .core import connectors

MODE_ITEMS = [
    ('QUICK', "Quick Cut", "Draw a cut and get the separated parts immediately (no plan history)", 'MOD_BOOLEAN', 0),
    (
        'PLAN',
        "Plan Mode",
        "Non-destructive: plan several cuts, edit, disable or remove them, build when ready",
        'MOD_BUILD',
        1,
    ),
]

TOOL_ITEMS = [
    ('STRAIGHT', "Plane Cut", "Drag a line in the viewport: a flat cut through the model", 'MESH_PLANE', 0),
    (
        'CURVED',
        "Curve Cut",
        "Draw a curved line over the model: the cut follows it through the model",
        'CURVE_BEZCURVE',
        1,
    ),
    (
        'FREEHAND',
        "Freehand Cut",
        "Draw a closed loop around the model surface: the loop is filled and used as the cut",
        'GREASEPENCIL',
        2,
    ),
]

SURFACE_ORIGIN_ITEMS = [
    (
        'SURFACE',
        "Cut Surface",
        "Origin at the centre of the cut surface itself, so R / S pivot on the surface",
        'PIVOT_MEDIAN_POINT',
        0,
    ),
    (
        'OBJECT',
        "Target Object",
        "Origin at the origin of the object being cut, so every cut surface shares one pivot",
        'OBJECT_ORIGIN',
        1,
    ),
]

SIDE_ITEMS = [
    ('A', "Side A", "The part on the + side of the cut surface carries the pin"),
    ('B', "Side B", "The part on the - side of the cut surface carries the pin"),
]

EXPORT_FORMATS = [
    ('STL', "STL", "Binary STL, one file per part"),
    ('OBJ', "OBJ", "Wavefront OBJ, one file per part"),
    ('FBX', "FBX", "Autodesk FBX, one file per part"),
]


def _record_update(self, context):
    from . import plan

    plan.on_record_settings_changed(context, self)


def _record_show_update(self, context):
    from . import plan

    plan.set_record_visibility(self, self.show)


def _active_update(self, context):
    from . import plan

    plan.on_active_changed(context)


def connector_props(update=None):
    """Connector settings shared by the scene defaults and every cut record."""
    return {
        'add_pin': BoolProperty(
            name="Add Connector",
            default=True,
            description="Create a matching pin and socket on this cut",
            update=update,
        ),
        'shape': EnumProperty(
            name="Shape",
            description="Connector shape (built-in or from the connector library)",
            items=connectors.shape_enum_items,
            update=update,
        ),
        'size_preset': EnumProperty(
            name="Size",
            items=[(i, n, d) for i, n, d, _f in connectors.SIZE_PRESETS],
            default='MEDIUM',
            description="Connector size relative to the cut cross-section",
            update=update,
        ),
        'pin_width_mm': FloatProperty(
            name="Width",
            description="Connector width / diameter in millimetres",
            default=5.0,
            min=0.2,
            soft_max=60.0,
            precision=2,
            update=update,
        ),
        'pin_height_mm': FloatProperty(
            name="Height",
            description="How far the pin protrudes into the socket (mm)",
            default=6.0,
            min=0.2,
            soft_max=80.0,
            precision=2,
            update=update,
        ),
        'cut_gap_mm': FloatProperty(
            name="Cut Gap",
            description="Total kerf: material removed along the cut (mm)",
            default=0.17,
            min=0.0,
            soft_max=5.0,
            precision=3,
            step=1,
        ),
        'clearance_mm': FloatProperty(
            name="Clearance",
            description="Radial gap between the pin and the socket (mm). Printer specific - test print!",
            default=0.30,
            min=0.0,
            soft_max=3.0,
            precision=3,
            step=1,
        ),
        'asymmetric': BoolProperty(
            name="Asymmetric Tip",
            default=True,
            description="Make the socket deeper than the pin so the pin never bottoms out (adds Tip Extra at the tip)",
        ),
        'tip_extra_mm': FloatProperty(
            name="Tip Extra",
            description="Extra socket depth at the tip (mm)",
            default=0.17,
            min=0.0,
            soft_max=5.0,
            precision=3,
            step=1,
        ),
        'pin_side': EnumProperty(name="Pin Side", items=SIDE_ITEMS, default='A', update=update),
    }


class ESP_CutRecord(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="Cut")
    cut_type: EnumProperty(name="Type", items=TOOL_ITEMS, default='STRAIGHT')
    enabled: BoolProperty(name="Ready", default=True, description="Include this cut in the build")
    show: BoolProperty(
        name="Show", default=True, description="Show the cut preview in the viewport", update=_record_show_update
    )
    target: StringProperty(name="Target", description="Object the cut was drawn on")
    two_contact: BoolProperty(default=False)
    surface_a: StringProperty()
    surface_b: StringProperty()
    pin_a: StringProperty()
    pin_b: StringProperty()
    pin_auto_a: FloatVectorProperty(size=16, default=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))
    pin_auto_b: FloatVectorProperty(size=16, default=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))
    center_a: FloatVectorProperty(size=3)
    center_b: FloatVectorProperty(size=3)
    normal_a: FloatVectorProperty(size=3, default=(0, 0, 1))
    normal_b: FloatVectorProperty(size=3, default=(0, 0, 1))
    inscribed_a: FloatProperty(default=1.0)
    inscribed_b: FloatProperty(default=1.0)
    anchor: FloatVectorProperty(
        size=3, description="World point on the model used to pick the part this cut applies to"
    )
    built: BoolProperty(default=False)


ESP_CutRecord.__annotations__.update(connector_props(update=_record_update))


class ESP_Settings(bpy.types.PropertyGroup):
    mode: EnumProperty(name="Mode", items=MODE_ITEMS, default='QUICK')
    tool: EnumProperty(name="Cut Tool", items=TOOL_ITEMS, default='STRAIGHT')
    freehand_smoothing: FloatProperty(
        name="Smoothing",
        description="Smooth the freehand loop before filling it",
        default=0.35,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    surface_origin: EnumProperty(
        name="Surface Origin",
        description="Where the origin of a generated cut surface is placed",
        items=SURFACE_ORIGIN_ITEMS,
        default='SURFACE',
    )
    surface_margin: FloatProperty(
        name="Surface Margin",
        description=(
            "How far the cut surface reaches past the region you drew, as a fraction of the "
            "stroke. The surface is sized to the stroke, not to the whole model, so a cut only "
            "touches what you marked - raise this if a cut fails to separate the part"
        ),
        default=0.06,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    control_points: IntProperty(
        name="Control Points", description="Editable points for curve and freehand cuts", default=20, min=4, max=96
    )
    two_contact: BoolProperty(
        name="Two Contacts / Base Split",
        default=False,
        description=(
            "Draw two contacts with any cut tool; both are cut together as one operation "
            "(e.g. two feet on a base). Each contact gets its own connector"
        ),
    )
    chain_cuts: BoolProperty(
        name="Chain Cuts", default=False, description="Start the same cut tool again right after a cut is finished"
    )
    keep_original: BoolProperty(
        name="Keep Original",
        default=True,
        description="Keep the source model (hidden in the ESP_Backup collection) instead of deleting it",
    )
    skip_failed: BoolProperty(
        name="Skip Failed Cuts",
        default=False,
        description="When a planned cut fails, skip it and keep building the others",
    )
    remesh_enable: BoolProperty(
        name="Remesh Parts",
        default=False,
        description="Voxel remesh the built parts (cleans boolean artefacts, loses fine detail)",
    )
    remesh_voxel_mm: FloatProperty(
        name="Voxel Size",
        default=0.3,
        min=0.01,
        soft_max=5.0,
        precision=3,
        description="Remesh voxel size in millimetres",
    )
    remesh_adaptivity: FloatProperty(name="Adaptivity", default=0.0, min=0.0, max=1.0, subtype='FACTOR')
    remesh_smooth: BoolProperty(name="Smooth Shading", default=False)
    explode_distance_mm: FloatProperty(
        name="Distance",
        default=5.0,
        min=0.0,
        soft_max=200.0,
        precision=2,
        description="How far the parts move away from each other (mm)",
    )
    exploded: BoolProperty(default=False)
    export_folder: StringProperty(name="Folder", subtype='DIR_PATH', default="//ESP_Export/")
    export_format: EnumProperty(name="Format", items=EXPORT_FORMATS, default='STL')
    cuts: CollectionProperty(type=ESP_CutRecord)
    active_cut: IntProperty(default=-1, update=_active_update)
    built: BoolProperty(default=False)
    base_object: StringProperty()
    built_collection: StringProperty()
    last_message: StringProperty()


ESP_Settings.__annotations__.update(connector_props(update=None))


CLASSES = (ESP_CutRecord, ESP_Settings)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.esp = PointerProperty(type=ESP_Settings)


def unregister():
    del bpy.types.Scene.esp
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
