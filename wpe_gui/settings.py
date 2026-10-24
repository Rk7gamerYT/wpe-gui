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
    "autoMute": True,
    "disableMouse": False,
    "pauseOnFullscreen": True,
    "scaling": "default",
    "clamping": "clamp",
    "windowed": False,
    "screen": "",
    "lastWallpaper": "",
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
