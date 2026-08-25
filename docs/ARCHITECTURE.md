# Architecture

```
easy_slice_print/
├── blender_manifest.toml   extension manifest (Blender 4.2+)
├── __init__.py             registers the modules below
├── props.py                Scene.esp settings + ESP_CutRecord (planned cut)
├── prefs.py                add-on preferences (solver, units, mesh check)
├── plan.py                 records ↔ preview objects ↔ CutSpec; backup/built collections
├── ops_tools.py            modal cut tools (plane / curve / freehand) + Quick mode execution
├── ops_plan.py             plan operators: new/delete/swap/reset, surface point editor, build/back/approve/clear
├── ops_misc.py             explode/collapse, export, connector library, check mesh
├── ui.py                   sidebar panels + UIList
├── draw.py                 GPU overlay helpers
└── core/                   pure geometry, no UI, no bpy.context
    ├── units.py            mm ↔ Blender units
    ├── mesh_utils.py       temp objects, boolean (modifier based), loose parts, measurements, ray helpers
    ├── surfaces.py         cut patches (plane / ribbon / loop), polyline utils, kerf slab
    ├── connectors.py       unit connector meshes, frames, library collection
    └── cutting.py          CutSpec → split → connectors → remesh → result objects
```

## The cut pipeline (`core/cutting.py`)

1. **Patch** — every tool produces an open mesh in world space:
   * plane: one big quad;
   * curve: the stroke (resampled to *Control Points*) extruded along the view direction, extended
     past the model on both ends (`surfaces.ribbon_patch`);
   * freehand: the loop drawn on the surface, pushed a little outward along the surface normals,
     smoothed, resampled, filled with triangles (`surfaces.loop_patch`).
2. **Kerf slab** — the patch is thickened by *Cut Gap* along its vertex normals into a closed
   solid (`surfaces.slab_from_patch`).
3. **Split** — `model − slab` (Boolean modifier, *Manifold* solver when available, *Exact*
   fallback), then loose parts are separated (C-side `mesh.separate`) and classified by the sign of
   their centroid against the first patch (BVH nearest point + normal). Side **A** is the + side.
   Parts on the same side are joined, so a plane through both arms still gives exactly two objects.
   Two-contact cuts subtract both slabs before separating.
4. **Connector** — the pin frame comes from `estimate_pin_frame`: the point where the stroke hit the
   model and the exit point along the view ray give a first centre; 16 in-plane rays refine it to the
   middle of the cross-section and the shortest ray gives the inscribed diameter (used by the size
   presets). Pin = unit mesh × `Matrix(loc, rot, scale(w, w, h))` with `+z` pointing into the socket
   part. `pin part ∪ pin`, `socket part − pin(+clearance radially, +tip extra axially)`.
5. **Remesh** (optional) and object creation in `ESP_Built_<name>`.

The same estimate is used for previews and builds, so what you see in Plan mode is what gets built.

## Plan mode data

`Scene.esp.cuts[]` (`ESP_CutRecord`) stores per cut: type, target object, enabled/visible flags,
names of the preview objects (`ESP_Surface_*`, `ESP_Pin_*` in `_ESP_Plan`), the automatic pin
matrix, estimated centre/normal/inscribed diameter per contact, an anchor point, and its own
connector settings. Curve/freehand control points live on the surface object as custom properties
(local space) and the mesh is rebuilt from them when edited.

User edits of the pin are kept as a *delta* in the pin's unscaled local frame
(`plan.user_delta`), so changing the size preset, the shape or the pin side keeps the offset.
A `depsgraph_update_post` handler notices moved cut planes and re-estimates the pin (deferred to a
timer to avoid recursion).

**Build** always rebuilds from the original: it removes the previous build, restores the source from
`ESP_Backup`, applies every *Ready* cut in list order (each cut picks the part closest to its
anchor), renumbers the parts, hides the source again and hides the plan previews. **Back to Plan**
undoes exactly that; **Approve** clears the plan and keeps the parts.

## Testing

`tests/test_core.py` exercises the geometry pipeline (straight/ribbon/loop/two-contact cuts,
custom connectors, remesh) and asserts closed-manifold results. `tests/test_addon.py` registers
the add-on, runs the full plan workflow through the real operators (build, rebuild, explode,
export STL/OBJ/FBX, back to plan, approve), Quick mode, and draws every panel with a recording
layout to catch property typos. Both run headless: `scripts/run_tests.sh`.
