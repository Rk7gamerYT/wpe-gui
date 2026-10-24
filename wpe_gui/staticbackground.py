"""Static desktop background: keep a still picture of the running wallpaper behind the desktop.

Like the Windows Wallpaper Engine, whatever is on screen when the app is closed stays as the desktop background
instead of the previous (unrelated) picture coming back. While wallpapers run, a frame of each one is captured,
the frames are laid out like the monitors, and the result is set as the GNOME background ('spanned', so every
monitor shows its own part).
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QRect, QTimer, Property, Qt, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

from . import library
from .engine import SPAN

OUTPUT_DIR = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "wpe-gui"
SCHEMA = "org.gnome.desktop.background"
KEYS = ("picture-uri", "picture-uri-dark", "picture-options")
SETTLE_MS = 6000  # wait for the engine to settle (and for batches of changes) before capturing
CAPTURE_TIMEOUT_MS = 25000


def gsettings(*args) -> str | None:
    try:
        done = subprocess.run(["gsettings", *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def video_frame(folder: Path, destination: Path) -> bool:
    """A frame from the wallpaper's video file; the engine's own screenshot is taken too early for videos."""
    try:
        name = json.loads((folder / "project.json").read_text(encoding="utf-8-sig")).get("file", "")
    except (OSError, ValueError):
        return False
    source = folder / name
    if not name or not source.is_file() or not shutil.which("ffmpeg"):
        return False
    done = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", str(source), "-frames:v", "1", str(destination)],
        capture_output=True, timeout=60,
    )
    return done.returncode == 0 and destination.is_file() and destination.stat().st_size > 0


def compose(pieces: dict, screens: dict, span_path: str | None, destination: Path) -> bool:
    """Lay the captured pictures out like the monitors and save them as one image.

    pieces: target key -> picture path; screens: monitor name -> QRect of the monitor.
    """
    if not screens:
        return False
    union = QRect()
    for rect in screens.values():
        union = union.united(rect)
    canvas = QImage(union.size(), QImage.Format_RGB32)
    canvas.fill(QColor("black"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    def draw(path, rect):
        image = QImage(path)
        if image.isNull():
            return
        # fill the monitor, cropping what doesn't fit, like the "fill" scaling mode
        scaled = image.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        source = QRect((scaled.width() - rect.width()) // 2, (scaled.height() - rect.height()) // 2,
                       rect.width(), rect.height())
        painter.drawImage(rect.translated(-union.topLeft()), scaled, source)

    if span_path:
        draw(span_path, union)
    for key, path in pieces.items():
        if key != SPAN and key in screens:
            draw(path, screens[key])
    painter.end()
    destination.parent.mkdir(parents=True, exist_ok=True)
    return canvas.save(str(destination), "PNG")


class StaticBackground(QObject):
    updated = Signal()
    supportedChanged = Signal()

    def __init__(self, settings, engine, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._engine = engine
        self._queue: list = []
        self._pieces: dict = {}
        self._span_path: str | None = None
        self._proc: QProcess | None = None
        self._timer = QTimer(self, singleShot=True, interval=SETTLE_MS)
        self._timer.timeout.connect(self._begin)
        self._watch = QTimer(self, interval=300)
        self._watch.timeout.connect(self._poll)
        self._deadline = QTimer(self, singleShot=True, interval=CAPTURE_TIMEOUT_MS)
        self._deadline.timeout.connect(self._give_up)
        engine.activeChanged.connect(self.schedule)
        settings.changed.connect(self.schedule)

    @Property(bool, notify=supportedChanged)
    def supported(self):
        """GNOME's background setting is available."""
        return gsettings("get", SCHEMA, "picture-uri") is not None

    # -- when to refresh -----------------------------------------------------------------------

    def _signature(self) -> str:
        """Changes whenever what is running (or how it is configured) changes."""
        props = self._engine._properties
        parts = [
            (key, path, tuple(props.engine_args(path)), tuple(sorted(props.engine_options(path).items())))
            for key, path in sorted(self._engine._assignments.items())
        ]
        parts.append((self._settings.get("scaling"), self._settings.get("clamping"), self._settings.get("layout")))
        screens = [(s.name(), s.geometry().getRect()) for s in QGuiApplication.screens()]
        return hashlib.sha1(repr((parts, screens)).encode()).hexdigest()

    @Slot()
    def schedule(self):
        if not self._settings.get("staticBackground") or not self._engine._assignments:
            return
        if self._proc is not None or self._signature() == self._settings.get("staticSignature"):
            return
        self._timer.start()  # restarts the wait while changes keep coming

    # -- capture -------------------------------------------------------------------------------

    def _begin(self):
        if self._proc is not None or not self._engine._assignments:
            return
        self._signature_at_start = self._signature()
        self._pieces = {}
        self._span_path = None
        self._queue = sorted(self._engine._assignments.items())
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self._next()

    def _next(self):
        if not self._queue:
            self._finish()
            return
        key, path = self._queue.pop(0)
        folder = Path(path)
        destination = OUTPUT_DIR / f"capture-{hashlib.sha1(key.encode()).hexdigest()[:8]}.png"
        destination.unlink(missing_ok=True)
        wallpaper = library.read_wallpaper(folder)
        if wallpaper and wallpaper.type == "video" and video_frame(folder, destination):
            self._store(key, destination)
            self._next()
            return
        self._start_engine_capture(key, path, destination)

    def _start_engine_capture(self, key, path, destination):
        exe = self._engine.binary()
        if not exe:
            self._fallback(key, path)
            return
        args = self._engine.build_args(path, key, audible=False) + [
            "--screenshot", str(destination), "--screenshot-delay", "5",
        ]
        proc = QProcess(self)
        if self._settings.get("windowed"):
            env = QProcessEnvironment.systemEnvironment()
            env.remove("WAYLAND_DISPLAY")
            env.insert("XDG_SESSION_TYPE", "x11")
            proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.start(exe, args)
        self._proc = proc
        self._current = (key, path, destination)
        self._watch.start()
        self._deadline.start()

    def _poll(self):
        key, path, destination = self._current
        if destination.is_file() and destination.stat().st_size > 0:
            self._release()
            self._store(key, destination)
            self._next()

    def _give_up(self):
        key, path, _destination = self._current
        self._release()
        self._fallback(key, path)

    def _release(self):
        self._watch.stop()
        self._deadline.stop()
        if self._proc is not None:
            proc, self._proc = self._proc, None
            proc.terminate()
            if not proc.waitForFinished(1500):
                proc.kill()

    def _fallback(self, key, path):
        """No capture: use the wallpaper's preview picture so the desktop still shows something sensible."""
        wallpaper = library.read_wallpaper(Path(path))
        if wallpaper and wallpaper.preview:
            self._store(key, wallpaper.preview)
        self._next()

    def _store(self, key, picture):
        if key == SPAN:
            self._span_path = str(picture)
        else:
            self._pieces[key] = str(picture)

    # -- result --------------------------------------------------------------------------------

    def _finish(self):
        screens = {s.name(): s.geometry() for s in QGuiApplication.screens()}
        # a new file name every time: GNOME reloads the background when the setting changes to a different URI
        destination = OUTPUT_DIR / f"static-background-{self._signature_at_start[:8]}.png"
        if not (self._pieces or self._span_path) or not compose(self._pieces, screens, self._span_path, destination):
            return
        self._settings.set("staticSignature", self._signature_at_start)
        self.apply_to_desktop(destination)
        for old in OUTPUT_DIR.glob("static-background-*.png"):
            if old != destination:
                old.unlink(missing_ok=True)
        self.updated.emit()

    def apply_to_desktop(self, image: Path):
        if gsettings("get", SCHEMA, "picture-uri") is None:
            return
        if not self._settings.get("originalBackground"):  # remember what the user had, once
            self._settings.set("originalBackground", {k: gsettings("get", SCHEMA, k) or "" for k in KEYS})
        uri = image.resolve().as_uri()
        gsettings("set", SCHEMA, "picture-uri", f"'{uri}'")
        gsettings("set", SCHEMA, "picture-uri-dark", f"'{uri}'")
        gsettings("set", SCHEMA, "picture-options", "'spanned'")

    @Slot()
    def restoreOriginal(self):
        """Give the desktop the background it had before the app first replaced it."""
        original = self._settings.get("originalBackground") or {}
        for key in KEYS:
            if original.get(key):
                gsettings("set", SCHEMA, key, original[key])
        self._settings.set("originalBackground", {})
        self._settings.set("staticSignature", "")
        self._settings.set("staticBackground", False)
