import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication, QEvent
from wpe_gui.engine import Engine
from wpe_gui.settings import Settings


class SleepEngine(Engine):
    def binary(self):
        return '/bin/sh'

    def build_args(self, *args, **kwargs):
        return ['-c', 'exec sleep 30']


class PauseProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = SleepEngine(Settings(Path(self.temp.name) / 'settings.json'), Mock())
        self.engine._start('A', '/wallpaper')
        self.until(lambda: self.engine._procs['A'].processId() != 0)

    def tearDown(self):
        self.engine.shutdown()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.temp.cleanup()

    def until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def stopped(self):
        pid = self.engine._procs['A'].processId()
        if not pid:
            return False
        try:
            return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].strip().startswith('T')
        except OSError:
            return False

    def test_pause_resume_and_restart_use_real_process_signals(self):
        self.engine.setTargetPaused('A', True)
        self.until(self.stopped)
        previous = self.engine._procs['A'].processId()
        self.engine._pending = {'A'}
        self.engine._reapply_pending()
        self.until(lambda: self.engine._procs['A'].processId() not in (0, previous) and self.stopped())
        self.engine.setTargetPaused('A', False)
        self.until(lambda: not self.stopped())
        self.assertFalse(self.engine.hasManualPause)
