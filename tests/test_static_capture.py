import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import QCoreApplication, QRect
from wpe_gui.engine import Engine, SPAN
from wpe_gui.settings import Settings


class StaticCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = Engine(Settings(Path(self.tmp.name) / 'settings.json'), Mock())
        self.engine._log = Mock()
        self.addCleanup(self.engine._audio_sync.stop)
        self.screens = {'A': Mock(), 'B': Mock()}
        self.screens['A'].geometry.return_value = QRect(-1920, 0, 1920, 1080)
        self.screens['B'].geometry.return_value = QRect(0, 0, 2560, 1440)

    def test_capture_has_private_geometry_and_keeps_live_processes(self):
        original = ['--fps', '30', '--silent', '--screen-root', 'A', '--layer', 'background', '--bg', '/scene']
        self.engine._procs = {'A': Mock()}
        before = dict(self.engine._procs)
        with patch.object(self.engine, 'build_args', return_value=original), \
             patch.object(self.engine, '_screens_by_name', return_value=self.screens):
            args = self.engine.build_capture_args('/scene', 'A')
        self.assertNotIn('--screen-root', args)
        self.assertNotIn('--layer', args)
        self.assertIn('--silent', args)
        self.assertEqual(args[args.index('--window')+1], '0x0x1920x1080')
        self.assertEqual(self.engine._procs, before)

    def test_span_capture_uses_union_without_a_desktop_layer(self):
        with patch.object(self.engine, 'build_args', return_value=['--screen-span', 'A,B', '--bg', '/scene']), \
             patch.object(self.engine, '_screens_by_name', return_value=self.screens):
            args = self.engine.build_capture_args('/scene', SPAN)
        self.assertNotIn('--screen-span', args)
        self.assertEqual(args[args.index('--window')+1], '0x0x4480x1440')
        self.assertIn('--no-fullscreen-pause', args)
