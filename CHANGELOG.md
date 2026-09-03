# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **The full demo is on the README and the site.** A carousel horse gets plane cuts across its
  legs and a curve cut over its head, is built into parts and pulled apart — the shot the README
  cover and the site hero were waiting for. It replaces the curve-cut GIF as the cover, and the
  plane-cut-with-planning clip fills the site's Plane Cut section, leaving four placeholder slots.

## [0.3.2-alpha] - 2026-09-03

### Added
- **First real demo footage.** A Curve cut in Quick Cut mode — a line drawn over a carousel horse's
  tail, which comes off as its own printable part, connector included — now opens both READMEs as a
  GIF and plays in the website hero and Curve Cut section as a video. The raw captures stay out of
  git (`/media/` is ignored); `docs/media/README.md` lists what is still to record and the ffmpeg
  recipe that derives the committed files from a capture.

### Fixed
- **Quick Cut with the Plane tool left the model uncut.** On anything but a simple shape the cut
  ran its full time, named two parts and created the backup, but the model came out whole — the
  horse it was reported on kept all 306k of its vertices in one part. The tool copied the model's
  cross section into the cut and dropped the quad that came with it, so the boolean subtracted the
  section itself; its rim lies on the surface tangentially and the exact solver returns the mesh
  barely touched. A cube still worked, which is why it survived 0.3.1-alpha. Plan Mode was never
  affected: it re-sections on the preview and picks the quad up there.

## [0.3.1-alpha] - 2026-09-03

### Added
- **The project is labelled alpha.** README, website, docs and the sidebar panel now say the
  add-on is under active development: bugs are expected, and the UI and plan data still change
  between releases.

### Fixed
- **Cutting an approved part cut the original model again.** After Approve, drawing a new cut on
  one of the finished parts and building rebuilt from the model as it was before *any* cut: every
  approved cut was thrown away and the plan sliced the untouched original. A part remembers the
  model it came from, and the plan was rooted at that memory instead of at the part under the
  cursor. The object you draw on is now the plan's source, so a second round of cuts starts from
  the geometry you already have. A plan can also carry cuts on several parts at once: each part a
  cut was drawn on is built from itself, its pieces are named after it (`Part_001_PART_001`), and
  Back to Plan brings all of them back.
- **The sidebar showed the wrong version.** The panel had `0.1.0` hard-coded while the extension
  shipped as 0.2.3. The version is now read from `blender_manifest.toml` at runtime, so what the
  panel shows is always the version Blender installed; a test keeps the two in step.

### Changed
- **A Plane Cut's surface is now the model's own cross section.** It used to be a rectangle built
  around the mouse stroke: as wide as the line you dragged, and as deep as every ray under that
  line happened to reach. Because everyone overshoots the stroke to be sure of crossing the part,
  the samples past the target hit whatever stood behind it, and the patch grew to the size of the
  whole figure - a huge rectangle reaching into places that had nothing to do with the cut, which
  could slice a second limb or fail to separate anything at all. The line now only picks the
  plane: the model is bisected by it, the resulting loops are filled, and the region the line
  actually crossed is used as the cut surface. That surface is the area the print is really cut
  through, so the preview matches the printed face, a hollow part sections into an annulus, the
  connector is sized from the true inscribed circle, and drawing across one leg leaves the other
  one alone. Moving or rotating the preview in Plan Mode takes the section again where it lands.
  A mesh that cannot be sectioned (open or non manifold) still falls back to the old rectangle.
- *Surface Margin* no longer applies to Plane Cuts - a cross section already covers exactly the
  area being cut. It still controls how far Curve and Freehand surfaces reach past the stroke.
- **The line now says which regions to cut.** A first pass kept the single region nearest the
  middle of the stroke, which is right on a figure with one limb in the way and wrong on
  everything else: a plane through a saint's chest also crosses the sword and the wings, and
  leaving those uncut means the halves stay joined through them and the cut reports that it split
  nothing. Every region whose span along the drawn direction overlaps the stroke is now cut - drag
  across one leg and the other is still spared, drag across the whole figure and everything on
  the plane comes with it.

- **Curve cuts follow the model too.** A curve used to be extruded to one depth for its whole
  length, taken from the furthest ray hit anywhere under the stroke - so a line drawn across a
  figure's near arm reached through the body behind it, and the preview was a slab rather than
  the face that gets printed. Depth is now measured under every column of the ribbon: the surface
  runs exactly as deep as the material beneath each point, only through the run of material the
  stroke is standing on, and a column with nothing under it is dropped so a stroke running off the
  end of a limb stops at the limb. As with plane cuts, what the boolean subtracts is the same
  ribbon at one flat depth reaching past the model, so its rim stays in free space.
- **The connector is measured from the cut face on all three tools.** Plane, curve and freehand
  cuts all size and place the pin with the largest circle that fits inside the real cut face. A
  freehand loop is drawn a hair outside the model so its rim clears the surface; that clearance
  is taken back off the pin, so the pin matches the limb rather than the loop.

### Fixed
- **Plane cuts that removed material without separating the part.** The boolean was being handed
  the cross section itself, whose rim runs along the model's surface for its whole length; an
  exact boolean asked to resolve that many near tangent intersections returns slivers, or a part
  that never came apart. On a sweep of 23 cut heights through a subdivided Suzanne the section
  cutter failed 3 times where the old oversized rectangle failed none, and pushing the rim
  further out made it worse, not better, because offsetting a concave outline folds it over
  itself. The boolean now gets a quad that runs out past the model and only pulls in where a
  region has to be spared, stopping in the empty gap between the two. Same result - the extra
  area covers nothing but air - and 23 of 23 on the same sweep. The preview and the connector
  still use the real section.
- **Connectors that ended up tiny and out at the edge of the part.** The pin's position and size
  came from marching rays out of a guessed centre and taking the middle of their bounding box,
  which on any cut face that is not roughly convex walks the pin out of the thick part and into a
  thin appendage - a plane through a figure's chest catches the sword too, and the pin came out a
  3 mm stub on the blade. The pin is now the largest circle that actually fits inside the cut
  face, so it sits where the material is thickest and is as wide as that material allows. On a
  hollow part it lands in the wall instead of the hole.
- **"Make the cut cross the whole part" on cuts that already crossed it.** When a cut removes
  material but the part stays in one piece, the message now says how many other regions the
  plane crosses that the line did not run across - the wing, the base, the sword the halves are
  still hanging from - instead of repeating advice that no longer applies.

## [0.2.3] - 2026-08-29

### Fixed
- **Blender no longer looks frozen while cutting**: cuts and plan builds used to run in one blocking
  call, so the desktop got no answer to its "is this window alive?" ping and offered *Wait / Force
  Quit* - on GNOME that happens after only 5 seconds, and a single cut on a dense model already takes
  about that long. The cut pipeline now runs one step at a time, handing control back to Blender
  between the booleans, so the window stays responsive. The status bar shows what the cut is doing
  (`EasySlice Cut: carving the socket... (3.2s)`) and **Esc** cancels a build in progress without
  leaving stray meshes behind.

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

[Unreleased]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.3.2-alpha...HEAD
[0.3.2-alpha]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.3.1-alpha...v0.3.2-alpha
[0.3.1-alpha]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.3...v0.3.1-alpha
[0.2.3]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rafaelomodei/easySlicePrint/releases/tag/v0.1.0
