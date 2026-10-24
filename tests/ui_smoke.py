"""Loads the QML UI offscreen with a real wallpaper selected and fails on any QML error.

    QT_QPA_PLATFORM=offscreen .venv/bin/python tests/ui_smoke.py [wallpaper folder]
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from wpe_gui.engine import Engine
from wpe_gui.models import WallpaperFilter, WallpaperModel
from wpe_gui.powersaver import PowerSaver
from wpe_gui.properties import PropertiesStore
from wpe_gui.settings import Settings
from wpe_gui.staticbackground import StaticBackground

try:  # present only in builds that have the login background feature
    from wpe_gui.login_background import LoginBackground
except ImportError:
    LoginBackground = None

messages = []
qInstallMessageHandler(lambda mode, ctx, text: messages.append(text))
app = QGuiApplication(sys.argv)
tmp = Path(tempfile.mkdtemp())
settings = Settings(tmp / "settings.json")
properties = PropertiesStore(tmp / "overrides.json")
engine = Engine(settings, properties)
powersaver = PowerSaver(settings, engine)
static_background = StaticBackground(settings, engine)
login_background = LoginBackground(engine) if LoginBackground else None
model = WallpaperModel(settings)
proxy = WallpaperFilter()
proxy.setSourceModel(model)
model.reload()

qml = QQmlApplicationEngine()
ctx = qml.rootContext()
contexts = dict(settings=settings, backend=engine, properties=properties, library=model, wallpapers=proxy,
                staticBackground=static_background)
if login_background:
    contexts["loginBackground"] = login_background
for name, obj in contexts.items():
    ctx.setContextProperty(name, obj)
qml.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "wpe_gui/qml/Main.qml")))
root = qml.rootObjects()[0]
folder = sys.argv[1] if len(sys.argv) > 1 else (str(model._items[0].path) if model._items else "")
root.setProperty("selected", {"title": "t", "preview": "", "path": folder, "wtype": "scene", "description": "d", "tags": ""})


def finish():
    errors = [m for m in messages if any(x in m for x in ("qml:", "TypeError", "ReferenceError", "Unable", "is not"))]
    print("QML errors:", len(errors))
    for m in errors:
        print("  !", m[:200])
    engine.shutdown()
    app.exit(1 if errors else 0)


QTimer.singleShot(2500, finish)
sys.exit(app.exec())
