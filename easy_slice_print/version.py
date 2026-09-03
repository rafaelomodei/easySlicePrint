# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""The add-on version, read from the extension manifest.

`blender_manifest.toml` is the single source of truth and ships next to this
module inside the installed extension, so the version shown in the sidebar can
never drift from the one Blender installed.
"""

import pathlib
import re

#: Development stage of this release. Alpha: usable, but expect rough edges.
STAGE = "alpha"

_FALLBACK = "0.0.0"


def _read_version():
    path = pathlib.Path(__file__).with_name("blender_manifest.toml")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else _FALLBACK


VERSION = _read_version()
#: What the UI shows, e.g. "0.3.1-alpha", or "0.2.3 alpha" when the number carries no stage.
VERSION_LABEL = VERSION if not STAGE or STAGE in VERSION else f"{VERSION} {STAGE}"
