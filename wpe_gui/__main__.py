import signal
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .engine import Engine
from .properties import PropertiesStore
from .models import WallpaperFilter, WallpaperModel
from .settings import Settings


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("wpe-gui")
    app.setDesktopFileName("wpe-gui")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    settings = Settings()
    properties = PropertiesStore()
    engine = Engine(settings, properties)
    properties.changed.connect(engine.propertiesChanged)
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
