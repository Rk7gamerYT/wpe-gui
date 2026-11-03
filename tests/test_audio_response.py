import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import QCoreApplication
from wpe_gui.engine import Engine
from wpe_gui.settings import Settings
from wpe_gui.properties import PropertiesStore


class AudioResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = patch.dict(os.environ, XDG_STATE_HOME=str(self.root/'state'))
        self.state.start(); self.addCleanup(self.state.stop)
        self.props = PropertiesStore(self.root/'overrides.json')
        self.engine = Engine(Settings(self.root/'settings.json'), self.props)
        self.engine._log = Mock()
        self.addCleanup(self.engine._reapply.stop)
        self.addCleanup(self.engine._audio_sync.stop)
        self.folder = str(self.root/'wallpaper')
        Path(self.folder).mkdir()
        self.props.changed.connect(self.engine.propertiesChanged)

    def test_live_response_changes_do_not_restart_or_enqueue_scene(self):
        self.engine._procs = {'A': Mock()}
        self.engine._assignments = {'A': self.folder}
        self.engine._render_signatures[self.folder] = self.engine._render_signature(self.folder)
        with patch.object(self.engine, '_stop_keys') as stop, patch.object(self.engine, '_start') as start:
            self.props.setEngineOption(self.folder, 'audioResponseMode', 'manual')
            self.props.setEngineOption(self.folder, 'audioResponseSpeed', '2')
            control = Path(self.engine._sync_audio_response(self.folder))
            self.assertEqual(json.loads(control.read_text()), 2)
            self.props.setEngineOption(self.folder, 'audioResponseMode', 'auto')
            self.assertEqual(json.loads(control.read_text()), 0)
            stop.assert_not_called(); start.assert_not_called()
            self.assertFalse(self.engine._pending)
            self.assertFalse(self.engine._reapply.isActive())

    def test_visual_changes_still_rebuild_scene(self):
        self.engine._procs = {'A': Mock()}
        self.engine._assignments = {'A': self.folder}
        self.engine._render_signatures[self.folder] = self.engine._render_signature(self.folder)
        self.props.setEngineOption(self.folder, 'scaling', 'fill')
        self.assertTrue(self.engine._reapply.isActive())

    def test_duplicate_option_is_a_noop_and_speed_rejects_nonfinite(self):
        changed = Mock(); self.props.changed.connect(changed)
        self.props.setEngineOption(self.folder, 'audioResponseSpeed', '2')
        self.props.setEngineOption(self.folder, 'audioResponseSpeed', '2')
        self.props.setEngineOption(self.folder, 'audioResponseSpeed', 'nan')
        self.props.setEngineOption(self.folder, 'audioResponseSpeed', 'inf')
        self.assertEqual(changed.call_count, 1)
        self.assertEqual(self.props.engineOption(self.folder, 'audioResponseSpeed'), '2')

    def test_only_exposed_numeric_audio_timing_is_detected(self):
        controls = {'visualizer_smoothtime': {'type':'slider', 'text':'Audio Smooth Delay', 'value':50},
                    'audioreactive': {'type':'bool', 'text':'Audioreactive', 'value':True},
                    'speed': {'type':'slider', 'text':'Animation speed', 'value':1}}
        (Path(self.folder)/'project.json').write_text(json.dumps({'title':'test','type':'scene','general':{'properties':controls}}))
        self.assertEqual(self.props.audioTimingControls(self.folder),
                         [{'key':'visualizer_smoothtime','label':'Audio Smooth Delay'}])

    def test_controls_are_independent_for_different_wallpapers(self):
        self.props.setEngineOption(self.folder, 'audioResponseMode', 'manual')
        self.props.setEngineOption(self.folder, 'audioResponseSpeed', '3')
        one = Path(self.engine._sync_audio_response(self.folder))
        two = Path(self.engine._sync_audio_response('/another-wallpaper'))
        self.assertNotEqual(one, two)
        self.assertEqual(json.loads(one.read_text()), 3)
        self.assertEqual(json.loads(two.read_text()), 0)
