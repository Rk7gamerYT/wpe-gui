"""Drives the app's Engine inside the throwaway shell (see session-test.sh): applies wallpapers like the UI would."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from wpe_gui.engine import Engine
from wpe_gui.powersaver import PowerSaver
from wpe_gui.properties import PropertiesStore
from wpe_gui.settings import Settings
from wpe_gui.x11hints import WindowHider
from wpe_gui.staticbackground import OUTPUT_DIR, StaticBackground, gsettings

app = QGuiApplication(sys.argv)
tmp = Path(tempfile.mkdtemp())
settings = Settings(tmp / "settings.json")
settings.set("windowed", True)
settings.set("silent", True)
settings.set("fps", 15)
settings.set("assetsDir", os.environ["WPE_ASSETS"])
settings.set("layout", os.environ.get("WPE_LAYOUT", "independent"))
engine = Engine(settings, PropertiesStore(tmp / "overrides.json"))
settings.set("powerSaving", os.environ.get("WPE_POWER", "maximized"))
engine.message.connect(lambda m: print("MESSAGE:", m, flush=True))
powersaver = PowerSaver(settings, engine)
static = StaticBackground(settings, engine)
hider = WindowHider(engine)
static.updated.connect(lambda: print('STATIC updated:', sorted(p.name for p in OUTPUT_DIR.glob('*.png')), flush=True))

first, second = os.environ["WPE_WALLPAPER"], os.environ.get("WPE_WALLPAPER2", os.environ["WPE_WALLPAPER"])
names = engine.screenNames()
print("qt screens:", [(s.name(), s.geometry().getRect()) for s in QGuiApplication.screens()], flush=True)
if settings.get("layout") == "independent" and len(names) > 1:
    engine.applyTo(first, names[0])
    engine.applyTo(second, names[1])
else:
    engine.applyTo(first, "")
print("assignments:", engine._assignments, "| summary:", engine.summary, flush=True)
print("args:", " ".join(engine.build_args(first, next(iter(engine._assignments)))[-6:]), flush=True)
def report():
    print("STATIC picture-uri:", gsettings("get", "org.gnome.desktop.background", "picture-uri"), flush=True)
    print("STATIC picture-options:", gsettings("get", "org.gnome.desktop.background", "picture-options"), flush=True)
    print("STATIC original saved:", settings.get("originalBackground"), flush=True)


QTimer.singleShot(int(os.environ.get("WPE_REPORT_SECONDS", "45")) * 1000, report)
QTimer.singleShot(int(os.environ.get("WPE_APP_SECONDS", "30")) * 1000, lambda: (engine.shutdown(), app.quit()))
app.exec()
