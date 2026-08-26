# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rafaelomodei/easySlicePrint/releases/tag/v0.1.0
