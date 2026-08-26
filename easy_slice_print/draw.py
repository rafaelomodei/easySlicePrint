# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Small GPU drawing helpers for the modal tools (region pixel space)."""

import gpu
from gpu_extras.batch import batch_for_shader

GREEN = (0.35, 0.95, 0.45, 0.95)
ORANGE = (1.0, 0.55, 0.15, 0.95)
WHITE = (1.0, 1.0, 1.0, 0.9)
RED = (1.0, 0.25, 0.2, 0.95)
DIM = (1.0, 1.0, 1.0, 0.35)


def _to3(points):
    return [(p[0], p[1], 0.0) for p in points]


def lines_2d(points, color, width=2.0, closed=False):
    if len(points) < 2:
        return
    pts = _to3(points)
    if closed:
        pts.append(pts[0])
    gpu.state.blend_set('ALPHA')
    try:
        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pts})
        shader.bind()
        shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("color", color)
        batch.draw(shader)
    except Exception:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(width)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pts})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def points_2d(points, color, size=8.0):
    if not points:
        return
    gpu.state.blend_set('ALPHA')
    gpu.state.point_size_set(size)
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": _to3(points)})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.point_size_set(1.0)
    gpu.state.blend_set('NONE')


def circle_2d(center, radius, color, segments=24, width=1.5):
    import math

    pts = [
        (
            center[0] + math.cos(2 * math.pi * i / segments) * radius,
            center[1] + math.sin(2 * math.pi * i / segments) * radius,
        )
        for i in range(segments)
    ]
    lines_2d(pts, color, width, closed=True)
