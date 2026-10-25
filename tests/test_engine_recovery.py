import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
import unittest
from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication, QEvent
from wpe_gui.engine import Engine


class ProcessEngine(Engine):
    def binary(self):
        return self.program

    def build_args(self, *args, **kwargs):
        return ["-c", self.script]

    def _audible_key(self, keys):
        return next(iter(keys), None)


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.engine = ProcessEngine(Mock(), Mock())
        self.engine.program = "/bin/sh"
        self.engine.script = "printf 'engine failure'; exit 139"
        self.addCleanup(self.engine.shutdown)

    def tearDown(self):
        self.engine.shutdown()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def until(self, predicate):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def test_crash_restarts_and_keeps_assignment(self):
        self.engine._start("test", "/wallpaper")
        self.until(lambda: "test" in self.engine._restarts)
        self.assertEqual(self.engine._assignments, {"test": "/wallpaper"})
        self.engine.script = "sleep 30"
        self.engine._restarts["test"].start(1)
        self.until(lambda: "test" in self.engine._procs)
        self.assertEqual(self.engine._failures["test"], 1)

    def test_stop_cancels_pending_recovery(self):
        self.engine._start("test", "/wallpaper")
        self.until(lambda: bool(self.engine._restarts))
        self.engine.stop()
        self.assertFalse(self.engine._restarts)
        self.assertFalse(self.engine._assignments)

    def test_repeated_crashes_stop_retrying(self):
        self.engine._start("test", "/wallpaper")
        for attempt in range(1, 4):
            self.until(lambda: bool(self.engine._restarts))
            self.assertEqual(self.engine._failures["test"], attempt)
            self.engine._restarts["test"].start(1)
            self.until(lambda: not self.engine._restarts)
        self.until(lambda: not self.engine._assignments)
        self.assertFalse(self.engine._procs)

    def test_missing_binary_cleans_up(self):
        self.engine.program = "/nonexistent/wpe-engine"
        self.engine._start("test", "/wallpaper")
        self.until(lambda: bool(self.engine._restarts))
        self.assertFalse(self.engine._procs)

    def test_output_buffer_is_bounded(self):
        self.engine.script = "head -c 1000000 /dev/zero; sleep 30"
        self.engine._start("test", "/wallpaper")
        proc = self.engine._procs["test"]
        self.until(lambda: len(self.engine._output[proc]) == 8192)
        self.assertLessEqual(len(self.engine._output[proc]), 8192)
