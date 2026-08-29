# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Rafael Omodei and EasySlice Print contributors
"""Run a long cut as a modal job instead of blocking Blender's main thread.

A boolean on a dense mesh takes seconds, and a plan build chains several of
them.  Done inside a plain `execute()` the whole thing runs in one go with the
event loop stopped, so the desktop compositor gets no answer to its liveness
ping (GNOME's `check-alive-timeout`, 5 s by default) and pops up the
"application is not responding - Wait / Force Quit" dialog.  Nothing is
actually wrong: Blender is just busy and cannot say so.

The fix is to cut the work into steps and return to the event loop between
them.  `core.cutting` exposes the pipeline as generators that yield a label
before each heavy step; `JobMixin` drives one of those generators from a modal
timer, one step per tick, so the window keeps answering pings and the user gets
a live progress line in the status bar.
"""

import time

JOB_TICK = 0.01  # timer interval: come back as soon as the event loop is free
JOB_BUDGET = 0.15  # keep pulling steps for this long before yielding back

RUNNING = 'RUNNING'
DONE = 'DONE'
ERROR = 'ERROR'
CANCELLED = 'CANCELLED'


class JobMixin:
    """Mixin for modal operators that need to run a step generator.

    Call `job_start` to begin, `job_step` from `modal()` while `job_running()`,
    and `job_stop` from any early exit path.
    """

    _job = None
    _job_timer = None
    _job_window = None
    _job_title = ""
    _job_label = ""
    _job_t0 = 0.0

    # -- lifecycle ----------------------------------------------------------
    def job_start(self, context, generator, title, add_handler=False):
        """Begin running `generator`; returns the value `modal()`/`invoke()` should return."""
        self._job = generator
        self._job_title = title
        self._job_label = "starting"
        self._job_t0 = time.time()
        self._job_window = context.window
        wm = context.window_manager
        self._job_timer = wm.event_timer_add(JOB_TICK, window=context.window)
        if add_handler:
            wm.modal_handler_add(self)
        if self._job_window is not None:
            try:
                self._job_window.cursor_modal_set('WAIT')
            except Exception:
                pass
        self.job_status(context)
        return {'RUNNING_MODAL'}

    def job_running(self):
        return self._job is not None

    def job_stop(self, context):
        if self._job_timer is not None:
            try:
                context.window_manager.event_timer_remove(self._job_timer)
            except Exception:
                pass
            self._job_timer = None
        if self._job is not None:
            self._job.close()
            self._job = None
        if self._job_window is not None:
            try:
                self._job_window.cursor_modal_restore()
            except Exception:
                pass
            self._job_window = None
        try:
            context.workspace.status_text_set(None)
        except Exception:
            pass

    # -- driving ------------------------------------------------------------
    def job_step(self, context, event):
        """Advance the job by as many steps as fit in one tick.

        Returns (state, payload): ('RUNNING', None) while there is more to do,
        ('DONE', generator return value), ('ERROR', exception) or
        ('CANCELLED', None).  The job is stopped for every state but RUNNING.
        """
        if event.type in {'ESC'} and event.value == 'PRESS':
            self.job_stop(context)
            return CANCELLED, None
        if event.type != 'TIMER':
            # swallow everything else: the scene is mid-edit and not safe to touch
            return RUNNING, None
        deadline = time.time() + JOB_BUDGET
        while True:
            try:
                label = next(self._job)
            except StopIteration as stop:
                self.job_stop(context)
                return DONE, stop.value
            except Exception as exc:  # CutError and anything the pipeline raises
                self.job_stop(context)
                return ERROR, exc
            if label:
                self._job_label = label
            if time.time() >= deadline:
                break
        self.job_status(context)
        return RUNNING, None

    def job_status(self, context):
        elapsed = time.time() - self._job_t0
        text = f"EasySlice {self._job_title}: {self._job_label}...  ({elapsed:.1f}s)  |  Esc: cancel"
        try:
            context.workspace.status_text_set(text)
        except Exception:
            pass
