# Contributing to EasySlice Print

Thanks for helping! EasySlice Print is free and open source under the
[PolyForm Noncommercial License 1.0.0](LICENSE). By contributing you agree that your contribution
is licensed under the same terms, and to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to help

* **Report bugs** with a reproducible `.blend` (issue template: *Bug report*).
* **Test prints**: share which clearance / gap values work on your printer — that knowledge goes
  into the docs.
* **Code**: pick an issue labelled `good first issue` or `help wanted`, or propose something in
  a *Feature request* first for larger changes.
* **Docs & translations**: the UI is English only for now; README translations are welcome.

## Development setup

1. Install Blender 4.2 LTS or newer (5.2 LTS recommended). No other dependencies.
2. Clone the repo and link the add-on into your Blender:
   ```bash
   scripts/dev_link.sh 5.2      # symlinks easy_slice_print/ into the user extensions folder
   ```
   Enable **EasySlice Print** in *Edit → Preferences → Add-ons*. After editing code use
   *System → Reload Scripts* (`F3`) or restart Blender.
3. Run the headless tests (Blender on PATH or `BLENDER=/path/to/blender`):
   ```bash
   BLENDER=/path/to/blender scripts/run_tests.sh
   ```
4. Lint / format with [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`):
   ```bash
   ruff check . && ruff format .
   ```
   or install the hooks once with `pre-commit install`.
5. Build the installable zip with `scripts/build.sh` (uses Blender's own extension builder + validator).

## Pull requests

* Branch from `main`, keep PRs focused, describe **why** in the description and link the issue.
* CI must be green: ruff, headless tests on Blender 4.2 and 5.2, extension build.
* Add or extend a test for any geometry behaviour (`tests/test_core.py`) or workflow
  (`tests/test_addon.py`). Panels are drawn in tests too, so property typos are caught.
* Add a line under **Unreleased** in `CHANGELOG.md` for user-visible changes.
* Commit messages: short imperative subject (`Add hex connector keying`), body explains the why.

## Code guidelines

* `easy_slice_print/core/` is pure geometry: no UI code, no `bpy.context`, no `bpy.ops` except
  the mesh-separate helper. Everything it needs is passed in.
* User-facing lengths are **millimetres**; convert once at the boundary with `plan.mm(context)`.
* Operators are undoable (`bl_options = {'REGISTER', 'UNDO'}`) and report clear messages.
* Keep Blender 4.2 compatibility: guard newer API with `hasattr` / `try` (see `_material`,
  `available_solvers`).
* **Originality**: features may be inspired by the wider 3D-printing ecosystem, but do not copy
  code, UI assets or text from other add-ons.

## Releasing (maintainers)

1. Bump `version` in `easy_slice_print/blender_manifest.toml` and `VERSION` in `ui.py`.
2. Move the *Unreleased* notes in `CHANGELOG.md` to a new version heading with the date.
3. Commit, tag `vX.Y.Z` and push the tag — the *Release* workflow tests, builds and attaches the
   zip to a GitHub release.

## Roadmap ideas

* Automatic cut suggestions from the print-bed size.
* Alignment keys for round connectors, dovetail / snap-fit connectors.
* Thin-wall warning around sockets.
* Per-part orientation on export.
