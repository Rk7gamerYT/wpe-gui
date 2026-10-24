import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .engine import Engine
from .properties import PropertiesStore
from .powersaver import PowerSaver
from .models import WallpaperFilter, WallpaperModel
from .settings import Settings


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("wpe-gui")
    app.setDesktopFileName("wpe-gui")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # One instance only: each one would restore the saved wallpapers and the engines would pile up
    runtime = QStandardPaths.writableLocation(QStandardPaths.RuntimeLocation) or "/tmp"
    lock = QLockFile(os.path.join(runtime, "wpe-gui.lock"))
    if not lock.tryLock(200):
        print("wpe-gui já está aberto.", file=sys.stderr)
        return 0

    settings = Settings()
    properties = PropertiesStore()
    engine = Engine(settings, properties)
    properties.changed.connect(engine.propertiesChanged)
    powersaver = PowerSaver(settings, engine)  # noqa: F841 (kept alive by the local reference)
    model = WallpaperModel(settings)
    proxy = WallpaperFilter()
    proxy.setSourceModel(model)
    model.reload()

    qml = QQmlApplicationEngine()
    ctx = qml.rootContext()
    ctx.setContextProperty("settings", settings)
    ctx.setContextProperty("backend", engine)
    ctx.setContextProperty("properties", properties)
    ctx.setContextProperty("library", model)
    ctx.setContextProperty("wallpapers", proxy)
    qml.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml/Main.qml")))
    if not qml.rootObjects():
        return 1
    app.aboutToQuit.connect(engine.shutdown)
    if settings.get("restoreOnStart"):
        engine.restore()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
