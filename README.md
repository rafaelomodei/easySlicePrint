# EasySlice Print

**Slice. Join. Print.** — a free, open-source Blender add-on that splits 3D models into
printable parts, adds matching **pins and sockets**, and exports the parts for resin or FDM printing.

> Português: veja [README.pt-BR.md](README.pt-BR.md)

[![CI](https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml/badge.svg)](https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/rafaelomodei/easySlicePrint?include_prereleases)](https://github.com/rafaelomodei/easySlicePrint/releases)
![Blender 4.2 – 5.2](https://img.shields.io/badge/Blender-4.2%20%E2%80%93%205.2-orange)
![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-Contributor%20Covenant%202.1-purple)](CODE_OF_CONDUCT.md)

## Features

| | |
|---|---|
| **Plane Cut** | drag a line in the viewport → flat cut through the model |
| **Curve Cut** | draw a curved line over the model → the cut follows the line through the model |
| **Freehand Cut** | draw a closed loop *around* the model surface (orbit while drawing) → the loop is filled and used as the cut surface (necks, wrists, anything a plane can't reach) |
| **Two Contacts / Base Split** | two contacts cut as one operation (e.g. both feet on a base), each with its own connector |
| **Quick Cut mode** | immediate final parts, no history |
| **Plan mode** | non-destructive: plan several cuts, edit/disable/remove them, move the cut planes and connectors, **Build** when ready, **Back to Plan** to keep editing, **Approve** to finish. The original model is never modified |
| **Connectors** | automatic pin + socket: Cylinder, Tapered, Hexagon, Box or **custom meshes** from your own connector library; size presets or explicit width/height; clearance; asymmetric tip (deeper socket); choose which side carries the pin; move/rotate/scale the connector freely |
| **Cut Gap (kerf)** | material removed along the cut so parts don't touch |
| **Remesh** | optional voxel remesh of the built parts |
| **Exploded view** | move the parts apart to inspect the connectors, collapse back |
| **Export** | one file per part — **STL, OBJ, FBX** — to a folder, in millimetres |

Tested headless on Blender 4.2.23 LTS and 5.2.1 LTS (CI runs both). Works on Windows, macOS and Linux.

## Install

1. Download `easy_slice_print-<version>.zip` from the releases (or build it, see below).
2. Blender → *Edit → Preferences → Add-ons → ⌄ (top right) → Install from Disk…* → pick the zip.
3. Enable **EasySlice Print**. The panel lives in the 3D Viewport sidebar (`N`) → **EasySlice** tab.

## Quick start

1. Use a **millimetre scene** (Scene Properties → Units → Unit Scale `0.001`, Length `Millimeters`)
   or set *Preferences → EasySlice → Units → "1 unit = 1 mm"*.
2. Select a **closed, manifold** mesh. Apply scale and rotation (`Ctrl+A`). Use *Check Mesh* (✓ icon) if unsure.
3. Pick **Quick Cut** or **Plan Mode**.
4. Click **Plane**, **Curve** or **Freehand** and draw in the viewport:
   * Plane: drag a line across the model (or click, click). `Esc` cancels.
   * Curve: draw a line over the model that crosses the whole silhouette.
   * Freehand: draw on the surface around the model; orbit with `MMB` between strokes;
     return to the green start point (or press `Enter`) to close the loop.
5. Connector panel: shape, size, pin side, cut gap, clearance.
6. **Plan mode**: select a cut in the list to edit it — *Edit Cut Surface* (G/R/S for planes, drag
   points for curves), *Select Connector* then G/R/S, *Reset*, *Swap* the pin side. Untick **Ready** to
   leave a cut out of the build, the eye hides its preview, ✕ deletes it.
7. **Build** → parts appear in `ESP_Built_<name>`. **Back to Plan** to change anything, **Approve** to finish.
8. **Exploded View** to check the fit, **Export** to write the files.

Connector clearance is printer specific (0.15–0.4 mm is typical). Test print a small piece first.

### Custom connectors

Press the library icon next to *Shape*. An `ESP_Connectors` collection is created with the
built-in templates. Add any mesh object to it and it shows up in the Shape menu. Convention: the
mesh fits `x, y ∈ [-0.5, 0.5]`, `z ∈ [-1, 1]`; `z = 0` is the cut surface and `+z` is the tip that goes
into the socket. Connectors must be rigid (no articulated joints).

## Requirements & limitations

* Blender 4.2 – 5.2. Closed manifold meshes only; open, self-intersecting or broken meshes give wrong booleans.
* Processing time depends on polygon count and the boolean solver (Preferences). The *Manifold* solver
  (Blender 4.5+) is used automatically when available, *Exact* as fallback.
* Not a printability analyser — wall thickness, orientation, supports and tolerances are up to you.

## Development

```bash
# run the headless tests (needs a Blender binary on PATH or in $BLENDER)
BLENDER=/path/to/blender scripts/run_tests.sh

# build the installable zip into dist/
BLENDER=/path/to/blender scripts/build.sh
```

Code layout: `easy_slice_print/core/` is pure geometry (patches → kerf slab → booleans → connectors),
`plan.py` holds the non-destructive records and previews, `ops_tools.py` the modal drawing tools,
`ops_plan.py` build/approve, `ui.py` the panels. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
and [docs/FEATURES.md](docs/FEATURES.md).

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
Security issues: see [SECURITY.md](SECURITY.md).

## License

**PolyForm Noncommercial License 1.0.0** — free to use, study, modify and share, including
contributing back, **but not for commercial purposes** (no selling, no bundling in paid products, no
commercial services). See [LICENSE](LICENSE).

> Note: Blender's official Extensions platform only accepts GPL-compatible licenses, so this add-on is
> distributed here (GitHub releases / Install from Disk) rather than on extensions.blender.org.

EasySlice Print is an independent project. It is not affiliated with, endorsed by or derived from any
commercial add-on; no third-party code or assets are included.
