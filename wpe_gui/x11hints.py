"""Keep the engine's windows out of the dock, Alt+Tab and the overview.

The engine draws the wallpaper in an ordinary X11 window, so the desktop lists it as a running application (a
generic gear icon). Marking it as a *desktop* window, which is what wallpaper windows are on X11, makes the window
manager stop treating it as an app.
"""

import re
import subprocess

from PySide6.QtCore import QObject, QTimer

TITLE = "wallpaperengine"  # window title the engine (GLFW) uses
DESKTOP = "_NET_WM_WINDOW_TYPE_DESKTOP"
_WINDOW = re.compile(r'^\s*(0x[0-9a-fA-F]+) "' + TITLE + '"', re.MULTILINE)


def _run(*cmd) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def engine_windows() -> list[str]:
    return _WINDOW.findall(_run("xwininfo", "-root", "-tree"))


def mark_as_desktop(window: str) -> bool:
    """Returns True when the window had to be changed."""
    if DESKTOP in _run("xprop", "-id", window, "_NET_WM_WINDOW_TYPE"):
        return False
    _run("xprop", "-id", window, "-f", "_NET_WM_WINDOW_TYPE", "32a", "-set", "_NET_WM_WINDOW_TYPE", DESKTOP)
    return True


class WindowHider(QObject):
    """After wallpapers start, watch for their windows for a few seconds and mark each one."""

    ATTEMPTS = 20
    INTERVAL_MS = 500

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._left = 0
        self._timer = QTimer(self, interval=self.INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        engine.activeChanged.connect(self.watch)

    def watch(self):
        self._left = self.ATTEMPTS
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        for window in engine_windows():
            mark_as_desktop(window)
        self._left -= 1
        if self._left <= 0:
            self._timer.stop()
