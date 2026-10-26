"""Exercise the one-command installer with a local archive, without system changes."""
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OnlineInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.app = self.home / 'installed app'
        self.source = self.home / 'source'
        self.source.mkdir()
        (self.source / 'wpe-gui.sh').touch()
        (self.source / 'install.sh').write_text('#!/bin/bash\nprintf "%s\\n" "$@" > install-arguments\n')
        self.archive = self.home / 'app.tar.gz'

    def run_installer(self, *args):
        with tarfile.open(self.archive, 'w:gz') as tar:
            tar.add(self.source, arcname='wpe-gui-main')
        return subprocess.run(['bash', str(ROOT / 'install-online.sh'), *args],
                              env=dict(os.environ, HOME=str(self.home), WPE_APP_DIR=str(self.app),
                                       WPE_ARCHIVE_URL=self.archive.as_uri()),
                              capture_output=True, text=True, timeout=10)

    @unittest.skipIf(os.geteuid() == 0, 'Installer intentionally rejects root')
    def test_download_install_and_update_preserve_user_environment(self):
        first = self.run_installer('--no-deps')
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual((self.app / 'install-arguments').read_text(), '--yes\n--no-deps\n')
        self.assertTrue((self.app / '.wpe-managed-install').is_file())
        (self.app / '.venv').mkdir()
        (self.app / '.venv/keep').touch()
        (self.source / 'new-version').touch()
        second = self.run_installer()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue((self.app / '.venv/keep').exists())
        self.assertTrue((self.app / 'new-version').exists())

    @unittest.skipIf(os.geteuid() == 0, 'Installer intentionally rejects root')
    def test_failed_installation_never_reports_success(self):
        (self.source / 'install.sh').write_text('#!/bin/bash\nexit 7\n')
        result = self.run_installer()
        self.assertEqual(result.returncode, 7)
        self.assertNotIn('Instalação concluída', result.stdout)

    def test_dry_run_creates_no_app_directory(self):
        result = self.run_installer('--dry-run')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.app.exists())

    @unittest.skipIf(os.geteuid() == 0, 'Installer intentionally rejects root')
    def test_does_not_overwrite_unmanaged_directory(self):
        self.app.mkdir()
        (self.app / 'personal-file').write_text('keep')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.app / 'personal-file').read_text(), 'keep')
        self.assertFalse((self.app / 'install.sh').exists())
