#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Pack the add-on into an installable Blender extension zip, without Blender.

`scripts/build.sh` prefers Blender's own `extension build`, which also validates the
manifest. This is the fallback for machines where Blender is not installed: same
layout (the package contents at the root of `<id>-<version>.zip`) and the same
default exclusions.

Usage: build_zip.py <source-dir> <output-dir>
"""

import fnmatch
import pathlib
import sys
import tomllib
import zipfile

EXCLUDE_DIRS = {"__pycache__", ".git", ".ruff_cache", ".mypy_cache"}
EXCLUDE_FILES = ("*.pyc", "*.pyo", "*.zip", "*.blend1", ".DS_Store")
REQUIRED = ("schema_version", "id", "version", "name", "tagline", "maintainer", "type", "license")


def read_manifest(src):
    path = src / "blender_manifest.toml"
    if not path.is_file():
        sys.exit(f"no blender_manifest.toml in {src}")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        sys.exit(f"blender_manifest.toml is missing: {', '.join(missing)}")
    return data


def wanted(src, path):
    rel = path.relative_to(src)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    return not any(fnmatch.fnmatch(rel.name, pat) for pat in EXCLUDE_FILES)


def main(argv):
    if len(argv) != 3:
        sys.exit("usage: build_zip.py <source-dir> <output-dir>")
    src = pathlib.Path(argv[1]).resolve()
    out = pathlib.Path(argv[2]).resolve()
    data = read_manifest(src)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{data['id']}-{data['version']}.zip"
    files = sorted(p for p in src.rglob("*") if p.is_file() and wanted(src, p))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(src).as_posix())
    for p in files:
        print(f"  {p.relative_to(src).as_posix()}")
    print(f"created {target} ({target.stat().st_size / 1024:.1f} KB, {len(files)} files)")


if __name__ == "__main__":
    main(sys.argv)
