"""EasySlice Print - slice models into printable parts with matching pins and sockets.

Free and open source under the PolyForm Noncommercial License 1.0.0.
"""

from . import ops_misc, ops_plan, ops_tools, plan, prefs, props, ui

MODULES = (props, prefs, plan, ops_tools, ops_plan, ops_misc, ui)


def register():
    for m in MODULES:
        m.register()


def unregister():
    for m in reversed(MODULES):
        m.unregister()
