"""Runs and stops the linux-wallpaperengine backend process."""

import shutil

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import library


class Engine(QObject):
    runningChanged = Signal()
    currentChanged = Signal()
    message = Signal(str)

    def __init__(self, settings, properties, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._properties = properties
        self._reapply = QTimer(self, singleShot=True, interval=500)
        self._reapply.timeout.connect(lambda: self.apply(self._current))
        self._proc: QProcess | None = None
        self._current = ""

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._proc is not None and self._proc.state() != QProcess.NotRunning

    @Property(str, notify=currentChanged)
    def current(self):
        return self._current

    @Slot(result="QVariant")
    def screenNames(self):
        return [s.name() for s in QGuiApplication.screens()]

    def _screen(self, name: str):
        screens = QGuiApplication.screens()
        return next((s for s in screens if s.name() == name), QGuiApplication.primaryScreen())

    def window_geometry(self) -> str:
        """X11 geometry (XxYxWxH) covering the chosen monitor, in the layout xrandr reports."""
        g = self._screen(self._settings.get("screen")).geometry()
        return f"{g.x()}x{g.y()}x{g.width()}x{g.height()}"

    def binary(self) -> str | None:
        custom = self._settings.get("enginePath")
        return custom if custom else shutil.which("linux-wallpaperengine")

    def build_args(self, path: str, screen: str | None = None) -> list[str]:
        s = self._settings
        args = ["--fps", str(s.get("fps"))]
        assets = s.get("assetsDir") or (str(a) if (a := library.default_assets_dir()) else "")
        if assets:
            args += ["--assets-dir", assets]
        if s.get("silent"):
            args.append("--silent")
        else:
            args += ["--volume", str(s.get("volume"))]
        if not s.get("autoMute"):
            args.append("--noautomute")
        if s.get("disableMouse"):
            args.append("--disable-mouse")
        if not s.get("pauseOnFullscreen"):
            args.append("--no-fullscreen-pause")
        # --scaling/--clamp/--bg apply to the preceding --window/--screen-root
        if s.get("windowed"):
            args += ["--window", self.window_geometry()]
        else:
            args += ["--screen-root", screen or self._screen(s.get("screen")).name()]
        args += ["--scaling", s.get("scaling"), "--clamp", s.get("clamping"), "--bg", path]
        return args + self._properties.engine_args(path)

    @Slot(str)
    def apply(self, path: str):
        exe = self.binary()
        if not exe:
            self.message.emit("linux-wallpaperengine não encontrado. Defina o caminho em Configurações.")
            return
        self.stop()
        self._proc = QProcess(self)
        if self._settings.get("windowed"):
            # GLEW can't initialise on native Wayland; run the window through XWayland
            env = QProcessEnvironment.systemEnvironment()
            env.remove("WAYLAND_DISPLAY")
            env.insert("XDG_SESSION_TYPE", "x11")
            self._proc.setProcessEnvironment(env)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(lambda _e: self.message.emit("Falha ao iniciar o motor."))
        self._proc.start(exe, self.build_args(path))
        self._current = path
        self.currentChanged.emit()
        self.runningChanged.emit()
        self._settings.set("lastWallpaper", path)

    @Slot(str)
    def propertiesChanged(self, path: str):
        """Restart the running wallpaper so edited properties take effect (debounced while sliding)."""
        if self.running and path == self._current:
            self._reapply.start()

    @Slot()
    def stop(self):
        if self._proc is not None:
            self._proc.finished.disconnect(self._on_finished)
            self._proc.terminate()
            if not self._proc.waitForFinished(2000):
                self._proc.kill()
            self._proc = None
            self.runningChanged.emit()

    def _on_finished(self, code, _status):
        out = bytes(self._proc.readAll()).decode(errors="replace").strip().splitlines()
        self._proc = None
        self.runningChanged.emit()
        if code != 0:
            tail = out[-1] if out else ""
            self.message.emit(f"O motor encerrou com código {code}. {tail}")
