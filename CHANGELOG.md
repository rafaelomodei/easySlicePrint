# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/rafaelomodei/easySlicePrint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rafaelomodei/easySlicePrint/releases/tag/v0.1.0
