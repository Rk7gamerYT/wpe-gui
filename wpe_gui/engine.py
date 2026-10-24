"""Runs and stops linux-wallpaperengine processes, one per target (monitor, or all monitors when spanning).

The engine accepts a single --window per process, so in window mode every monitor gets its own process.
"""

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import library

SPAN = "*"  # target key of the single process covering every monitor
LAYOUTS = ("independent", "duplicate", "span")


class Engine(QObject):
    activeChanged = Signal()
    message = Signal(str)

    def __init__(self, settings, properties, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._properties = properties
        self._procs: dict[str, QProcess] = {}
        self._assignments: dict[str, str] = {}  # target key -> wallpaper folder
        self._reapply = QTimer(self, singleShot=True, interval=500)
        self._reapply.timeout.connect(self._reapply_pending)
        self._pending: set[str] = set()

    # -- state exposed to QML ------------------------------------------------------------------

    @Property(bool, notify=activeChanged)
    def running(self):
        return bool(self._procs)

    @Property("QVariant", notify=activeChanged)
    def active(self):
        """Folders of the wallpapers currently running."""
        return sorted(set(self._assignments.values()))

    @Property(str, notify=activeChanged)
    def summary(self):
        """One line for the status bar, e.g. 'DP-5: Alone · HDMI-3: Crab Rave'."""
        def title(path):
            wp = library.read_wallpaper(Path(path))
            return wp.title if wp else Path(path).name
        names = {t: title(p) for t, p in self._assignments.items()}
        if len(set(names.values())) == 1 and len(names) > 1:
            return next(iter(names.values()))
        return " · ".join(names[t] if t == SPAN else f"{t}: {names[t]}" for t in sorted(names))

    @Slot(result="QVariant")
    def screenNames(self):
        return [s.name() for s in QGuiApplication.screens()]

    @Slot(str, result="QVariant")
    def targetsOf(self, path):
        """Monitors this wallpaper is running on (for the Apply menu)."""
        return [t for t, p in self._assignments.items() if p == path]

    # -- geometry ------------------------------------------------------------------------------

    @staticmethod
    def _geometry(screens) -> str:
        """X11 geometry XxYxWxH covering the given screens, in the layout xrandr reports."""
        x1 = min(s.geometry().x() for s in screens)
        y1 = min(s.geometry().y() for s in screens)
        x2 = max(s.geometry().x() + s.geometry().width() for s in screens)
        y2 = max(s.geometry().y() + s.geometry().height() for s in screens)
        return f"{x1}x{y1}x{x2 - x1}x{y2 - y1}"

    @staticmethod
    def _screens_by_name() -> dict:
        return {s.name(): s for s in QGuiApplication.screens()}

    # -- command line --------------------------------------------------------------------------

    def binary(self) -> str | None:
        custom = self._settings.get("enginePath")
        return custom if custom else shutil.which("linux-wallpaperengine")

    def build_args(self, path: str, target: str) -> list[str]:
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

        screens = self._screens_by_name()
        if target == SPAN:
            selected = list(screens.values())
        else:
            selected = [screens.get(target) or QGuiApplication.primaryScreen()]
        # --scaling/--clamp/--bg apply to the preceding --window/--screen-root/--screen-span
        if s.get("windowed"):
            args += ["--window", self._geometry(selected)]
        elif target == SPAN:
            args += ["--screen-span", ",".join(sc.name() for sc in selected)]
        else:
            args += ["--screen-root", selected[0].name()]

        options = self._properties.engine_options(path)
        args += [
            "--scaling", options.get("scaling") or s.get("scaling"),
            "--clamp", options.get("clamping") or s.get("clamping"),
            "--bg", path,
        ]
        return args + self._properties.engine_args(path)

    # -- starting and stopping -----------------------------------------------------------------

    def _targets_for(self, target: str) -> list[str]:
        """Process keys that applying to `target` ('' means every monitor) affects."""
        layout = self._settings.get("layout")
        if layout == "span":
            return [SPAN]
        names = [s.name() for s in QGuiApplication.screens()]
        if layout == "duplicate" or not target:
            return names
        return [target]

    @Slot(str)
    def apply(self, path: str):
        self.applyTo(path, "")

    @Slot(str, str)
    def applyTo(self, path: str, target: str):
        """Run `path` on a monitor ('' = all monitors); the layout setting decides how monitors are shared."""
        if not self.binary():
            self.message.emit("linux-wallpaperengine não encontrado. Defina o caminho em Configurações.")
            return
        keys = self._targets_for(target)
        if keys == [SPAN]:
            self._stop_keys([k for k in self._procs if k != SPAN])
        else:
            self._stop_keys([SPAN])
        self._stop_keys(keys)
        for key in keys:
            self._start(key, path)
        self._remember()

    def _start(self, key: str, path: str):
        proc = QProcess(self)
        if self._settings.get("windowed"):
            # GLEW can't initialise on native Wayland; run the window through XWayland
            env = QProcessEnvironment.systemEnvironment()
            env.remove("WAYLAND_DISPLAY")
            env.insert("XDG_SESSION_TYPE", "x11")
            proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.finished.connect(lambda code, _s, k=key, p=proc: self._on_finished(k, p, code))
        proc.errorOccurred.connect(lambda _e: self.message.emit("Falha ao iniciar o motor."))
        proc.start(self.binary(), self.build_args(path, key))
        self._procs[key] = proc
        self._assignments[key] = path
        self.activeChanged.emit()

    def _stop_keys(self, keys):
        procs = [(k, self._procs.pop(k)) for k in keys if k in self._procs]
        for _k, proc in procs:
            proc.finished.disconnect()
            proc.terminate()
        for k, proc in procs:  # terminate all first, then wait, so stopping N monitors doesn't take N x 2s
            if not proc.waitForFinished(2000):
                proc.kill()
            self._assignments.pop(k, None)
        if procs:
            self.activeChanged.emit()

    @Slot()
    def stop(self):
        self._stop_keys(list(self._procs))
        self._remember()

    def shutdown(self):
        """Stop the processes when the app quits, keeping what was saved so restore() can bring it back."""
        self._stop_keys(list(self._procs))

    @Slot(str)
    def stopPath(self, path: str):
        """Stop this wallpaper on every monitor it runs on, leaving the others alone."""
        self._stop_keys([k for k, p in self._assignments.items() if p == path])
        self._remember()

    def _remember(self):
        self._settings.set("assignments", dict(self._assignments))

    @Slot()
    def restore(self):
        """Start again what was running last time the app was open."""
        saved = self._settings.get("assignments") or {}
        names = set(self._screens_by_name())
        for key, path in saved.items():
            if (key == SPAN or key in names) and Path(path).is_dir():
                self._start(key, path)

    @Slot(str)
    def propertiesChanged(self, path: str):
        """Restart the running wallpaper so edited properties take effect (debounced while sliding)."""
        keys = [k for k, p in self._assignments.items() if p == path]
        if keys:
            self._pending.update(keys)
            self._reapply.start()

    def _reapply_pending(self):
        keys, self._pending = self._pending, set()
        for key in keys:
            path = self._assignments.get(key)
            if path:
                self._stop_keys([key])
                self._start(key, path)

    def _on_finished(self, key, proc, code):
        out = bytes(proc.readAll()).decode(errors="replace").strip().splitlines()
        if self._procs.get(key) is proc:
            del self._procs[key]
            self._assignments.pop(key, None)
            self.activeChanged.emit()
        if code != 0:
            tail = out[-1] if out else ""
            self.message.emit(f"O motor encerrou com código {code}. {tail}")
