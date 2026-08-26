# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""EasySlice Print - slice models into printable parts with matching pins and sockets.

Free software under the GNU General Public License v3.0 or later.
"""

from . import ops_misc, ops_plan, ops_tools, plan, prefs, props, ui

MODULES = (props, prefs, plan, ops_tools, ops_plan, ops_misc, ui)


def register():
    for m in MODULES:
        m.register()


def unregister():
    for m in reversed(MODULES):
        m.unregister()
