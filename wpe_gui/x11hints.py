"""Keep the engine's windows out of the dock, Alt+Tab and the overview.

The engine draws the wallpaper in an ordinary X11 window, so the desktop lists it as a running application (a
generic gear icon). Marking it as a *desktop* window, which is what wallpaper windows are on X11, makes the window
manager stop treating it as an app.
"""

import ctypes
import ctypes.util
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


def let_input_through(window: str) -> bool:
    """Give the window an empty *input shape*, so pointer events go to whatever is below it.

    The X server hit-tests with its own window stack, and the engine's window (full monitor) ends up above the other
    X11 windows in it: without this, X11 apps (Steam, xterm, ...) get no clicks while a wallpaper is running. Wayland
    apps never had the problem, the compositor decides their focus. The shape stays on the window after we disconnect.
    """
    x11_path, xext_path = ctypes.util.find_library("X11"), ctypes.util.find_library("Xext")
    if not x11_path or not xext_path:
        return False
    x11, xext = ctypes.CDLL(x11_path), ctypes.CDLL(xext_path)
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    xext.XShapeCombineRectangles.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                             ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        # kind 2 = ShapeInput, operation 0 = ShapeSet, no rectangles = an empty region
        xext.XShapeCombineRectangles(display, int(window, 16), 2, 0, 0, None, 0, 0, 0)
        x11.XSync(display, 0)
    finally:
        x11.XCloseDisplay(display)
    return True


class WindowHider(QObject):
    """After wallpapers start, watch for their windows for a few seconds and mark each one."""

    ATTEMPTS = 20
    INTERVAL_MS = 500

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._left = 0
        self._passthrough: set[str] = set()  # window ids already made input-transparent
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
            if window not in self._passthrough and let_input_through(window):
                self._passthrough.add(window)
        self._left -= 1
        if self._left <= 0:
            self._timer.stop()
