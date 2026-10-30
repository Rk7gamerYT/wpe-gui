import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication
from wpe_gui.engine import Engine, SPAN
from wpe_gui.settings import Settings


class ManualPauseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = Engine(Settings(Path(self.temp.name) / 'settings.json'), Mock())
        self.engine._procs = {'A': Mock(), 'B': Mock()}
        self.engine._assignments = {'A': '/one', 'B': '/two'}
        self.signals = patch.object(self.engine, '_signal').start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.engine._audio_sync.stop)

    def test_manual_monitor_pause_survives_automatic_updates(self):
        self.engine.setTargetPaused('A', True)
        self.engine.setPausedTargets({'B'})
        self.assertEqual(self.engine._paused, {'A', 'B'})
        self.engine.setPausedTargets(set())
        self.assertEqual(self.engine._paused, {'A'})
        self.assertTrue(self.engine.hasManualPause)
        self.engine.setTargetPaused('A', False)
        self.assertFalse(self.engine._paused)
        self.assertFalse(self.engine.hasManualPause)

    def test_manual_resume_keeps_automatic_pause(self):
        self.engine.setPausedTargets({'A'})
        self.engine.setTargetPaused('A', True)
        self.engine.setTargetPaused('A', False)
        self.assertEqual(self.engine._paused, {'A'})
        self.assertFalse(self.engine.hasManualPause)

    def test_global_resume_clears_manual_holds_but_respects_power_saving(self):
        self.engine.setTargetPaused('A', True)
        self.engine.setGlobalPaused(True)
        self.assertEqual(self.engine._paused, {'A', 'B'})
        self.engine.setPausedTargets({'B'})
        self.engine.setGlobalPaused(False)
        self.assertEqual(self.engine._paused, {'B'})
        self.assertFalse(self.engine.hasManualPause)

    def test_resume_one_monitor_during_global_pause(self):
        self.engine.setGlobalPaused(True)
        self.engine.setTargetPaused('B', False)
        self.assertFalse(self.engine._pause_all)
        self.assertEqual(self.engine._paused, {'A'})
        self.assertEqual(self.engine._manual_paused, {'A'})

    def test_new_monitor_inherits_global_pause(self):
        self.engine.setGlobalPaused(True)
        proc = Mock()
        self.engine._procs['C'] = proc
        self.engine._assignments['C'] = '/three'
        self.engine._process_started('C', proc)
        self.signals.assert_any_call(proc, signal.SIGSTOP)
        self.assertIn('C', self.engine._paused)

    def test_restart_reapplies_manual_pause_once_pid_exists(self):
        self.engine.setTargetPaused('A', True)
        self.engine._paused.discard('A')
        replacement = Mock()
        self.engine._procs['A'] = replacement
        self.engine._process_started('A', replacement)
        self.signals.assert_any_call(replacement, signal.SIGSTOP)
        self.assertIn('A', self.engine._paused)
        self.signals.reset_mock()
        self.engine._process_started('A', Mock())
        self.signals.assert_not_called()

    def test_spanned_wallpaper_is_one_pause_target(self):
        self.engine._procs = {SPAN: Mock()}
        self.engine._assignments = {SPAN: '/span'}
        self.engine.setTargetPaused(SPAN, True)
        self.assertEqual(self.engine._paused, {SPAN})
        self.assertEqual(self.engine.playbackTargets[0]['label'], 'Todos os monitores (estendido)')

    def test_unknown_monitor_does_not_change_pause_state(self):
        self.engine.setTargetPaused('missing', True)
        self.assertFalse(self.engine.hasManualPause)
