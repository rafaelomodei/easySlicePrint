#!/usr/bin/env bash
# Uploads a built extension zip to extensions.blender.org.
#
# Blender's own extension command line only works locally - `blender --command extension
# build` packs the zip and `... validate` checks the manifest (both run by scripts/build.sh).
# There is no upload subcommand: publishing goes through the platform API, documented at
# https://developer.blender.org/docs/features/extensions/ci_cd/
#
# Usage:
#   BLENDER_EXTENSIONS_TOKEN=xxx scripts/publish_extension.sh                 # build + upload
#   BLENDER_EXTENSIONS_TOKEN=xxx scripts/publish_extension.sh --dry-run       # show, upload nothing
#   BLENDER_EXTENSIONS_TOKEN=xxx scripts/publish_extension.sh --zip dist/easy_slice_print-0.3.3-alpha.zip
#
# Options:
#   --zip PATH          upload this zip instead of building one
#   --version X.Y.Z     version to publish (default: the manifest version)
#   --notes-file PATH   release notes (default: that version's section of CHANGELOG.md)
#   --dry-run           print the request and stop
#
# The token is generated on https://extensions.blender.org/ under the user profile page.
# An upload creates a new version on the platform; it goes live after moderation, so run
# this only when the release is meant to reach users - it is not wired to any schedule.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$HERE/easy_slice_print/blender_manifest.toml"
API="https://extensions.blender.org/api/v1/extensions"
# The API rejects release notes longer than this (ExtensionVersionRequest.release_notes).
NOTES_MAX=1024

zip_path=""
version=""
notes_file=""
dry_run=0
while [ $# -gt 0 ]; do
  case "$1" in
    --zip) zip_path="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --notes-file) notes_file="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

field() { grep -E "^$1 *= *\"" "$MANIFEST" | sed -E 's/.*"([^"]+)".*/\1/'; }
extension_id="$(field id)"
[ -n "$version" ] || version="$(field version)"
[ -n "$extension_id" ] || { echo "no id in $MANIFEST" >&2; exit 1; }

if [ -z "$zip_path" ]; then
  zip_path="$HERE/dist/${extension_id}-${version}.zip"
  if [ ! -f "$zip_path" ]; then
    echo "==> building $zip_path"
    "$HERE/scripts/build.sh"
  fi
fi
[ -f "$zip_path" ] || { echo "zip not found: $zip_path" >&2; exit 1; }

# Release notes: this version's section of the changelog, same slice the Release workflow
# takes for the GitHub release, trimmed to whole lines within the API limit.
notes_tmp=""
if [ -z "$notes_file" ]; then
  notes_tmp="$(mktemp)"
  trap 'rm -f "$notes_tmp"' EXIT
  awk -v ver="$version" '/^## /{p = index($0, "[" ver "]") || index($0, " " ver " ")} p' \
    "$HERE/CHANGELOG.md" > "$notes_tmp"
  notes_file="$notes_tmp"
fi
[ -s "$notes_file" ] || { echo "no release notes for $version (looked in $notes_file)" >&2; exit 1; }

notes="$(cat "$notes_file")"
if [ "${#notes}" -gt "$NOTES_MAX" ]; then
  # Keep whole lines, leaving room for the pointer at the end.
  suffix="
[...]

Full changelog: https://github.com/rafaelomodei/easySlicePrint/blob/main/CHANGELOG.md"
  notes="$(awk -v max="$(( NOTES_MAX - ${#suffix} ))" \
    '{ if (n + length($0) + 1 > max) exit; print; n += length($0) + 1 }' "$notes_file")$suffix"
  notes="${notes:0:$NOTES_MAX}"
fi

echo "==> extension : $extension_id"
echo "==> version   : $version"
echo "==> zip       : $zip_path ($(du -h "$zip_path" | cut -f1))"
echo "==> endpoint  : $API/$extension_id/versions/upload/"
echo "==> notes     : ${#notes} chars"
if [ "$dry_run" = 1 ]; then
  echo "--- release notes ---"
  printf '%s\n' "$notes"
  echo "--- dry run, nothing uploaded ---"
  exit 0
fi

: "${BLENDER_EXTENSIONS_TOKEN:?set BLENDER_EXTENSIONS_TOKEN (extensions.blender.org profile page)}"

response="$(mktemp)"
trap 'rm -f "$notes_tmp" "$response"' EXIT
code="$(curl -sS -X POST "$API/$extension_id/versions/upload/" \
  -H "Authorization: bearer $BLENDER_EXTENSIONS_TOKEN" \
  -F "version_file=@$zip_path" \
  -F "release_notes=$notes" \
  -o "$response" -w '%{http_code}')"

cat "$response"; echo
if [ "$code" != "201" ] && [ "$code" != "200" ]; then
  echo "upload failed (HTTP $code)" >&2
  exit 1
fi
echo "==> uploaded. It goes live after moderation:"
echo "    https://extensions.blender.org/approval-queue/easy-slice-print/"
