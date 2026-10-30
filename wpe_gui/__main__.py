import os
import signal
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QSystemTrayIcon  # the tray needs the widgets application

from .updater import Updater
from .engine import Engine
from .kde import native_wayland, PlasmaDesktop
from .properties import PropertiesStore
from .powersaver import PowerSaver
from .staticbackground import StaticBackground
from .x11hints import WindowHider
from .models import WallpaperFilter, WallpaperModel
from .settings import Settings
from .tray import Tray, ask_running_instance_to_show
from .login_background import LoginBackground


def main() -> int:
    if "--self-test" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        test_app = QApplication([])
        from .engine_locator import locate_engine
        from . import __version__
        binary = locate_engine()
        if not binary:
            raise RuntimeError("O pacote não contém o motor.")
        result = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or "--audio-gain" not in result.stdout:
            raise RuntimeError("O motor empacotado não passou na verificação: " + result.stderr)
        print("wpe-gui", __version__, "Python/Qt/motor: OK")
        return 0
    if "--install-desktop" in sys.argv or "--uninstall-desktop" in sys.argv:
        from . import desktop_entry
        done = desktop_entry.install() if "--install-desktop" in sys.argv else desktop_entry.uninstall()
        verb = "instalado" if "--install-desktop" in sys.argv else "removido"
        print(f"{len(done)} arquivos {verb}s em ~/.local/share:", *[f"  {p}" for p in done], sep="\n")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("wpe-gui")
    app.setDesktopFileName("wpe-gui")
    app.setQuitOnLastWindowClosed(False)  # hiding the window to the tray must not end the app (see tray.py)
    # Quit properly on SIGTERM (logout, `kill`) and Ctrl+C: the default action would end this process and
    # leave the engines it started running with nobody to stop them
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    wake = QTimer()
    wake.timeout.connect(lambda: None)
    wake.start(250)  # gives Python a chance to run the signal handlers while Qt's loop is waiting

    # One instance only: each one would restore the saved wallpapers and the engines would pile up
    runtime = QStandardPaths.writableLocation(QStandardPaths.RuntimeLocation) or "/tmp"
    lock = QLockFile(os.path.join(runtime, "wpe-gui.lock"))
    if not lock.tryLock(200):
        if not ask_running_instance_to_show():  # normally the running app just brings its window up
            print("wpe-gui já está aberto.", file=sys.stderr)
        return 0

    updater = Updater()
    updater.restartRequested.connect(app.quit)
    app.aboutToQuit.connect(updater.shutdown)
    from .bundle import ensure_integrations
    try:
        ensure_integrations()
    except (OSError, subprocess.TimeoutExpired) as error:
        print("Integração do pacote:", error, file=sys.stderr)
    settings = Settings()
    properties = PropertiesStore()
    engine = Engine(settings, properties)
    login_background = LoginBackground(engine)
    login_background.message.connect(engine.message.emit)
    properties.changed.connect(engine.propertiesChanged)
    powersaver = PowerSaver(settings, engine)  # noqa: F841 (kept alive by the local reference)
    engine.plasma_desktop = PlasmaDesktop(settings, engine) if native_wayland() else None
    static_background = StaticBackground(settings, engine)
    window_hider = WindowHider(engine)  # noqa: F841 (kept alive by the local reference)
    model = WallpaperModel(settings)
    proxy = WallpaperFilter()
    proxy.setSourceModel(model)
    model.reload()

    qml = QQmlApplicationEngine()
    ctx = qml.rootContext()
    ctx.setContextProperty("updater", updater)
    ctx.setContextProperty("settings", settings)
    ctx.setContextProperty("backend", engine)
    ctx.setContextProperty("loginBackground", login_background)
    ctx.setContextProperty("properties", properties)
    ctx.setContextProperty("staticBackground", static_background)
    ctx.setContextProperty("library", model)
    ctx.setContextProperty("wallpapers", proxy)
    # Start hidden in the tray (setting or --minimized), but only when there is a tray to come back from
    start_hidden = ("--minimized" in sys.argv or settings.get("startHidden")) and QSystemTrayIcon.isSystemTrayAvailable()
    if start_hidden:
        qml.setInitialProperties({"visible": False})  # never show the window, instead of showing and hiding it
    qml.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml/Main.qml")))
    if not qml.rootObjects():
        return 1
    app.aboutToQuit.connect(engine.shutdown)
    tray = Tray(app, qml.rootObjects()[0], engine, settings)
    if start_hidden and tray.available:
        tray.hide_window()  # in case the initial property didn't keep it hidden
    if settings.get("restoreOnStart"):
        engine.restore()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
