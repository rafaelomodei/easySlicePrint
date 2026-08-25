#!/usr/bin/env bash
# Builds the installable extension zip into dist/ using Blender's own extension builder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER:-blender}"
mkdir -p "$HERE/dist"
"$BLENDER" -b --command extension build --source-dir "$HERE/easy_slice_print" --output-dir "$HERE/dist"
"$BLENDER" -b --command extension validate "$HERE"/dist/*.zip
ls -la "$HERE/dist"
