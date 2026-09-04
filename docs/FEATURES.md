# Feature map

EasySlice Print targets the workflow professional model cutters expect (studied from public
material about commercial cutting add-ons — landing pages, docs and tutorial videos). Everything
below is an original implementation; nothing was copied.

> **Alpha.** The add-on is under active development: every feature below is implemented and
> covered by the headless tests, but bugs are expected, and both the UI and the plan data stored
> in the `.blend` still change between releases.

| Workflow need | EasySlice Print | Where |
|---|---|---|
| Two ways of working: immediate vs. planned | **Quick Cut** / **Plan Mode** toggle | `ESP_PT_main` |
| Straight cut drawn in the viewport | **Plane Cut** (drag a line; plane contains the view direction) | `ops_tools.ESP_OT_cut_straight` |
| Cut only the regions that were marked | a Plane cut's surface is the model's own cross section on the drawn plane, over every region the line ran across and only those - draw across one leg and the other is untouched, drag across the whole figure and the sword comes too | `section.plane_section` |
| A curve that stops where the model does | every column of the ribbon runs as deep as the material under it and no further, through the run of material the stroke is standing on - a curve across the near arm leaves the body behind it alone | `plan.ribbon_surfaces`, `section.band_around` |
| Cut surface that is the real printed area | the plane section is filled from the mesh itself, so a hollow part sections into an annulus | `section.plane_section` |
| Connector that actually fits the cut face | on all three tools the pin is the largest circle that fits inside the real cut face, so a face shaped like a chest plus a sword still puts the pin in the chest, and a hollow part puts it in the wall | `section.inscribed_circle` |
| A cut that cannot separate says why | a plane crossing a wing or a base the line missed leaves the halves joined through it; the message names how many regions were left out instead of repeating "cross the whole part" | `cutting.still_joined_message` |
| Curved cut following a drawn line | **Curve Cut** (stroke → ribbon extruded along the view) | `ESP_OT_cut_curved` |
| Cut that wraps around a limb / neck | **Freehand Cut** (closed loop on the surface, loop filled) | `ESP_OT_cut_freehand` |
| Reach the far side of the model while marking | orbit between strokes; the loop is kept in world space, hidden parts drawn faded, auto-close only on a visible start point, `Ctrl+Z` undoes a stroke, `Enter`/`C` close from any angle | `ESP_OT_cut_freehand` |
| Fill a loop drawn across several viewpoints | the loop is spanned by a relaxed membrane (concentric rings, interior smoothed onto the average of its neighbours, boundary pinned) | `surfaces.membrane_fill` |
| Cut faces that print smooth enough to mate | control points are splined and the fill relaxed, so a Curve/Freehand cut face is as smooth as a Plane cut instead of showing the facets of the control polyline | `surfaces.spline_polyline`, `surfaces.loop_patch` |
| Control the stroke smoothing / editable point count / surface resolution | *Smoothing*, *Control Points* and *Surface Detail* (a Curve cut); *Loop Smoothing* and *Surface Detail* for Freehand | `ESP_PT_tools` |
| Trace a detail and have the cut land on it | a freehand loop keeps every point drawn - no resample to *Control Points*, no smoothing unless asked - so the rim runs through the stroke and a traced step survives into the printed face | `ESP_OT_cut_freehand.close_loop` |
| Know which tool has the mouse | the pointer becomes a blade for the Plane Cut and a pencil while drawing a stroke or editing points | `ops_tools.set_cursor` |
| Separate a figure from its base (two contacts at once) | **Two Contacts / Base Split** toggle; both contacts drawn in one go, one record `Base Split NNN` | `settings.two_contact` |
| Automatically start the next cut | **Chain Cuts** | `settings.chain_cuts` |
| Editable list of planned cuts: enable, hide, delete, rename | **Planned Cuts** UIList (Ready ☑, eye, ✕, name) | `ESP_UL_cuts` |
| Draft is cheap, geometry deferred to build | records store only the cut surface + pin transform; booleans run on **Build** | `plan.py`, `ESP_OT_build` |
| Move / rotate / scale a straight cut | **Edit Cut Surface** selects the plane; G/R/S; pin follows (depsgraph handler) | `ESP_OT_edit_surface`, `plan.depsgraph_handler` |
| Cut surface with a usable pivot | generated surfaces get their own origin at the patch centre (*Surface Origin*: Cut Surface / Target Object) | `plan.surface_origin_point` |
| Edit curve/freehand points | point editor modal: drag, Ctrl+LMB add, X delete, G slide whole cut, R reset, Ctrl+Z undo | `ESP_OT_edit_surface` |
| Connector on/off, shape, size, width/height | Connector panel (per next cut or per selected cut; new cuts copy the selected cut's settings) | `ESP_PT_connector` |
| Built-in + custom connector shapes | Cylinder, Tapered, Hexagon, Box + `ESP_Connectors` library (unit-box convention) | `core/connectors.py` |
| Printed parts that actually fit together | *Printer Clearance* set once per printer in the preferences; each cut picks Press / Snug / Easy / Loose / Custom, and the panel shows how much wider the socket comes out | `ESP_Preferences.printer_clearance_mm`, `plan.apply_fit` |
| Clearance, asymmetric tip, tip extra | **Fit & Clearance** sub-panel | `ESP_PT_fit` |
| Pin on side A or B, swap | *Pin Side* + **Swap** | `ESP_OT_swap_pin_side` |
| Move/rotate/scale the pin manually, reset | **Select Connector** (G/R/S) / **Manual Connector Adjust** panel / **Reset** | `ESP_OT_select_pin`, `ESP_PT_pin_adjust`, `ESP_OT_reset_pin` |
| Cut gap / kerf in mm | *Cut Gap* → kerf slab subtracted before splitting | `surfaces.slab_from_patch` |
| Keep the source model | **Keep Original** → hidden in `ESP_Backup` | `plan.move_to_backup` |
| Continue after a failed cut | **Skip Failed Cuts** | `ESP_OT_build` |
| Remesh (draft only) | **Remesh** sub-panel (voxel size, adaptivity, smooth) | `cutting.remesh_mesh` |
| Build, return to draft, approve, delete history | **Build** / **Back to Plan** / **Approve** / **Clear Plan** | `ops_plan.py` |
| Parts land in a collection | `ESP_Built_<name>` with `<name>_PART_001…` (Quick mode: `_UPPER/_LOWER`, `_LEFT/_RIGHT`, `_FRONT/_BACK`) | `cutting.side_labels` |
| Exploded view with distance | **Exploded View** → Explode / Collapse | `ops_misc.py` |
| One-button export STL/OBJ/FBX | **Export** (folder + format, one file per part, millimetres) | `ESP_OT_export` |
| Mesh sanity | **Check Mesh** + warning before cutting (preference) | `ESP_OT_check_mesh` |
| Units in mm | scene unit scale conversion or *1 unit = 1 mm* preference | `core/units.py` |

## Not (yet) covered

* Articulated / movable joints (out of scope: connectors are rigid by design).
* Automatic printability analysis (wall thickness, supports).
* Automatic bed-size based cut suggestions (roadmap).
