#!/usr/bin/env bash
# Runs the headless test-suite. Set BLENDER to your blender binary if it is not on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER:-blender}"
"$BLENDER" -b --factory-startup --python "$HERE/tests/test_core.py" -- "$@"
"$BLENDER" -b --factory-startup --python "$HERE/tests/test_addon.py" -- "$@"
