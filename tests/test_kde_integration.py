import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication
from wpe_gui.engine import Engine
from wpe_gui.settings import Settings


class KDEIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(self.root / 'settings.json')
        props = Mock()
        props.engine_options.return_value = {}
        props.engine_args.return_value = []
        self.engine = Engine(self.settings, props)
        self.addCleanup(self.engine.shutdown)

    def test_kde_wayland_ignores_saved_gnome_window_mode(self):
        self.settings.set('windowed', True)
        screen = Mock()
        screen.name.return_value = 'DP-5'
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='KDE', XDG_SESSION_TYPE='wayland'), \
             patch.object(self.engine, '_screens_by_name', return_value={'DP-5': screen}), \
             patch('wpe_gui.engine.library.audio_responsive', return_value=False):
            args = self.engine.build_args(str(self.root), 'DP-5')
        self.assertIn('--screen-root', args)
        self.assertNotIn('--window', args)
        self.assertEqual(args[args.index('--layer') + 1], 'background')

    def test_gnome_keeps_window_mode(self):
        self.settings.set('windowed', True)
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='ubuntu:GNOME', XDG_SESSION_TYPE='wayland'):
            self.assertTrue(self.engine.windowed())

    def test_migrates_hdmi_connector_without_losing_wallpaper(self):
        self.settings.set('assignments', {'HDMI-3': str(self.root)})
        with patch.object(self.engine, '_screens_by_name', return_value={'HDMI-A-3': Mock()}), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch.object(self.engine, '_start') as start, \
             patch.object(self.engine, '_rebalance_audio'):
            self.engine.restore()
        start.assert_called_once_with('HDMI-A-3', str(self.root), planned={'HDMI-A-3'})
        self.assertEqual(self.settings.get('assignments'), {'HDMI-A-3': str(self.root)})

    def test_existing_kde_assignment_wins_over_old_hdmi_alias(self):
        current = self.root / 'current'
        current.mkdir()
        self.settings.set('assignments', {'HDMI-3': str(self.root), 'HDMI-A-3': str(current)})
        with patch.object(self.engine, '_screens_by_name', return_value={'HDMI-A-3': Mock()}), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch.object(self.engine, '_start') as start, \
             patch.object(self.engine, '_rebalance_audio'):
            self.engine.restore()
        start.assert_called_once_with('HDMI-A-3', str(current), planned={'HDMI-A-3'})
