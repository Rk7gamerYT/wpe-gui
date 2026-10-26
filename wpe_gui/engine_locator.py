"""Find the engine even when graphical launchers omit ~/.local/bin from PATH."""
import os
import shutil
from pathlib import Path


def locate_engine(custom=""):
    if custom:
        path = Path(custom).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else shutil.which(custom)
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    candidates = [
        Path.home() / ".local/bin/linux-wallpaperengine",
        data / "wpe-gui/linux-wallpaperengine/build/output/linux-wallpaperengine",
        Path.home() / ".local/share/wpe-gui/linux-wallpaperengine/build/output/linux-wallpaperengine",
    ]
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return shutil.which("linux-wallpaperengine")
