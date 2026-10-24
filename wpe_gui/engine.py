"""Runs and stops the linux-wallpaperengine backend process."""

import shutil

from PySide6.QtCore import QObject, QProcess, Property, Signal, Slot

from . import library


class Engine(QObject):
    runningChanged = Signal()
    currentChanged = Signal()
    message = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._proc: QProcess | None = None
        self._current = ""

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._proc is not None and self._proc.state() != QProcess.NotRunning

    @Property(str, notify=currentChanged)
    def current(self):
        return self._current

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
            args += ["--window", s.get("windowGeometry")]
        else:
            args += ["--screen-root", screen or s.get("screen")]
        args += ["--scaling", s.get("scaling"), "--clamp", s.get("clamping"), "--bg", path]
        return args

    @Slot(str)
    def apply(self, path: str):
        exe = self.binary()
        if not exe:
            self.message.emit("linux-wallpaperengine não encontrado. Defina o caminho em Configurações.")
            return
        self.stop()
        self._proc = QProcess(self)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(lambda _e: self.message.emit("Falha ao iniciar o motor."))
        self._proc.start(exe, self.build_args(path))
        self._current = path
        self.currentChanged.emit()
        self.runningChanged.emit()
        self._settings.set("lastWallpaper", path)

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
        self._proc = None
        self.runningChanged.emit()
        if code != 0:
            self.message.emit(f"O motor encerrou com código {code}.")
