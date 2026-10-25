import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtGui import QImage

from wpe_gui.login_helper import configure, read_png


class LoginHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "usr/share/gdm/dconf").mkdir(parents=True)
        (self.root / "usr/share/gdm/generate-config").touch()
        self.source = self.root / "capture.png"
        image = QImage(16, 9, QImage.Format_RGB32)
        image.fill(0xff336699)
        self.assertTrue(image.save(str(self.source), "PNG"))
        self.runner = Mock()
        self.image = self.root / "var/lib/wpe-gui/login.png"
        self.override = self.root / "usr/share/gdm/dconf/99-wpe-gui"

    def test_install_and_reset_preserve_other_gdm_settings(self):
        other = self.override.with_name("00-upstream-settings")
        other.write_text("existing settings")
        configure(self.source, self.root, self.runner)
        self.assertEqual(read_png(self.image), self.source.read_bytes())
        self.assertEqual(self.image.stat().st_mode & 0o777, 0o644)
        self.assertIn("background-size='cover'", self.override.read_text())
        self.assertEqual(other.read_text(), "existing settings")
        configure(None, self.root, self.runner)
        self.assertFalse(self.image.exists())
        self.assertFalse(self.override.exists())
        self.assertEqual(other.read_text(), "existing settings")

    def test_compile_failure_restores_existing_override_and_image(self):
        configure(self.source, self.root, self.runner)
        previous = (self.image.read_bytes(), self.override.read_bytes())
        self.runner.side_effect = [subprocess.CalledProcessError(1, "generate-config"), None]
        with self.assertRaises(subprocess.CalledProcessError):
            configure(None, self.root, self.runner)
        self.assertEqual((self.image.read_bytes(), self.override.read_bytes()), previous)

    def test_invalid_and_symlink_sources_do_not_write_configuration(self):
        bad = self.root / "bad.png"
        bad.write_bytes(b"not a screenshot")
        with self.assertRaises(ValueError):
            configure(bad, self.root, self.runner)
        link = self.root / "link.png"
        link.symlink_to(self.source)
        with self.assertRaises(OSError):
            configure(link, self.root, self.runner)
        self.assertFalse(self.override.exists())
        self.runner.assert_not_called()

    def test_temporary_symlink_is_not_followed(self):
        self.image.parent.mkdir(parents=True)
        target = self.root / "unrelated"
        target.write_bytes(b"keep")
        self.image.with_suffix(".tmp").symlink_to(target)
        with self.assertRaises(FileExistsError):
            configure(self.source, self.root, self.runner)
        self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
