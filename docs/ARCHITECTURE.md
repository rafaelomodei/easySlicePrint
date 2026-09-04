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
   * plane: the model's own cross section on the drawn plane. The mesh is bisected by the
     plane, the resulting loops are filled (a hollow part sections into an annulus) and the fill
     is split into connected islands - one per region the plane crosses. Every island whose span
     along the drawn direction overlaps the stroke is kept: the plane contains the view
     direction, so on screen it collapses onto the line, and "the regions the line ran across" is
     literally an interval overlap (`section.plane_section`, `plan.straight_section`). The line
     picks the plane and the regions; it has no say in how big the surface is.

     What the boolean subtracts is **not** that section. A section's rim runs along the model's
     surface for its whole length, and an exact boolean asked to resolve that many near tangent
     intersections comes back with slivers or with a part that never separated - measurably
     worse than the oversized quad it replaced, and worse still as the rim is pushed further out,
     because offsetting a concave outline folds it over itself. So the cutter is a quad
     (`section.clip_rect`): it runs out past the model on every side with nothing to protect and
     pulls in only where a region has to be spared, stopping in the middle of the empty gap. Same
     result as subtracting the section - the extra area covers nothing but air - with a rim the
     solver can resolve. Only when regions are interleaved along both axes, and no quad
     separates them, does the section itself go to the boolean.

     A moved or rotated preview re-sections the model and rebuilds the quad (`plan.rebuilt_section`,
     driven from `plan.refresh_record_frames`). If the mesh cannot be sectioned at all - open or
     non manifold - the tool falls back to the old quad around the stroke (`surfaces.rect_patch`,
     `CutToolBase.model_span`);
   * curve: the stroke (resampled to *Control Points*, then splined to *Surface Detail* samples
     per segment) extruded along the view direction and extended past its ends by *Surface
     Margin* (`surfaces.ribbon_patch`). Depth is measured per column: rays are marched under
     every splined sample, and `section.band_around` - the one dimensional `clip_rect` - picks
     the run of material the stroke is standing on and widens it half way into the empty gaps
     beside it. The preview then gives each column its own span so the surface follows the
     silhouette (a column with nothing under it is dropped), while the boolean gets the same
     ribbon at one flat depth, past the model on both sides (`plan.ribbon_surfaces`). One depth
     range for the whole ribbon, taken from the furthest hit anywhere under the stroke, is what
     used to make a curve across a figure's near arm reach through the body behind it;
   * freehand: the loop drawn on the surface (over as many strokes and viewpoints as needed —
     samples are stored in world space, so orbiting between strokes keeps the loop), pushed
     outward along the surface normals - which is also what keeps its rim off the model, so it
     needs no separate cutter - splined, and spanned by a relaxed
     membrane (`surfaces.loop_patch` → `surfaces.membrane_fill`: concentric rings closed
     by a centre vertex, then the interior vertices are iterated onto the average of their
     neighbours with the boundary pinned). The fixed point of that iteration is the discrete
     minimal surface through the drawn loop: dead flat for a loop drawn from one viewpoint,
     a smooth saddle for a loop that wraps around the model. Nothing but a straight polyline is
     ever handed to the boolean, which is what keeps the printed cut face from showing facets.

     Unlike a curve, a freehand loop is **not** resampled to *Control Points* and is not
     smoothed by default: it is the tool for tracing a detail, so its control points are the
     points that were drawn, however many that is (`loop_smoothing` defaults to 0, and
     `surfaces.loop_boundary` spends what is left of its sample budget on the spline instead of
     splining and then decimating). What is left between the stroke and the cut face is the
     outward push, `plan.loop_margin` — every millimetre of it moves the cut off the traced
     line, so it is kept as small as the *classification* in step 3 tolerates, not as small as
     the boolean does: a loop at a hip junction separates cleanly at 0.8 mm but every loose
     piece then votes to the same side of a membrane that local.
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
   part. The radial clearance is resolved from the printer profile by the cut's Fit preset
   (`plan.apply_fit`), and is a gap per side: the socket opens up by twice it.
   `pin part ∪ pin`, `socket part − pin(+clearance radially, +tip extra axially)`.
5. **Remesh** (optional) and object creation in `ESP_Built_<name>`.

The same estimate is used for previews and builds, so what you see in Plan mode is what gets built.

## Plan mode data

`Scene.esp.cuts[]` (`ESP_CutRecord`) stores per cut: type, target object, enabled/visible flags,
names of the preview objects (`ESP_Surface_*`, `ESP_Pin_*` in `_ESP_Plan`), the automatic pin
matrix, estimated centre/normal/inscribed diameter per contact, an anchor point, and its own
connector settings. Curve/freehand control points live on the surface object as custom properties
(local space) and the mesh is rebuilt from them when edited.

A generated cut surface carries its own origin: the patch is produced in world space, then stored
local to `plan.surface_origin_point` (the patch's median point by default, the target object's
origin when *Surface Origin* says so) with the offset as the object's `matrix_world`. That is what
makes `R` / `S` on a cut surface pivot on the surface itself. Everything downstream reads it back
through `plan.surface_world_patch` (`matrix_basis @ v.co`), so moved, rotated and scaled surfaces
build exactly as previewed.

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
