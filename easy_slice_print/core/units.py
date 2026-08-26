# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Unit helpers. All user facing values are in millimetres."""


def mm_to_bu(scene, settings=None):
    """Blender units per millimetre for the current scene.

    With a millimetre scene (unit scale 0.001) 1 BU == 1 mm.
    With the default metre scene (unit scale 1.0) 1 mm == 0.001 BU.
    `settings.unit_mode == 'BU_IS_MM'` forces 1 BU == 1 mm regardless of scene.
    """
    if settings is not None and getattr(settings, "unit_mode", "SCENE") == 'BU_IS_MM':
        return 1.0
    scale = scene.unit_settings.scale_length or 1.0
    return 0.001 / scale


def bu_to_mm(scene, settings=None):
    return 1.0 / mm_to_bu(scene, settings)
