# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Plan (draft) records, preview objects and the glue between records and the
core cut pipeline."""

import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix, Vector

from .core import connectors, cutting, mesh_utils, surfaces
from .core.units import mm_to_bu
from .props import connector_props

PLAN_COLLECTION = "_ESP_Plan"
BACKUP_COLLECTION = "ESP_Backup"
BUILT_PREFIX = "ESP_Built_"
GREEN = (0.30, 0.90, 0.40, 0.40)
ORANGE = (1.00, 0.55, 0.15, 0.85)
PREFIX = {'STRAIGHT': "Plane Cut", 'CURVED': "Curve Cut", 'FREEHAND': "Freehand Cut"}

_suspend = 0


class ContactData:
    """What a cut tool produces for one contact (everything in world space)."""

    def __init__(self, kind):
        self.kind = kind
        self.verts = []
        self.faces = []
        self.points = []  # editable control points (curve / freehand)
        self.view_dir = Vector((0.0, 0.0, -1.0))
        self.depth_range = (0.0, 0.0)
        self.extend = 0.0
        self.margin = 0.0
        self.detail = surfaces.SURFACE_DETAIL  # spline samples per control point segment
        self.hit = None  # where the stroke touched the model
        self.through = None  # direction through the model at `hit`
        self.center_hint = None  # alternative: a point inside the part
        self.anchor = Vector((0.0, 0.0, 0.0))


# ----------------------------------------------------------------------------
# preferences / units
# ----------------------------------------------------------------------------
def prefs(context):
    try:
        return context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return None


def pref(context, name, default):
    p = prefs(context)
    return getattr(p, name, default) if p is not None else default


def mm(context):
    return mm_to_bu(context.scene, prefs(context))


# ----------------------------------------------------------------------------
# collections
# ----------------------------------------------------------------------------
def get_or_create_collection(scene, name, hide_render=True):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    col.hide_render = hide_render
    return col


def plan_collection(scene):
    return get_or_create_collection(scene, PLAN_COLLECTION)


def backup_collection(scene):
    return get_or_create_collection(scene, BACKUP_COLLECTION)


def built_collection(scene, base_name):
    return get_or_create_collection(scene, BUILT_PREFIX + base_name, hide_render=False)


def move_to_backup(scene, obj):
    homes = [c.name for c in obj.users_collection]
    for c in obj.users_collection:
        c.objects.unlink(obj)
    backup_collection(scene).objects.link(obj)
    obj["esp_backup_home"] = homes
    obj.hide_set(True)
    obj.hide_render = True


def restore_from_backup(scene, obj):
    homes = list(obj.get("esp_backup_home", []))
    bc = bpy.data.collections.get(BACKUP_COLLECTION)
    if bc is not None and obj.name in bc.objects:
        bc.objects.unlink(obj)
    linked = False
    for name in homes:
        col = bpy.data.collections.get(name)
        if col is None and name == scene.collection.name:
            col = scene.collection
        if col is not None and obj.name not in col.objects:
            col.objects.link(obj)
            linked = True
    if not linked and obj.name not in scene.collection.objects:
        scene.collection.objects.link(obj)
    if "esp_backup_home" in obj:
        del obj["esp_backup_home"]
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_render = False


def ensure_evaluable(obj):
    """Make sure a (possibly hidden) object is evaluated by the depsgraph."""
    state = (obj.hide_viewport, obj.hide_get())
    obj.hide_viewport = False
    obj.hide_set(False)
    return state


def restore_visibility(obj, state):
    obj.hide_viewport = state[0]
    obj.hide_set(state[1])


def resolve_target(context):
    """The mesh the cut tools act on: active mesh object (never a preview), else the plan's base."""
    obj = context.active_object
    if obj is not None and obj.type == 'MESH' and "esp_preview" not in obj and obj.visible_get():
        return obj
    settings = context.scene.esp
    base = bpy.data.objects.get(settings.base_object) if settings.base_object else None
    if base is not None and base.type == 'MESH':
        return base
    return None


# ----------------------------------------------------------------------------
# preview objects
# ----------------------------------------------------------------------------
def _material(name, rgba):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = False
    mat.diffuse_color = rgba
    try:
        mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    return mat


def _preview_object(scene, name, mesh, kind, color, mat_name):
    obj = bpy.data.objects.new(name, mesh)
    plan_collection(scene).objects.link(obj)
    obj.display_type = 'SOLID'
    obj.show_in_front = True
    obj.hide_render = True
    obj.color = color
    obj["esp_preview"] = kind
    mesh.materials.append(_material(mat_name, color))
    return obj


def surface_origin_point(context, data, target):
    """Where the origin of a generated cut surface goes.

    By default the surface's own median point, so R / S on it pivot on the surface
    instead of on some point out in the scene. 'OBJECT' puts it on the origin of the
    model being cut, which is what you want when several cut surfaces should share
    one pivot.
    """
    if context.scene.esp.surface_origin == 'OBJECT' and target is not None:
        return target.matrix_world.translation.copy()
    if data.verts:
        return surfaces.patch_center(data.verts)
    return Vector((0.0, 0.0, 0.0))


def create_surface_object(context, name, data, target=None):
    """The patch arrives in world space; it is stored local to `origin` so the preview
    object carries a real origin of its own (mesh AND the editable control points)."""
    origin = surface_origin_point(context, data, target)
    me = mesh_utils.mesh_from_pydata(name, [Vector(v) - origin for v in data.verts], data.faces)
    obj = _preview_object(context.scene, name, me, 'surface', GREEN, "ESP_Preview_Surface")
    obj.matrix_world = Matrix.Translation(origin)
    obj["esp_kind"] = data.kind
    flat_pts = [c for p in data.points for c in (Vector(p) - origin)]
    obj["esp_points"] = flat_pts
    obj["esp_points_orig"] = list(flat_pts)
    obj["esp_view"] = list(data.view_dir)
    obj["esp_depth"] = list(data.depth_range)
    obj["esp_extend"] = data.extend
    obj["esp_margin"] = data.margin
    obj["esp_detail"] = data.detail
    if data.hit is not None:
        obj["esp_hit"] = list(data.hit)
        obj["esp_through"] = list(data.through)
    if data.center_hint is not None:
        obj["esp_center_hint"] = list(data.center_hint)
    obj["esp_mw"] = [v for row in obj.matrix_world for v in row]
    return obj


def surface_points(obj):
    flat = list(obj.get("esp_points", []))
    return [Vector(flat[i : i + 3]) for i in range(0, len(flat) - 2, 3)]


def set_surface_points(obj, points):
    obj["esp_points"] = [c for p in points for c in p]


def rebuild_surface(obj, draft=False):
    """Regenerate the patch from its control points.

    `draft` halves the spline resolution and cuts the membrane relaxation short; it is
    what runs while a control point is being dragged, so the preview keeps up with the
    mouse. The full surface is rebuilt as soon as the drag ends.
    """
    kind = obj.get("esp_kind", 'STRAIGHT')
    pts = surface_points(obj)
    detail = int(obj.get("esp_detail", surfaces.SURFACE_DETAIL))
    if draft:
        detail = max(1, detail // 2)
    if kind == 'CURVED' and len(pts) >= 2:
        # the control points are local to the object; the stored view direction is world
        view = (obj.matrix_basis.to_3x3().inverted_safe() @ Vector(obj["esp_view"])).normalized()
        verts, faces = surfaces.ribbon_patch(
            pts, view, 0.0, obj["esp_extend"], depth_range=tuple(obj["esp_depth"]), detail=detail
        )
    elif kind == 'FREEHAND' and len(pts) >= 3:
        verts, faces = surfaces.loop_patch(pts, detail=detail, passes=6 if draft else None)
    else:
        return
    me = obj.data
    me.clear_geometry()
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()


def surface_world_patch(obj):
    mw = obj.matrix_basis  # previews are never parented; basis is always current
    verts = [mw @ v.co for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    return verts, faces


def create_pin_object(context, name, shape_id, matrix):
    shape, custom = connectors.resolve_shape(shape_id)
    bm = connectors.unit_connector_bmesh(shape, custom)
    me = mesh_utils.bmesh_to_mesh(bm, name)
    bm.free()
    obj = _preview_object(context.scene, name, me, 'pin', ORANGE, "ESP_Preview_Pin")
    obj.matrix_world = matrix
    obj["esp_shape"] = shape_id
    return obj


def update_pin_mesh(obj, shape_id):
    shape, custom = connectors.resolve_shape(shape_id)
    bm = connectors.unit_connector_bmesh(shape, custom)
    me = mesh_utils.bmesh_to_mesh(bm, obj.name)
    bm.free()
    me.materials.append(_material("ESP_Preview_Pin", ORANGE))
    old = obj.data
    obj.data = me
    mesh_utils.remove_mesh(old)
    obj["esp_shape"] = shape_id


def flat(m):
    return [m[i][j] for i in range(4) for j in range(4)]


def unflat(vals):
    return Matrix([[vals[i * 4 + j] for j in range(4)] for i in range(4)])


# ----------------------------------------------------------------------------
# frames & sizes
# ----------------------------------------------------------------------------
def contact_frame(context, target, verts, faces, hit=None, through=None, center_hint=None):
    bvh = mesh_utils.bvh_from_pydata(verts, faces)
    diag = mesh_utils.object_world_diagonal(target)
    state = ensure_evaluable(target)
    try:
        depsgraph = context.evaluated_depsgraph_get()
        if center_hint is not None:
            return cutting.estimate_pin_frame(target, depsgraph, bvh, diag, center_hint=center_hint)
        return cutting.estimate_pin_frame(target, depsgraph, bvh, diag, surface_point=hit, through_dir=through)
    finally:
        restore_visibility(target, state)


def preset_size_mm(context, preset, inscribed_bu):
    factor = connectors.preset_factor(preset)
    width_mm = max(1.0, inscribed_bu * factor / mm(context))
    return width_mm, width_mm * connectors.HEIGHT_RATIO


def contact_size_bu(context, src, inscribed_bu):
    """(width, height) in BU for a settings source (record or scene defaults)."""
    if src.size_preset == 'CUSTOM':
        return src.pin_width_mm * mm(context), src.pin_height_mm * mm(context)
    w_mm, h_mm = preset_size_mm(context, src.size_preset, inscribed_bu)
    return w_mm * mm(context), h_mm * mm(context)


def _contact_attr(rec, base, i):
    return getattr(rec, f"{base}_{'ab'[i]}")


def _set_contact_attr(rec, base, i, value):
    setattr(rec, f"{base}_{'ab'[i]}", value)


def auto_pin_matrix(context, rec, i):
    center = Vector(_contact_attr(rec, "center", i))
    normal = Vector(_contact_attr(rec, "normal", i))
    w, h = contact_size_bu(context, rec, _contact_attr(rec, "inscribed", i))
    return connectors.connector_matrix(center, cutting.protrude_direction(normal, rec.pin_side), w, h)


def apply_preset(context, rec):
    """Write the preset size of contact A into the width/height fields."""
    if rec.size_preset == 'CUSTOM':
        return
    w_mm, h_mm = preset_size_mm(context, rec.size_preset, rec.inscribed_a)
    rec.pin_width_mm = w_mm
    rec.pin_height_mm = h_mm


def printer_clearance_mm(context):
    """The clearance this printer needs on each side of a pin, from the preferences."""
    return pref(context, "printer_clearance_mm", 0.10)


def preset_clearance_mm(context, fit_preset):
    return printer_clearance_mm(context) * connectors.fit_factor(fit_preset)


_applying_fit = False


def apply_fit(context, src):
    """Write the Fit preset into the gap field, so the number in the panel is the real one.

    `src` is a cut record or the scene defaults - both carry the connector settings. The
    write lands on a property that has an update callback of its own, which calls back in
    here, so the guard and the tolerance check keep it from looping.
    """
    global _applying_fit
    if src.fit_preset == 'CUSTOM' or _applying_fit:
        return
    target = preset_clearance_mm(context, src.fit_preset)
    if abs(src.clearance_mm - target) <= 1e-6:
        return
    _applying_fit = True
    try:
        src.clearance_mm = target
    finally:
        _applying_fit = False


def copy_connector_props(src, dst):
    for key in connector_props():
        try:
            setattr(dst, key, getattr(src, key))
        except TypeError:
            pass


def contact_count(rec):
    return 2 if rec.two_contact else 1


def record_objects(rec):
    out = []
    for name in (rec.surface_a, rec.surface_b, rec.pin_a, rec.pin_b):
        if name:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                out.append(obj)
    return out


def unique_record_name(settings, prefix):
    names = {r.name for r in settings.cuts}
    n = 1
    while f"{prefix} {n:03d}" in names:
        n += 1
    return f"{prefix} {n:03d}"


# ----------------------------------------------------------------------------
# records
# ----------------------------------------------------------------------------
def add_record(context, target, cut_type, contacts):
    global _suspend
    settings = context.scene.esp
    _suspend += 1
    try:
        base_name = target.get("esp_base", target.name) if target.get("esp_part") else target.name
        if not settings.base_object or bpy.data.objects.get(settings.base_object) is None:
            settings.base_object = base_name
        rec = settings.cuts.add()
        rec.name = unique_record_name(settings, "Base Split" if len(contacts) == 2 else PREFIX[cut_type])
        rec.cut_type = cut_type
        rec.target = target.name
        rec.two_contact = len(contacts) == 2
        active = settings.cuts[settings.active_cut] if 0 <= settings.active_cut < len(settings.cuts) - 1 else None
        copy_connector_props(active if active is not None else settings, rec)
        for i, data in enumerate(contacts):
            sobj = create_surface_object(context, f"ESP_Surface_{rec.name}_{'AB'[i]}", data, target)
            _set_contact_attr(rec, "surface", i, sobj.name)
            center, normal, inscribed = contact_frame(
                context, target, data.verts, data.faces, data.hit, data.through, data.center_hint
            )
            _set_contact_attr(rec, "center", i, center)
            _set_contact_attr(rec, "normal", i, normal)
            _set_contact_attr(rec, "inscribed", i, inscribed)
        apply_preset(context, rec)
        apply_fit(context, rec)
        for i in range(len(contacts)):
            matrix = auto_pin_matrix(context, rec, i)
            pin = create_pin_object(context, f"ESP_Pin_{rec.name}_{'AB'[i]}", rec.shape, matrix)
            _set_contact_attr(rec, "pin", i, pin.name)
            _set_contact_attr(rec, "pin_auto", i, flat(matrix))
            pin.hide_viewport = not rec.add_pin
        rec.anchor = contacts[0].anchor
        settings.active_cut = len(settings.cuts) - 1
    finally:
        _suspend -= 1
    return rec


def on_record_settings_changed(context, rec):
    global _suspend
    if _suspend:
        return
    _suspend += 1
    try:
        apply_preset(context, rec)
        apply_fit(context, rec)
        for i in range(contact_count(rec)):
            pin = bpy.data.objects.get(_contact_attr(rec, "pin", i))
            if pin is None:
                continue
            if pin.get("esp_shape") != rec.shape:
                update_pin_mesh(pin, rec.shape)
            old_auto = unflat(_contact_attr(rec, "pin_auto", i))
            new_auto = auto_pin_matrix(context, rec, i)
            delta = user_delta(old_auto, pin.matrix_basis)
            pin.matrix_world = _frame(new_auto) @ delta @ _scale(new_auto)
            _set_contact_attr(rec, "pin_auto", i, flat(new_auto))
            pin.hide_viewport = not (rec.add_pin and rec.show)
    finally:
        _suspend -= 1


def _is_identity(m, tol=1e-5):
    ident = Matrix.Identity(4)
    return all(abs(m[i][j] - ident[i][j]) < tol for i in range(4) for j in range(4))


def _frame(m):
    """Rotation + translation part of a matrix (scale removed)."""
    return m.normalized()


def _scale(m):
    s = m.to_scale()
    return Matrix.Diagonal((s.x, s.y, s.z, 1.0))


def user_delta(auto, current):
    """What the user did to the pin, expressed in the pin's unscaled local frame.

    auto = F @ S  (frame @ scale); current = F @ D @ S  ->  D = F^-1 @ current @ S^-1
    Identity when the pin was never touched. Survives size/side/shape changes.
    """
    d = _frame(auto).inverted_safe() @ current @ _scale(auto).inverted_safe()
    return Matrix.Identity(4) if _is_identity(d) else d


def user_moved_pin(rec, i):
    pin = bpy.data.objects.get(_contact_attr(rec, "pin", i))
    if pin is None:
        return False
    return not _is_identity(user_delta(unflat(_contact_attr(rec, "pin_auto", i)), pin.matrix_basis))


def reset_pins(context, rec):
    global _suspend
    _suspend += 1
    try:
        for i in range(contact_count(rec)):
            pin = bpy.data.objects.get(_contact_attr(rec, "pin", i))
            if pin is None:
                continue
            auto = auto_pin_matrix(context, rec, i)
            pin.matrix_world = auto
            _set_contact_attr(rec, "pin_auto", i, flat(auto))
    finally:
        _suspend -= 1


def refresh_record_frames(context, rec):
    """Re-estimate centre/normal/size from the (possibly edited) cut surfaces."""
    target = bpy.data.objects.get(rec.target)
    base = bpy.data.objects.get(context.scene.esp.base_object)
    if target is None:
        target = base
    if target is None:
        return
    for i in range(contact_count(rec)):
        sobj = bpy.data.objects.get(_contact_attr(rec, "surface", i))
        if sobj is None:
            continue
        verts, faces = surface_world_patch(sobj)
        hit = Vector(sobj["esp_hit"]) if "esp_hit" in sobj else None
        through = Vector(sobj["esp_through"]) if "esp_through" in sobj else None
        hint = Vector(sobj["esp_center_hint"]) if "esp_center_hint" in sobj else None
        if hit is not None and sobj.get("esp_kind") == 'STRAIGHT':
            # a moved plane: re-anchor the hit onto the new plane along the view direction
            hint, hit = _reanchor_plane(verts, faces, hit, through, hint)
        try:
            center, normal, inscribed = contact_frame(context, target, verts, faces, hit, through, hint)
        except Exception:
            continue
        _set_contact_attr(rec, "center", i, center)
        _set_contact_attr(rec, "normal", i, normal)
        _set_contact_attr(rec, "inscribed", i, inscribed)
        sobj["esp_mw"] = flat(sobj.matrix_world)
    on_record_settings_changed(context, rec)


def _reanchor_plane(verts, faces, hit, through, hint):
    n = surfaces.patch_normal(verts, faces)
    c = surfaces.patch_center(verts)
    d = Vector(through) if through is not None else n
    denom = d.dot(n)
    if abs(denom) < 1e-6:
        return c, None
    t = (c - hit).dot(n) / denom
    return None, hit + d * t


def set_record_visibility(rec, show):
    for i in range(contact_count(rec)):
        s = bpy.data.objects.get(_contact_attr(rec, "surface", i))
        if s is not None:
            s.hide_viewport = not show
        p = bpy.data.objects.get(_contact_attr(rec, "pin", i))
        if p is not None:
            p.hide_viewport = not (show and rec.add_pin)


def on_active_changed(context):
    settings = context.scene.esp
    if not (0 <= settings.active_cut < len(settings.cuts)):
        return
    rec = settings.cuts[settings.active_cut]
    col = bpy.data.collections.get(PLAN_COLLECTION)
    if col is None:
        return
    for obj in col.objects:
        if obj is None:
            continue
        kind = obj.get("esp_preview")
        if kind in ('pin', 'surface'):
            obj.color = ORANGE if kind == 'pin' else GREEN
    for obj in record_objects(rec):
        obj.color = (1.0, 0.85, 0.2, 0.9) if obj.get("esp_preview") == 'pin' else (0.5, 1.0, 0.55, 0.5)


def remove_record(context, index):
    settings = context.scene.esp
    if not (0 <= index < len(settings.cuts)):
        return
    rec = settings.cuts[index]
    for obj in record_objects(rec):
        mesh_utils.remove_object(obj)
    settings.cuts.remove(index)
    settings.active_cut = min(index, len(settings.cuts) - 1)


def remove_all_records(context):
    settings = context.scene.esp
    while len(settings.cuts):
        remove_record(context, len(settings.cuts) - 1)
    col = bpy.data.collections.get(PLAN_COLLECTION)
    if col is not None:
        for obj in list(col.objects):
            mesh_utils.remove_object(obj)
        bpy.data.collections.remove(col)
    settings.active_cut = -1


def set_plan_hidden(context, hidden):
    col = bpy.data.collections.get(PLAN_COLLECTION)
    if col is not None:
        col.hide_viewport = hidden


def record_spec(context, rec, settings, remesh=True):
    apply_fit(context, rec)
    contacts = []
    shape, custom = connectors.resolve_shape(rec.shape)
    for i in range(contact_count(rec)):
        sobj = bpy.data.objects.get(_contact_attr(rec, "surface", i))
        if sobj is None:
            raise cutting.CutError(f"Preview surface of '{rec.name}' is missing")
        verts, faces = surface_world_patch(sobj)
        pin = bpy.data.objects.get(_contact_attr(rec, "pin", i))
        pm = pin.matrix_basis.copy() if (rec.add_pin and pin is not None) else None
        contacts.append(cutting.ContactSpec(verts, faces, rec.add_pin, pm, shape, custom))
    u = mm(context)
    return cutting.CutSpec(
        contacts=contacts,
        gap=rec.cut_gap_mm * u,
        clearance=rec.clearance_mm * u,
        tip_extra=(rec.tip_extra_mm * u) if rec.asymmetric else 0.0,
        pin_side=rec.pin_side,
        solver=pref(context, "solver", 'AUTO'),
        remesh=remesh and settings.remesh_enable,
        remesh_voxel=settings.remesh_voxel_mm * u,
        remesh_adaptivity=settings.remesh_adaptivity,
        remesh_smooth=settings.remesh_smooth,
    )


def quick_spec(context, target, contacts):
    """CutSpec for Quick mode straight from the tool output and the scene defaults."""
    settings = context.scene.esp
    apply_fit(context, settings)
    shape, custom = connectors.resolve_shape(settings.shape)
    specs = []
    for data in contacts:
        pm = None
        if settings.add_pin:
            center, normal, inscribed = contact_frame(
                context, target, data.verts, data.faces, data.hit, data.through, data.center_hint
            )
            w, h = contact_size_bu(context, settings, inscribed)
            pm = connectors.connector_matrix(center, cutting.protrude_direction(normal, settings.pin_side), w, h)
        specs.append(cutting.ContactSpec(data.verts, data.faces, settings.add_pin, pm, shape, custom))
    u = mm(context)
    return cutting.CutSpec(
        contacts=specs,
        gap=settings.cut_gap_mm * u,
        clearance=settings.clearance_mm * u,
        tip_extra=(settings.tip_extra_mm * u) if settings.asymmetric else 0.0,
        pin_side=settings.pin_side,
        solver=pref(context, "solver", 'AUTO'),
    )


# ----------------------------------------------------------------------------
# follow moved cut planes (G/R/S on the preview) -> re-place the pin
# ----------------------------------------------------------------------------
_dirty = set()


def _refresh_dirty():
    global _dirty
    names = list(_dirty)
    _dirty = set()
    scene = bpy.context.scene
    if scene is None:
        return None
    for rec in scene.esp.cuts:
        if rec.surface_a in names or rec.surface_b in names:
            try:
                refresh_record_frames(bpy.context, rec)
            except Exception:
                pass
    return None


@persistent
def depsgraph_handler(scene, depsgraph):
    settings = getattr(scene, "esp", None)
    if settings is None or not len(settings.cuts):
        return
    changed = False
    for rec in settings.cuts:
        for name in (rec.surface_a, rec.surface_b):
            if not name:
                continue
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            cur = flat(obj.matrix_basis)
            old = obj.get("esp_mw")
            if old is None or any(abs(a - b) > 1e-6 for a, b in zip(cur, old)):
                obj["esp_mw"] = cur
                if old is not None:
                    _dirty.add(name)
                    changed = True
    if changed and not bpy.app.timers.is_registered(_refresh_dirty):
        bpy.app.timers.register(_refresh_dirty, first_interval=0.05)


def register():
    if depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_handler)


def unregister():
    if depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_handler)
