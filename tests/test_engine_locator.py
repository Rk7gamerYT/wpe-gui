import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from wpe_gui.engine_locator import locate_engine

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/bin/python'


class EngineLocatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def executable(self, relative, content="#!/bin/sh\nprintf '%s\\n' '--audio-gain'\n"):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(0o755)
        return path

    def test_finds_local_bin_without_path(self):
        engine = self.executable('.local/bin/linux-wallpaperengine')
        with patch('wpe_gui.engine_locator.Path.home', return_value=self.home), \
             patch('wpe_gui.engine_locator.shutil.which', return_value=None):
            self.assertEqual(locate_engine(), str(engine))

    def test_finds_build_when_launcher_symlink_is_missing(self):
        engine = self.executable('.local/share/wpe-gui/linux-wallpaperengine/build/output/linux-wallpaperengine')
        with patch.dict(os.environ, XDG_DATA_HOME=str(self.home / '.local/share')), \
             patch('wpe_gui.engine_locator.Path.home', return_value=self.home), \
             patch('wpe_gui.engine_locator.shutil.which', return_value=None):
            self.assertEqual(locate_engine(), str(engine))

    def test_rejects_non_executable_custom_file(self):
        file = self.home / 'engine'
        file.write_text('invalid')
        self.assertIsNone(locate_engine(str(file)))

    def test_installer_preserves_settings_and_saves_verified_path(self):
        import json
        config = self.home / '.config/wpe-gui/settings.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'volume': 42, 'assignments': {'DP-1': '/wallpaper'}}))
        engine = self.executable('engine')
        done = subprocess.run([str(PYTHON), '-m', 'wpe_gui.install_config', str(engine)],
                              cwd=ROOT, env=dict(os.environ, HOME=str(self.home)),
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(config.read_text())
        self.assertEqual(data['enginePath'], str(engine))
        self.assertEqual(data['volume'], 42)
        self.assertEqual(data['assignments'], {'DP-1': '/wallpaper'})

    def test_broken_engine_does_not_modify_settings(self):
        config = self.home / '.config/wpe-gui/settings.json'
        config.parent.mkdir(parents=True)
        config.write_text('{"volume": 42}')
        engine = self.executable('engine', '#!/bin/sh\nexit 1\n')
        done = subprocess.run([str(PYTHON), '-m', 'wpe_gui.install_config', str(engine)],
                              cwd=ROOT, env=dict(os.environ, HOME=str(self.home)),
                              capture_output=True, text=True, timeout=10)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(config.read_text(), '{"volume": 42}')
