import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/distro-packages.sh'


class DistroPackageTests(unittest.TestCase):
    def test_main_distro_families_and_derivatives(self):
        for release, expected in [('ID=ubuntu', 'debian'), ('ID=debian', 'debian'),
                                  ('ID=linuxmint\nID_LIKE="ubuntu debian"', 'debian'),
                                  ('ID=fedora', 'fedora'), ('ID=arch', 'arch'),
                                  ('ID=cachyos\nID_LIKE=arch', 'arch'),
                                  ('ID=opensuse-tumbleweed\nID_LIKE="opensuse suse"', 'opensuse')]:
            with self.subTest(release=release), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'os-release'; path.write_text(release)
                result = subprocess.run(['bash', '-c', 'source "$1"; family "$2"', 'test', str(HELPER), str(path)],
                                        capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.strip(), expected)

    def test_each_family_has_compiler_python_and_media_dependencies(self):
        for family in ['debian', 'fedora', 'arch', 'opensuse']:
            result = subprocess.run(['bash', '-c', 'source "$1"; packages "$2"', 'test', str(HELPER), family],
                                    capture_output=True, text=True, check=True)
            self.assertIn('cmake', result.stdout)
            self.assertIn('python', result.stdout)
            self.assertIn('mpv', result.stdout)
