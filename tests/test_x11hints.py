import unittest
from unittest.mock import patch

from PySide6.QtCore import QObject, QCoreApplication, Signal
from wpe_gui.x11hints import WindowHider


class FakeEngine(QObject):
    activeChanged = Signal()
    running = False


class WindowHiderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.engine = FakeEngine()
        self.hider = WindowHider(self.engine)
        self.addCleanup(self.hider._timer.stop)

    @patch('wpe_gui.x11hints.let_input_through', return_value=True)
    @patch('wpe_gui.x11hints.mark_as_desktop')
    @patch('wpe_gui.x11hints.engine_windows', return_value=['0x123'])
    def test_reapplies_shape_after_remap_or_reused_id(self, windows, mark, shape):
        self.engine.running = True
        self.engine.activeChanged.emit()
        # The old watcher stopped after 20 scans and skipped already-seen IDs.
        for _ in range(25):
            self.hider._tick()
        self.assertEqual(shape.call_count, 25)
        self.assertTrue(self.hider._timer.isActive())
        windows.return_value = []
        self.hider._tick()
        windows.return_value = ['0x123']
        self.hider._tick()
        self.assertEqual(shape.call_count, 26)
        self.engine.running = False
        self.engine.activeChanged.emit()
        self.assertFalse(self.hider._timer.isActive())
