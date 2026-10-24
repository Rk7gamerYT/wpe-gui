"""JSON-backed settings exposed to QML."""

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

CONFIG_PATH = Path.home() / ".config/wpe-gui/settings.json"

DEFAULTS = {
    "enginePath": "",
    "libraryDirs": [],
    "assetsDir": "",
    "fps": 30,
    "volume": 100,
    "silent": False,
    "autoMute": False,
    "disableMouse": False,
    "pauseOnFullscreen": True,
    "powerSaving": "fullscreen",  # off | fullscreen | maximized
    "audioGain": 1.0,
    "closeToTray": True,  # closing the window keeps the app running in the system tray
    "staticBackground": True,  # keep a still picture of the wallpaper as the desktop background
    "staticSignature": "",
    "originalBackground": {},
    "scaling": "default",
    "clamping": "clamp",
    "windowed": False,
    "layout": "independent",
    "assignments": {},
    "restoreOnStart": True,
}


class Settings(QObject):
    changed = Signal()

    def __init__(self, path: Path = CONFIG_PATH, parent=None):
        super().__init__(parent)
        self._path = path
        self._data = dict(DEFAULTS)
        try:
            self._data.update(json.loads(path.read_text()))
        except (OSError, ValueError):
            pass

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    @Slot(str, "QVariant")
    def set(self, key, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))
        self.changed.emit()

    @Slot(str, result="QVariant")
    def value(self, key):
        return self.get(key)
