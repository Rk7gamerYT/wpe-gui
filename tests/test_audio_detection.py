import json
import tempfile
import unittest
from pathlib import Path
from wpe_gui.library import audio_responsive


class AudioDetectionTests(unittest.TestCase):
    def test_detects_shader_and_script_audio_without_metadata(self):
        for marker in (b'g_AudioSpectrum64Left', b'engine.registerAudioBuffers(64)'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'project.json').write_text(json.dumps({'general': {}}))
                (root / 'scene.pkg').write_bytes(marker)
                self.assertTrue(audio_responsive(str(root)))
                audio_responsive.cache_clear()
