import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wpe_gui.updater import install_verified, select_update, update_target


class UpdaterTests(unittest.TestCase):
    def release(self, **asset):
        return {'tag_name': 'v0.3.0', 'assets': [dict(name='wpe-gui-0.3.0-x86_64.AppImage',
                browser_download_url='https://github.com/Rk7gamerYT/wpe-gui/releases/download/v0.3.0/app.AppImage',
                digest='sha256:' + 'a' * 64, size=100, **asset)]}

    def test_only_new_releases_are_selected(self):
        self.assertEqual(select_update(self.release(), '0.2.0')['version'], 'v0.3.0')
        self.assertIsNone(select_update(self.release(), '0.3.0'))
        self.assertIsNone(select_update(dict(self.release(), prerelease=True)))

    def test_untrusted_asset_or_missing_digest_is_rejected(self):
        for key, value in [('browser_download_url', 'https://example.com/file.AppImage'), ('digest', '')]:
            release = self.release()
            release['assets'][0][key] = value
            with self.assertRaises(ValueError):
                select_update(release)

    def test_failed_verification_preserves_current_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, download = Path(tmp) / 'app.AppImage', Path(tmp) / 'download'
            target.write_bytes(b'old'); download.write_bytes(b'new')
            with self.assertRaises(ValueError):
                install_verified(download, target, '0' * 64)
            self.assertEqual(target.read_bytes(), b'old')
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['app.AppImage', 'download'])

    def test_verified_update_atomically_replaces_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, download = Path(tmp) / 'app.AppImage', Path(tmp) / 'download'
            target.write_bytes(b'old'); download.write_bytes(b'new')
            install_verified(download, target, hashlib.sha256(b'new').hexdigest())
            self.assertEqual(target.read_bytes(), b'new')
            self.assertTrue(os.access(target, os.X_OK))

    def test_source_install_never_overwrites_its_python_launcher(self):
        with patch.dict(os.environ, {'APPIMAGE': ''}):
            with self.assertRaises(ValueError):
                update_target()
