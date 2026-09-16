# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""The diagnosis of a failed cut, painted on the cut surface in the 3D viewport.

`core.diagnosis` finds where a failed boolean left the two halves joined, and scores
any point by its distance from there: 0 on the join, 1 well clear of it. This module
paints the cut surface with that scale - red where the cut fails to separate, orange
around it, green where it is cutting cleanly, all red when none of it reaches the
model - drawn straight from the GPU with a draw handler, so it needs no vertex
colours, no change to the viewport shading, and disappears without a trace. The
model itself is left alone: the surface is what the user edits, so the surface is
what carries the map.

The map stays until the next cut attempt, the next build, or the user hides it. It is
not part of the undo history - nothing in the scene is - so an undo that takes the cut
away has to take the map with it: after every undo or redo the map is kept only while
the cut it was made for is still in the plan.
"""

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

RED = (1.0, 0.22, 0.18)
ORANGE = (1.0, 0.58, 0.12)
GREEN = (0.30, 0.90, 0.40)
SURFACE_ALPHA = 0.75
SPLIT_DEPTH = 6  # a coarse cutter face is subdivided this many times at most, so the gradient shows on it

_state = None  # what is being shown; None when nothing is
_handler = None


class _Shown:
    def __init__(self, surface, cut, label):
        self.surface = surface  # (positions, colours, indices)
        self.cut = cut  # the cutter carved something: red is a join; otherwise nothing cut
        self.label = label  # the cut this belongs to, for the panel
        self.batch = None  # built on the first draw, on the GPU thread


def ramp(score):
    """Red at 0, orange half way, green at 1."""
    if score <= 0.5:
        t = score * 2.0
        a, b = RED, ORANGE
    else:
        t = (score - 0.5) * 2.0
        a, b = ORANGE, GREEN
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _split_triangle(a, b, c, limit, depth, out):
    """`abc` as triangles no longer than `limit` on any side, up to `depth` splits."""
    if depth <= 0 or max((b - a).length, (c - b).length, (a - c).length) <= limit:
        out.append((a, b, c))
        return
    ab, bc, ca = (a + b) * 0.5, (b + c) * 0.5, (c + a) * 0.5
    _split_triangle(a, ab, ca, limit, depth - 1, out)
    _split_triangle(ab, b, bc, limit, depth - 1, out)
    _split_triangle(ca, bc, c, limit, depth - 1, out)
    _split_triangle(ab, bc, ca, limit, depth - 1, out)


def _surface_geometry(diag, verts, faces):
    """The cut surface, tessellated finely enough for the gradient to show on a coarse face.

    It is drawn from both sides, so its own normal is not used for shading: the colour
    alone has to say where it stands.
    """
    if not verts or not faces:
        return None
    pts = [Vector(v) for v in verts]
    tris = []
    limit = diag.radius * 0.5 if diag.cut else 1e30
    for f in faces:
        for k in range(1, len(f) - 1):
            _split_triangle(pts[f[0]], pts[f[k]], pts[f[k + 1]], limit, SPLIT_DEPTH, tris)
    if not tris:
        return None
    index = {}
    pos = []
    for t in tris:
        for p in t:
            key = (round(p.x, 6), round(p.y, 6), round(p.z, 6))
            if key not in index:
                index[key] = len(pos)
                pos.append(p)
    scores = diag.score_points(pos)
    colors = [ramp(s) + (SURFACE_ALPHA,) for s in scores]
    indices = [tuple(index[(round(p.x, 6), round(p.y, 6), round(p.z, 6))] for p in t) for t in tris]
    return [tuple(p) for p in pos], colors, indices


def show(diag, label=""):
    """Paint `diag` (a `core.diagnosis.Diagnosis`) on the surface it carries. -> shown?"""
    global _state
    if diag is None:
        clear()
        return False
    verts, faces = diag.surface
    surface = _surface_geometry(diag, verts, faces)
    if surface is None:
        clear()
        return False
    _state = _Shown(surface, diag.cut, label)
    _ensure_handler()
    redraw()
    return True


def show_with_note(diag, label=""):
    """`show`, and the sentence to append to the error message when the map is up."""
    if diag is None or not show(diag, label):
        return ""
    if diag.cut:
        return " The cut surface is shown red where the halves stay joined."
    return " The cut surface is shown all red: none of it cuts the model."


def clear():
    global _state
    if _state is None:
        return
    _state = None
    redraw()


def active():
    return _state is not None


def shown():
    return _state


def redraw():
    try:
        windows = bpy.context.window_manager.windows
    except AttributeError:
        return
    for window in windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# ----------------------------------------------------------------------------
# drawing
# ----------------------------------------------------------------------------
def _batch(state):
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin('SMOOTH_COLOR')
    pos, colors, indices = state.surface
    return shader, batch_for_shader(shader, 'TRIS', {"pos": pos, "color": colors}, indices=indices)


def _draw():
    state = _state
    if state is None:
        return
    import gpu

    if state.batch is None:
        try:
            state.batch = _batch(state)
        except Exception:
            state.batch = (None, None)
    shader, batch = state.batch
    if shader is None:
        return
    gpu.state.blend_set('ALPHA')
    gpu.state.face_culling_set('NONE')
    # the cut runs through the material: it has to show through, like the preview does
    gpu.state.depth_test_set('NONE')
    shader.bind()
    batch.draw(shader)
    gpu.state.blend_set('NONE')


def _ensure_handler():
    global _handler
    if _handler is not None or bpy.app.background:
        return
    _handler = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_VIEW')


def _remove_handler():
    global _handler
    if _handler is None:
        return
    try:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
    except Exception:
        pass
    _handler = None


@persistent
def _load_pre(_dummy):
    clear()


@persistent
def _undo_post(scene, _depsgraph):
    """Undo or redo: the map stays only while the cut it belongs to is still in the plan.

    A Quick cut is never in the plan, so its map goes with the first undo - which is
    the undo of the cut itself.
    """
    state = _state
    if state is None:
        return
    settings = getattr(scene, "esp", None)
    if settings is None or not any(rec.name == state.label for rec in settings.cuts):
        clear()


_HANDLERS = (
    (bpy.app.handlers.load_pre, _load_pre),
    (bpy.app.handlers.undo_post, _undo_post),
    (bpy.app.handlers.redo_post, _undo_post),
)


def register():
    for handlers, fn in _HANDLERS:
        if fn not in handlers:
            handlers.append(fn)


def unregister():
    clear()
    _remove_handler()
    for handlers, fn in _HANDLERS:
        if fn in handlers:
            handlers.remove(fn)
