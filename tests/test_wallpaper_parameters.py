import json
import tempfile
import unittest
from pathlib import Path
from wpe_gui.library import read_project, read_wallpaper
from wpe_gui.properties import PropertiesStore


class WallpaperParametersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / '100'
        self.base.mkdir()
        self.project = {'title': 'Base', 'type': 'web', 'file': 'index.html', 'general': {'properties': {
            'speed': {'type': 'slider', 'value': 2},
            'image': {'type': 'file', 'value': None},
            'folder': {'type': 'directory', 'value': ''}}}}
        (self.base / 'project.json').write_text(json.dumps(self.project))
        self.store = PropertiesStore(self.root / 'overrides.json')

    def test_preset_inherits_type_and_defaults_without_changing_original(self):
        preset = self.root / '200'; preset.mkdir()
        (preset / 'project.json').write_text(json.dumps({'title': 'Preset', 'dependency': '100',
                                                      'preset': {'speed': 3, 'image': None}}))
        wallpaper = read_wallpaper(preset)
        self.assertEqual(wallpaper.type, 'web')
        self.assertEqual(wallpaper.title, 'Preset')
        self.assertEqual(wallpaper.properties['speed']['value'], 3)
        self.assertEqual(read_project(self.base), self.project)

    def test_dependency_cycles_and_paths_are_rejected(self):
        for dependency in ('100', '../100', '/tmp', '１００'):
            (self.base / 'project.json').write_text(json.dumps({'dependency': dependency}))
            self.assertIsNone(read_wallpaper(self.base))

    def test_auto_uses_author_defaults_and_keeps_manual_values(self):
        folder = str(self.base)
        self.store.setValue(folder, 'speed', 4)
        self.assertEqual(self.store.parameterMode(folder), 'manual')  # legacy adjustments survive
        self.assertEqual(self.store.engine_args(folder), ['--set-property', 'speed=4'])
        self.store.setEngineOption(folder, 'wallpaperParametersMode', 'auto')
        self.assertEqual(self.store.engine_args(folder), [])
        self.assertEqual(next(x['value'] for x in self.store.load(folder) if x['key'] == 'speed'), 2)
        self.store.setEngineOption(folder, 'wallpaperParametersMode', 'manual')
        self.assertEqual(self.store.engine_args(folder), ['--set-property', 'speed=4'])
        self.assertEqual(read_project(self.base), self.project)

    def test_optional_files_and_directories_are_strings(self):
        folder = str(self.base)
        self.assertEqual(next(x['value'] for x in self.store.load(folder) if x['key'] == 'image'), '')
        self.store.setValue(folder, 'image', '/tmp/a b.png')
        self.store.setValue(folder, 'folder', '/tmp/music')
        self.assertEqual(self.store.engine_args(folder), ['--set-property', 'image=/tmp/a b.png',
                                                        '--set-property', 'folder=/tmp/music'])
