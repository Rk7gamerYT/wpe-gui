"""Install (or remove) the application menu entry and icons for the current user.

Without a .desktop file named after the app id (`wpe-gui`) the desktop shows a generic gear icon in the dock and the
app can't be found in the application menu. Everything goes under ~/.local/share, nothing needs administrator rights.
"""

import os
import shutil
import subprocess
from pathlib import Path

APP_ID = "wpe-gui"
ROOT = Path(__file__).resolve().parents[1]
ICONS = Path(__file__).resolve().parent / "assets/icons"
SIZES = (32, 48, 64, 128, 256, 512)


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def _targets() -> list[Path]:
    data = _data_home()
    paths = [data / "applications" / f"{APP_ID}.desktop", data / "icons/hicolor/scalable/apps" / f"{APP_ID}.svg"]
    paths += [data / f"icons/hicolor/{s}x{s}/apps/{APP_ID}.png" for s in SIZES]
    return paths


def _entry() -> str:
    launcher = os.environ.get("APPIMAGE") or str(ROOT / "wpe-gui.sh")
    if any(c in launcher for c in ' "\\'):
        launcher = '"' + launcher.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Wallpaper Engine",
        "GenericName=Wallpapers animados",
        "Comment=Wallpapers animados para o Linux",
        f"Exec={launcher}",
        f"Icon={APP_ID}",
        "Terminal=false",
        "Categories=Utility;",
        "Keywords=wallpaper;fundo;papel de parede;engine;",
        f"StartupWMClass={APP_ID}",
        "StartupNotify=false",
        "",
    ])


def _refresh_caches():
    data = _data_home()
    for cmd in (["update-desktop-database", str(data / "applications")],
                ["gtk-update-icon-cache", "-f", "-t", str(data / "icons/hicolor")]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, capture_output=True, timeout=30)


def install() -> list[Path]:
    desktop, svg, *pngs = _targets()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(_entry())
    written = [desktop]
    if (ICONS / "app.svg").is_file():
        svg.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ICONS / "app.svg", svg)
        written.append(svg)
    for size, target in zip(SIZES, pngs):
        source = ICONS / "png" / f"app-{size}.png"
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            written.append(target)
    _refresh_caches()
    return written


def uninstall() -> list[Path]:
    removed = []
    for path in _targets():
        if path.is_file():
            path.unlink()
            removed.append(path)
    _refresh_caches()
    return removed
