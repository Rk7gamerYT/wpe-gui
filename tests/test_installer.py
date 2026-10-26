"""Verify desktop routing and dry-run isolation without installing anything."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def run_installer(self, desktop, *options):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, HOME=directory, XDG_CURRENT_DESKTOP=desktop)
            done = subprocess.run(
                ['bash', str(ROOT / 'install.sh'), '--dry-run', '--no-deps', '--no-engine', '--yes', *options],
                env=env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])
            return done.stdout

    def test_kde_installs_its_plugins_without_gnome_extension(self):
        output = self.run_installer('KDE')
        self.assertIn('/kde/install.sh', output)
        self.assertNotIn('/extension/install.sh', output)

    def test_kde_matches_colon_separated_desktops(self):
        self.assertIn('/kde/install.sh', self.run_installer('ubuntu:KDE'))

    def test_no_kde_skips_plugins(self):
        self.assertNotIn('/kde/install.sh', self.run_installer('KDE', '--no-kde'))

    def test_other_desktops_do_not_install_gnome_or_kde(self):
        output = self.run_installer('sway')
        self.assertNotIn('/kde/install.sh', output)
        self.assertNotIn('/extension/install.sh', output)
