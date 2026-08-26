#!/usr/bin/env bash
# Builds the installable extension zip into dist/.
#
# Uses Blender's own extension builder when Blender is on the PATH (it also validates
# the manifest); otherwise falls back to scripts/build_zip.py, which writes the same
# zip layout in pure Python.
#
# Usage: scripts/build.sh          (BLENDER=/path/to/blender to pick a specific build)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER:-blender}"
mkdir -p "$HERE/dist"

# The GPL requires the licence text to travel with the program, so ship a copy
# inside the zip (removed again right after the build - it is not tracked).
cp "$HERE/LICENSE" "$HERE/easy_slice_print/LICENSE"
trap 'rm -f "$HERE/easy_slice_print/LICENSE"' EXIT

if command -v "$BLENDER" >/dev/null 2>&1; then
  "$BLENDER" -b --command extension build --source-dir "$HERE/easy_slice_print" --output-dir "$HERE/dist"
  "$BLENDER" -b --command extension validate "$HERE"/dist/*.zip
else
  echo "Blender not found (set BLENDER=/path/to/blender to use it) - packing with scripts/build_zip.py."
  echo "The zip is installable, but the manifest was not validated by Blender."
  python3 "$HERE/scripts/build_zip.py" "$HERE/easy_slice_print" "$HERE/dist"
fi
ls -la "$HERE/dist"
