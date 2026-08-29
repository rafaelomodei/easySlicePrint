# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.2] - 2026-08-28

### Added
- **Printer profile**: *Printer Clearance* in the add-on preferences - how much room your printer
  needs between a pin and its socket, on each side, for the printed parts to go together. It
  belongs to the printer and the filament rather than to the model, so it is set once and every
  cut in every file uses it. Defaults to 0.1 mm, which suits most FDM printers.
- **Fit** preset on every cut: *Press* (0.5x), *Snug* (1x, the default), *Easy* (1.5x), *Loose*
  (2.5x) or *Custom*. It scales the printer clearance, so you pick how tight the joint should feel
  instead of guessing a number. The panel now spells out the consequence - how much wider the
  socket comes out than the pin.

### Changed
- The connector gap now defaults to 0.10 mm per side (0.20 mm on the diameter) instead of 0.30 mm
  per side (0.60 mm on the diameter). The old default left a printed pin visibly loose: the value
  has always been applied to each side, so it opens the socket by twice itself, and 0.60 mm on the
  diameter is well past the 0.10-0.30 mm range these joints are normally printed with.
- *Clearance* is now called *Gap per Side*, because that is what it is.
- Opening a file made with 0.2.x: the cuts in it keep their stored gap until a connector setting is
  touched, at which point the Fit preset (Snug) takes over and writes the printer value. Set Fit to
  *Custom* on a cut you had tuned by hand to keep its own number.

## [0.2.1] - 2026-08-27

### Added
- *Surface Detail* setting (default 3): how many spline samples are built between two control
  points. The cut surface is generated at that resolution instead of at the resolution of the
  editable control points. Set it to 1 for the old raw polyline.
- The pointer now says which tool is running: a blade over the Plane Cut, and the pencil (paint
  brush) cursor while a Curve or Freehand stroke is being drawn and while control points are being
  edited. The normal pointer comes back when the tool ends, whether it was confirmed or cancelled.

### Changed
- Curve and Freehand cuts now produce a smooth cut surface. The control points are run through a
  centripetal Catmull-Rom spline (`surfaces.spline_polyline`) before the ribbon is extruded, and a
  freehand loop is spanned by a relaxed membrane (`surfaces.membrane_fill`) instead of an n-gon
  triangulation or a centroid fan: concentric rings are dropped inside the loop and every interior
  vertex is iterated onto the average of its neighbours with the boundary pinned. The fixed point
  of that iteration is the minimal surface through the drawn loop - dead flat for a loop drawn
  from a single viewpoint, a smooth saddle for a loop drawn while orbiting. Printed faces come out
  smooth and mate properly, instead of showing the facets and the centre spike of the old fill.
- *Smoothing* now also applies to the Curve Cut stroke, which was hard-coded to a single light
  pass. It takes the shake and the model's own triangle facets out of the drawn line.
- Dragging a point in *Edit Cut Surface* rebuilds the preview at half resolution while the mouse
  is down and at full resolution on release, so the editor stays responsive on dense surfaces.

## [0.2.0] - 2026-08-26

### Added
- Freehand Cut: orbit between strokes to mark the far side of the model. The loop is kept in
  world space, the stretch running behind the model is drawn faded and the jump between two
  strokes dimmed, `Ctrl+Z` / `Backspace` undoes the last stroke and `Enter` / `C` close the
  loop from any angle.
- `scripts/build_zip.py`: packs the extension zip without Blender; `scripts/build.sh` falls
  back to it when Blender is not on the PATH.

### Changed
- Generated cut surfaces now carry their own origin, placed at the centre of the surface, so `R`
  and `S` in *Edit Cut Surface* pivot on the surface instead of on a point out in the scene. New
  *Surface Origin* setting switches it to the origin of the object being cut when several cut
  surfaces should share one pivot.
- Cut surfaces are sized to what was drawn instead of to the model's bounding diagonal. A Plane
  cut is now as wide as the line you dragged and only as deep as the model reaches underneath it
  (rays are marched through every crossing under the stroke); a Curve cut spans the same measured
  depth and reaches just past the ends of the stroke. Previously both were built at 1.3x / 0.5x the
  bounding diagonal and centred on the model, so a short line across a wrist also sliced everything
  else lying in that plane.
- New *Surface Margin* setting (default 6%) controls how far a cut surface reaches past the drawn
  region; raise it if a cut reports that it did not split the part.

### Fixed
- Freehand Cut no longer snaps the loop closed on a start point hidden behind the model after
  orbiting - auto-close now requires that point to be visible.
- Loops drawn across several viewpoints are filled with a centroid fan instead of a degenerate
  n-gon triangulation (`surfaces.loop_patch`).
- Alt+LMB goes to the viewport when *Emulate 3 Button Mouse* is on, so it orbits instead of drawing.
- Plane and Curve cuts discard the stroke with a warning when the view is orbited mid-stroke,
  instead of building a cut out of two different viewpoints.
- Editing the control points of a rotated Curve surface rebuilt the ribbon along a world-space
  view direction; the direction is now taken into the object's local frame.

## [0.1.0] - 2026-08-25

### Added
- Plane, Curve and Freehand cut tools (modal viewport tools with GPU overlay).
- Two contacts / base split (both contacts cut as one operation, each with its own connector).
- Quick Cut mode (immediate parts) and Plan Mode (non-destructive records, previews, editable
  surfaces and connectors, Build / Back to Plan / Approve / Clear).
- Pin + socket connectors: Cylinder, Tapered, Hexagon, Box and a custom connector library;
  size presets or explicit width/height; clearance; asymmetric tip; pin side swap; manual transform.
- Cut gap (kerf), Keep Original, Skip Failed Cuts, optional voxel remesh.
- Exploded view and one-click STL / OBJ / FBX export in millimetres.
- Headless test-suite and CI for Blender 4.2 LTS and 5.2 LTS.
- Released as free software under the GNU GPL v3.0 or later.

[Unreleased]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rafaelomodei/easySlicePrint/releases/tag/v0.1.0
