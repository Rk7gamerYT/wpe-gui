"""Runs and stops linux-wallpaperengine processes, one per target (monitor, or all monitors when spanning).

The engine accepts a single --window per process, so in window mode every monitor gets its own process.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import time
import signal
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import library
from .kde import native_wayland, screen_alias
from .engine_locator import locate_engine

SPAN = "*"  # target key of the single process covering every monitor
LAYOUTS = ("independent", "duplicate", "span")


class Engine(QObject):
    activeChanged = Signal()
    message = Signal(str)
    savedChanged = Signal()

    def __init__(self, settings, properties, parent=None):
        super().__init__(parent)
        self._log = logging.getLogger("wpe_gui.engine")
        if not self._log.handlers:
            log_dir = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "wpe-gui"
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                handler = RotatingFileHandler(log_dir / "engine.log", maxBytes=1_000_000, backupCount=2)
                handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
                self._log.addHandler(handler)
                self._log.setLevel(logging.INFO)
            except OSError:
                self._log.addHandler(logging.NullHandler())
        self._restarts = {}
        self._failures = {}
        self._output = {}
        self._started_at = {}
        self._settings = settings
        self._properties = properties
        settings.changed.connect(self.savedChanged.emit)
        self._procs: dict[str, QProcess] = {}
        self._assignments: dict[str, str] = {}  # target key -> wallpaper folder
        self._reapply = QTimer(self, singleShot=True, interval=500)
        self._reapply.timeout.connect(self._reapply_pending)
        self._pending: set[str] = set()
        self._paused: set[str] = set()  # target keys whose process is stopped (power saving)
        self._power_paused: set[str] = set()
        self._manual_paused: set[str] = set()
        self._pause_all = False
        self._audio_roles: dict[str, bool] = {}
        self._audio_sync = QTimer(self, singleShot=True, interval=0)
        self._audio_sync.timeout.connect(self._rebalance_audio)
        self._audio_settings = self._audio_settings_snapshot()
        settings.changed.connect(self._on_settings_changed)

    def _audio_settings_snapshot(self):
        return tuple(self._settings.get(key) for key in ("volume", "silent", "autoMute", "audioGain"))

    def _on_settings_changed(self):
        audio = self._audio_settings_snapshot()
        if audio == self._audio_settings:
            return
        self._audio_settings = audio
        self._pending.update(self._procs)
        if self._pending:
            self._reapply.start()

    # -- state exposed to QML ------------------------------------------------------------------

    @Property(bool, constant=True)
    def nativeDesktop(self):
        return native_wayland()

    @Property(bool, notify=savedChanged)
    def canRestore(self):
        return bool(self._settings.get("assignments"))

    @Property(bool, notify=activeChanged)
    def running(self):
        return bool(self._procs)

    @Property(bool, notify=activeChanged)
    def hasManualPause(self):
        return self._pause_all or bool(self._manual_paused & self._assignments.keys())

    @Property("QVariant", notify=activeChanged)
    def playbackTargets(self):
        return [{"key": key, "label": "Todos os monitores (estendido)" if key == SPAN else key,
                 "manuallyPaused": self._pause_all or key in self._manual_paused,
                 "paused": key in self._paused}
                for key in sorted(self._assignments)]

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
            text = next(iter(names.values()))
        else:
            text = " · ".join(names[t] if t == SPAN else f"{t}: {names[t]}" for t in sorted(names))
        if self._paused & set(self._assignments):
            text += " (pausado: " + ", ".join("todos os monitores" if t == SPAN else t
                                              for t in sorted(self._paused & set(self._assignments))) + ")"
        return text

    @Slot(result="QVariant")
    def runningTargets(self):
        return sorted(self._procs)

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

    def windowed(self):
        return bool(self._settings.get("windowed")) and not native_wayland()

    def binary(self) -> str | None:
        return locate_engine(self._settings.get("enginePath"))

    def build_args(self, path: str, target: str, audible: bool = True) -> list[str]:
        s = self._settings
        options = self._properties.engine_options(path)
        args = ["--fps", str(int(float(s.get("fps"))))]
        assets = s.get("assetsDir") or (str(a) if (a := library.default_assets_dir()) else "")
        if assets:
            args += ["--assets-dir", assets]
        sound = options.get("sound", "")
        silent = sound == "muted" or (sound != "enabled" and s.get("silent"))
        if silent or not audible:
            args.append("--silent")
        else:
            volume = options.get("volume")
            args += ["--volume", str(int(float(s.get("volume") if volume in (None, "") else volume)))]
        if not s.get("autoMute"):
            args.append("--noautomute")
        if s.get("disableMouse"):
            args.append("--disable-mouse")
        if s.get("powerSaving") == "off":
            args.append("--no-fullscreen-pause")

        screens = self._screens_by_name()
        if target == SPAN:
            selected = list(screens.values())
        else:
            selected = [screens.get(target) or QGuiApplication.primaryScreen()]
        # --scaling/--clamp/--bg apply to the preceding --window/--screen-root/--screen-span
        if self.windowed():
            args += ["--window", self._geometry(selected)]
        elif target == SPAN:
            args += ["--screen-span", ",".join(sc.name() for sc in selected)]
        else:
            args += ["--screen-root", selected[0].name()]

        if native_wayland():
            args += ["--layer", "background"]

        if library.audio_responsive(path):
            try:
                gain = float(options.get("audioGain") or s.get("audioGain"))
            except (TypeError, ValueError):
                gain = 1.0
            if gain != 1.0:
                args += ["--audio-gain", f"{gain:g}"]
        args += [
            "--scaling", options.get("scaling") or s.get("scaling"),
            "--clamp", options.get("clamping") or s.get("clamping"),
            "--bg", path,
        ]
        return args + self._properties.engine_args(path)

    # -- power saving --------------------------------------------------------------------------

    def setPausedTargets(self, wanted: set):
        """Update automatic pauses without clearing manual playback controls."""
        self._power_paused = set(wanted)
        self._update_pauses()

    def _wanted_pauses(self):
        manual = set(self._assignments) if self._pause_all else self._manual_paused
        return (manual | self._power_paused) & self._procs.keys()

    def _update_pauses(self):
        wanted = self._wanted_pauses()
        if wanted == self._paused:
            return
        for key in self._procs.keys() & (wanted | self._paused):
            self._signal(self._procs[key], signal.SIGSTOP if key in wanted else signal.SIGCONT)
        self._paused = wanted
        self._audio_sync.start()
        self.activeChanged.emit()

    @Slot(bool)
    def setGlobalPaused(self, paused):
        self._pause_all = paused
        if not paused:
            self._manual_paused.clear()
        self._update_pauses()
        self.activeChanged.emit()

    @Slot(str, bool)
    def setTargetPaused(self, key, paused):
        if key not in self._assignments:
            return
        if self._pause_all and not paused:
            self._manual_paused.update(self._assignments)
            self._pause_all = False
        if paused:
            self._manual_paused.add(key)
        else:
            self._manual_paused.discard(key)
        self._update_pauses()
        self.activeChanged.emit()

    def _process_started(self, key, proc):
        if self._procs.get(key) is proc and key in self._wanted_pauses():
            # QProcess.start() may return before a PID exists; apply the pause once it does.
            self._signal(proc, signal.SIGSTOP)
        self._update_pauses()

    @staticmethod
    def _signal(proc, sig):
        try:
            if proc.processId():
                os.kill(proc.processId(), sig)
        except ProcessLookupError:
            pass

    def _audible_targets(self):
        """One sound source per wallpaper, preferring a copy that is not paused."""
        groups = {}
        for key in sorted(self._procs):
            path = self._assignments.get(key)
            if path:
                groups.setdefault(str(Path(path).resolve()), []).append(key)
        audible = set()
        for keys in groups.values():
            candidates = [key for key in keys if key not in self._paused] or keys
            # Keep an existing source to avoid restarting it when another monitor is added.
            audible.add(next((key for key in candidates if self._audio_roles.get(key)), candidates[0]))
        return audible

    def _rebalance_audio(self):
        audible = self._audible_targets()
        changes = [key for key in self._procs if self._audio_roles.get(key) != (key in audible)]
        # Stop duplicate playback before enabling the replacement source.
        for key in sorted(changes, key=lambda key: key in audible):
            path = self._assignments.get(key)
            if not path:
                continue
            self._stop_keys([key])
            self._start(key, path, audio_owner=key in audible)

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
            self._stop_keys([k for k in self._assignments if k != SPAN])
        else:
            self._stop_keys([SPAN])
        self._stop_keys(keys)
        planned = set(self._assignments) | set(keys)
        for key in keys:
            self._start(key, path, planned)
        self._remember()

    def _start(self, key: str, path: str, planned=None, extra_args=None, audio_owner=None):
        planned = planned if planned is not None else set(self._assignments) | {key}
        proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        # Some scenes use audio shaders/scripts without declaring support in project.json.
        env.insert("WPE_AUDIO_PROCESSING", "1" if library.audio_responsive(path) else "0")
        if self.windowed():
            # GLEW can't initialise on native Wayland; run the window through XWayland
            env.remove("WAYLAND_DISPLAY")
            env.insert("XDG_SESSION_TYPE", "x11")
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.started.connect(lambda k=key, p=proc: self._process_started(k, p))
        proc.finished.connect(lambda code, _s, k=key, p=proc: self._on_finished(k, p, code))
        proc.readyReadStandardOutput.connect(lambda p=proc: self._read_output(p))
        proc.errorOccurred.connect(lambda error, k=key, p=proc: self._on_error(k, p, error))
        self._procs[key] = proc
        self._assignments[key] = path
        audible = key in self._audible_targets() if audio_owner is None else audio_owner
        self._audio_roles[key] = audible
        self._started_at[proc] = time.monotonic()
        self._output[proc] = b""
        proc.start(self.binary(), self.build_args(path, key, audible=audible) + (extra_args or []))
        self._update_pauses()
        self._audio_sync.start()
        self.activeChanged.emit()

    def captureWallpaper(self, path: str, destination: str) -> bool:
        """Restart one active target with the native capture option, preserving assignments."""
        keys = [key for key, folder in self._assignments.items() if folder == path]
        if not keys:
            self.message.emit("Aplique este wallpaper antes de usar a imagem na tela de login.")
            return False
        primary = QGuiApplication.primaryScreen().name()
        key = primary if primary in keys else keys[0]
        planned = set(self._assignments)
        self._stop_keys([key])
        self._start(key, path, planned, ["--screenshot", destination, "--screenshot-delay", "5"])
        return True

    def _stop_keys(self, keys):
        keys = list(keys)
        for key in keys:
            timer = self._restarts.pop(key, None)
            if timer:
                timer.stop()
                timer.deleteLater()
            self._failures.pop(key, None)
            self._assignments.pop(key, None)
            self._audio_roles.pop(key, None)
        procs = [(k, self._procs.pop(k)) for k in keys if k in self._procs]
        for k, proc in procs:
            proc.finished.disconnect()
            if k in self._paused:
                self._signal(proc, signal.SIGCONT)  # a stopped process would sit on the pending SIGTERM
                self._paused.discard(k)
            proc.terminate()
        for k, proc in procs:  # terminate all first, then wait, so stopping N monitors doesn't take N x 2s
            if not proc.waitForFinished(2000):
                proc.kill()
            proc.waitForFinished(1000)
            self._output.pop(proc, None)
            self._started_at.pop(proc, None)
            proc.deleteLater()
        if keys:
            self.activeChanged.emit()

    @Slot()
    def stop(self):
        self._manual_paused.clear()
        self._pause_all = False
        self._stop_keys(list(self._assignments))

    def shutdown(self):
        """Stop the processes when the app quits, keeping what was saved so restore() can bring it back."""
        self._stop_keys(list(self._assignments))
        self._audio_sync.stop()

    @Slot(str)
    def stopPath(self, path: str):
        """Stop this wallpaper on every monitor it runs on, leaving the others alone."""
        self._stop_keys([k for k, p in self._assignments.items() if p == path])
        self._manual_paused.intersection_update(self._assignments)
        self._audio_sync.start()

    def _remember(self):
        self._settings.set("assignments", dict(self._assignments))

    @Slot()
    def restore(self):
        """Restore the last applied monitor assignments without duplicating processes."""
        saved = self._settings.get("assignments") or {}
        names = set(self._screens_by_name())
        migrated = {}
        for key, path in saved.items():
            matches = [name for name in names if screen_alias(name) == screen_alias(key)]
            new_key = matches[0] if key not in names and len(matches) == 1 else key
            # Never replace an assignment already saved under the current connector name.
            if new_key != key and new_key in saved:
                continue
            migrated[new_key] = path
        if migrated != saved:
            self._settings.set("assignments", migrated)
        saved = migrated
        valid = {k: p for k, p in saved.items() if (k == SPAN or k in names) and Path(p).is_dir()}
        if not valid:
            self.message.emit("Nenhum wallpaper salvo disponível nos monitores conectados.")
            return
        if not self.binary():
            self.message.emit("linux-wallpaperengine não encontrado. Defina o caminho em Configurações.")
            return
        # Leave already running targets alone; repeated Restore clicks are harmless.
        if SPAN in valid:
            self._stop_keys([k for k in self._assignments if k != SPAN])
        else:
            self._stop_keys([SPAN])
        for key, path in valid.items():
            if self._assignments.get(key) == path:
                continue
            self._stop_keys([key])
            self._start(key, path, planned=set(valid) | set(self._assignments))

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
                self._start(key, path, planned=set(self._assignments) | {key})

    def _read_output(self, proc):
        # Drain continuously so a verbose engine cannot grow Qt's buffer indefinitely.
        chunk = bytes(proc.readAllStandardOutput())
        self._output[proc] = (self._output.get(proc, b"") + chunk)[-8192:]

    def _on_error(self, key, proc, error):
        if error == QProcess.FailedToStart:
            self._on_finished(key, proc, -1)

    def _retry(self, key, path, timer):
        if self._restarts.get(key) is not timer:
            return
        del self._restarts[key]
        timer.deleteLater()
        if self._assignments.get(key) == path:
            self._start(key, path, planned=set(self._assignments))

    def _on_finished(self, key, proc, code):
        self._read_output(proc)
        out = self._output.pop(proc, b"").decode(errors="replace").strip()
        uptime = time.monotonic() - self._started_at.pop(proc, time.monotonic())
        if self._procs.get(key) is not proc:
            proc.deleteLater()
            return
        del self._procs[key]
        self._audio_roles.pop(key, None)
        self._audio_sync.start()
        self._paused.discard(key)
        path = self._assignments[key]
        attempts = (0 if uptime >= 120 else self._failures.get(key, 0)) + 1
        self._failures[key] = attempts
        self._log.error("target=%s exit=%s uptime=%.1fs attempt=%s error=%s\n%s",
                        key, code, uptime, attempts, proc.errorString(), out)
        if attempts <= 3:
            timer = QTimer(self, singleShot=True, interval=1000 * 2 ** (attempts - 1))
            timer.timeout.connect(lambda: self._retry(key, path, timer))
            self._restarts[key] = timer
            timer.start()
            self.message.emit(f"O motor encerrou em {key}. Reiniciando ({attempts}/3)…")
        else:
            self._assignments.pop(key, None)
            self.message.emit(f"O motor falhou repetidamente em {key}. Aplique o wallpaper novamente. {out[-500:]}")
        self.activeChanged.emit()
        proc.deleteLater()
