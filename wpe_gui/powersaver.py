"""Power saving: pause the wallpaper on monitors that have a maximized or fullscreen app.

GNOME doesn't let ordinary programs see other windows, so the GNOME Shell extension (extension/) watches them and
publishes, over D-Bus, the monitors that are covered. Without the extension nothing is ever reported covered and
nothing is paused.
"""

import json
import os
import sys

from PySide6.QtCore import SLOT, QObject, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusServiceWatcher
from PySide6.QtGui import QGuiApplication

from .engine import SPAN

SERVICE = "org.wpegui.Background"
PATH = "/org/wpegui/Background"
MODES = ("off", "fullscreen", "maximized")


class PowerSaver(QObject):
    def __init__(self, settings, engine, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._engine = engine
        self._covered = {"maximized": [], "fullscreen": []}

        bus = QDBusConnection.sessionBus()
        connected = bus.connect(SERVICE, PATH, SERVICE, "CoveredChanged", self, SLOT("onCoveredChanged(QString)"))
        if os.environ.get("WPE_DEBUG"):
            print(f"[powersaver] connect CoveredChanged -> {connected}", file=sys.stderr, flush=True)
        # The extension may start later (or the shell restart): fetch the state whenever the service appears
        self._watcher = QDBusServiceWatcher(
            SERVICE, bus, QDBusServiceWatcher.WatchModeFlag.WatchForRegistration, self
        )
        self._watcher.serviceRegistered.connect(lambda _name: self._fetch())

        settings.changed.connect(self.update)
        engine.activeChanged.connect(self.update)
        self._fetch()

    def _fetch(self):
        reply = QDBusInterface(SERVICE, PATH, SERVICE, QDBusConnection.sessionBus()).call("GetCovered")
        args = reply.arguments()
        if args:
            self.onCoveredChanged(str(args[0]))

    @Slot(str)
    def onCoveredChanged(self, text: str):
        try:
            data = json.loads(text)
            self._covered = {"maximized": data.get("maximized", []), "fullscreen": data.get("fullscreen", [])}
        except (ValueError, AttributeError):
            return
        self.update()

    def covered_screens(self) -> set[str]:
        """Names of the screens covered according to the chosen mode."""
        mode = self._settings.get("powerSaving")
        if mode not in ("fullscreen", "maximized"):
            return set()
        rects = [tuple(r) for r in self._covered["fullscreen"]]
        if mode == "maximized":
            rects += [tuple(r) for r in self._covered["maximized"]]
        names = set()
        for screen in QGuiApplication.screens():
            g = screen.geometry()
            if (g.x(), g.y(), g.width(), g.height()) in rects:
                names.add(screen.name())
        return names

    def wanted_pauses(self) -> set[str]:
        covered = self.covered_screens()
        every = {s.name() for s in QGuiApplication.screens()}
        wanted = set(covered)
        if covered and covered >= every:  # a spanned wallpaper only pauses when nothing of it is visible
            wanted.add(SPAN)
        return wanted

    @Slot()
    def update(self):
        wanted = self.wanted_pauses()
        if os.environ.get("WPE_DEBUG"):
            print(f"[powersaver] mode={self._settings.get('powerSaving')} covered={self._covered} wanted={sorted(wanted)} "
                  f"targets={self._engine.runningTargets()}", file=sys.stderr, flush=True)
        self._engine.setPausedTargets(wanted)
