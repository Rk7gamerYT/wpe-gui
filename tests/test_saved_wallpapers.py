import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication
from wpe_gui.engine import Engine
from wpe_gui.json_store import write_json
from wpe_gui.settings import Settings


class SavedWallpaperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'settings.json'
        self.settings = Settings(self.path)
        self.engine = Engine(self.settings, Mock())
        self.saved = {'DP-5': str(self.root)}
        self.settings.set('assignments', self.saved)
        self.addCleanup(self.engine.shutdown)

    def test_stop_preserves_json_and_restore_survives_reopening(self):
        self.engine._assignments = dict(self.saved)
        self.engine.stop()
        self.assertFalse(self.engine._assignments)
        reopened = Settings(self.path)
        self.assertEqual(reopened.get('assignments'), self.saved)
        self.assertTrue(self.engine.canRestore)
        with patch.object(self.engine, '_screens_by_name', return_value={'DP-5': Mock()}), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch.object(self.engine, '_start') as start, \
             patch.object(self.engine, '_rebalance_audio'):
            self.engine.restore()
            start.assert_called_once_with('DP-5', str(self.root), planned={'DP-5'})

    def test_repeated_restore_does_not_duplicate_running_target(self):
        self.engine._assignments = dict(self.saved)
        with patch.object(self.engine, '_screens_by_name', return_value={'DP-5': Mock()}), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch.object(self.engine, '_start') as start, \
             patch.object(self.engine, '_rebalance_audio'):
            self.engine.restore()
            self.engine.restore()
            start.assert_not_called()

    def test_failed_json_replacement_preserves_previous_file(self):
        previous = self.path.read_bytes()
        with patch('wpe_gui.json_store.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                write_json(self.path, {'assignments': {}})
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.root.iterdir()), [self.path])
        self.assertEqual(json.loads(previous)['assignments'], self.saved)
