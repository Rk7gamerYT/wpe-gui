"""Plasma wallpaper and KWin integration, scoped to the current user session."""
import json
import os
from pathlib import Path

from PySide6.QtCore import ClassInfo, QObject, QTimer, Slot
from PySide6.QtDBus import QDBusAbstractAdaptor, QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtGui import QGuiApplication

PLUGIN = "org.wpegui.wallpaper"
SERVICE = "org.wpegui.KWin"
OBJECT = "/org/wpegui/KWin"


def is_kde():
    return "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")


def native_wayland():
    return is_kde() and os.environ.get("XDG_SESSION_TYPE") == "wayland"


def screen_alias(name):
    # Mutter and KWin use different connector names for the same HDMI output.
    return name.replace("HDMI-A-", "HDMI-")


def plasma_script(script):
    reply = QDBusInterface("org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell",
                           QDBusConnection.sessionBus()).call("evaluateScript", script)
    if reply.type() == QDBusMessage.ErrorMessage:
        raise RuntimeError(reply.errorMessage())
    return str(reply.arguments()[0]) if reply.arguments() else ""


@ClassInfo(**{"D-Bus Interface": SERVICE})
class CoverageAdaptor(QDBusAbstractAdaptor):
    @Slot(result=str)
    def GetCovered(self):
        return json.dumps(self.parent()._covered)

    @Slot(str)
    def ReportCovered(self, text):
        self.parent().onCoveredChanged(text)


class KWinBridge(QObject):
    def __init__(self, powersaver):
        super().__init__(powersaver)
        self.bus = QDBusConnection.sessionBus()
        self.adaptor = CoverageAdaptor(powersaver)
        self.registered = self.bus.registerService(SERVICE)
        self.loaded = False
        if not self.registered:
            return
        self.bus.registerObject(OBJECT, powersaver, QDBusConnection.ExportAdaptors)
        self.start()
        self.watcher = QTimer(self, interval=10000)
        self.watcher.timeout.connect(self.start)
        self.watcher.start()
        QGuiApplication.instance().aboutToQuit.connect(self.close)

    def interface(self):
        return QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", self.bus)

    def start(self):
        interface = self.interface()
        reply = interface.call("isScriptLoaded", "wpe-gui")
        if reply.arguments() and reply.arguments()[0] is True:
            if self.loaded:
                return
            # A previous app crash may leave a script with a stale initial report.
            interface.call("unloadScript", "wpe-gui")
        data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home()/".local/share")))
        path = data / "kwin/scripts/wpe-gui/contents/code/main.js"
        if not path.is_file():
            return
        reply = interface.call("loadScript", str(path), "wpe-gui")
        if reply.type() != QDBusMessage.ErrorMessage and reply.arguments() and int(reply.arguments()[0]) >= 0:
            number = int(reply.arguments()[0])
            runner = QDBusInterface("org.kde.KWin", f"/Scripting/Script{number}", "org.kde.kwin.Script", self.bus)
            result = runner.call("run")
            self.loaded = result.type() != QDBusMessage.ErrorMessage

    def close(self):
        self.watcher.stop()
        if self.loaded:
            self.interface().call("unloadScript", "wpe-gui")
        self.bus.unregisterObject(OBJECT)
        self.bus.unregisterService(SERVICE)


class PlasmaDesktop(QObject):
    """Keep Plasma's wallpaper transparent only while its engine is alive."""
    def __init__(self, settings, engine):
        super().__init__(engine)
        self.settings, self.engine = settings, engine
        self.timer = QTimer(self, singleShot=True, interval=150)
        self.timer.timeout.connect(self.update)
        engine.activeChanged.connect(self.timer.start)
        QGuiApplication.instance().aboutToQuit.connect(self.close)

    def snapshot(self):
        if self.settings.get("originalKdeBackground"):
            return
        text = plasma_script('''print(JSON.stringify(desktops().map(function(d) {
            var p = d.wallpaperPlugin;
            d.currentConfigGroup = ["Wallpaper", p, "General"];
            return {id:d.id, plugin:p, image:d.readConfig("Image", ""),
                    color:d.readConfig("Color", "#202124"), fill:d.readConfig("FillMode", 2)};
        })))''')
        self.settings.set("originalKdeBackground", json.loads(text))

    def update(self, stopped=False):
        if not native_wayland():
            return
        data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home()/".local/share")))
        if not (data / "plasma/wallpapers" / PLUGIN / "metadata.json").is_file():
            self.engine.message.emit("Instale a integração KDE com ./kde/install.sh antes de aplicar o wallpaper.")
            return
        targets = self.engine.runningTargets() if not stopped else []
        images = self.settings.get("kdeStaticImages") or {}
        entries = []
        for screen in QGuiApplication.screens():
            entries.append(dict(rect=list(screen.geometry().getRect()),
                                running=screen.name() in targets or "*" in targets,
                                image=images.get(screen.name(), "")))
        try:
            if not targets and not self.settings.get("originalKdeBackground"):
                return
            self.snapshot()
            plasma_script('''var entries = %s;
                desktops().forEach(function(d) {
                    var g = screenGeometry(d.screen);
                    var e = entries.find(function(e) {
                        return e.rect[0] === g.x && e.rect[1] === g.y &&
                               e.rect[2] === g.width && e.rect[3] === g.height;
                    });
                    if (!e) return;
                    if (!e.running && d.wallpaperPlugin !== %s) return;
                    d.wallpaperPlugin = %s;
                    d.currentConfigGroup = ["Wallpaper", %s, "General"];
                    d.writeConfig("Image", e.image);
                    d.writeConfig("Running", e.running);
                });''' % (json.dumps(entries), json.dumps(PLUGIN), json.dumps(PLUGIN), json.dumps(PLUGIN)))
        except (RuntimeError, ValueError) as exc:
            self.engine.message.emit(f"Não foi possível atualizar o fundo do Plasma: {exc}")

    def close(self):
        self.timer.stop()
        self.update(stopped=True)

    def restore(self):
        originals = self.settings.get("originalKdeBackground") or []
        plasma_script('''var originals = %s;
            desktops().forEach(function(d) {
                var o = originals.find(function(o) { return o.id === d.id; });
                if (!o) return;
                d.wallpaperPlugin = o.plugin;
                d.currentConfigGroup = ["Wallpaper", o.plugin, "General"];
                d.writeConfig("Image", o.image);
                d.writeConfig("Color", o.color);
                d.writeConfig("FillMode", o.fill);
            });''' % json.dumps(originals))
        self.settings.set("originalKdeBackground", [])
