#!/usr/bin/env bash
# Symlinks the add-on into Blender's user extensions folder for live development.
# Usage: scripts/dev_link.sh [blender-series]   (default: 5.2)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SERIES="${1:-5.2}"
case "$(uname -s)" in
  Darwin) BASE="$HOME/Library/Application Support/Blender/$SERIES/extensions/user_default" ;;
  Linux)  BASE="${XDG_CONFIG_HOME:-$HOME/.config}/blender/$SERIES/extensions/user_default" ;;
  *)      echo "On Windows link %APPDATA%\\Blender Foundation\\Blender\\$SERIES\\extensions\\user_default\\easy_slice_print to $HERE/easy_slice_print"; exit 0 ;;
esac
mkdir -p "$BASE"
ln -sfn "$HERE/easy_slice_print" "$BASE/easy_slice_print"
echo "Linked $BASE/easy_slice_print -> $HERE/easy_slice_print"
echo "Now enable 'EasySlice Print' in Edit > Preferences > Add-ons (refresh the list if needed)."
