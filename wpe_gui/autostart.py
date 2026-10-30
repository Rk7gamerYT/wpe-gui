"""Manage the current user's XDG session autostart entry."""

import os
import sys
from pathlib import Path


def entry_path() -> Path:
    config = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(config) if config and Path(config).is_absolute() else Path.home() / ".config"
    return root / "autostart/wpe-gui.desktop"


def enabled() -> bool:
    return entry_path().is_file()


def _quote(argument: str) -> str:
    # Desktop Entry Exec quoting is different from shell quoting; '%' is a field code.
    for char in ('\\', '"', '`', '$'):
        argument = argument.replace(char, '\\' + char)
    return '"' + argument.replace('%', '%%') + '"'


def set_enabled(value: bool) -> None:
    entry = entry_path()
    if not value:
        entry.unlink(missing_ok=True)
        return
    root = Path(__file__).resolve().parent.parent
    launcher = root / "wpe-gui.sh"
    appimage = os.environ.get("APPIMAGE")
    command = [appimage] if appimage else ([str(launcher)] if launcher.is_file() else [sys.executable, "-m", "wpe_gui"])
    # Like Steam's -silent: starting with the session must not pop the window up, just live in the tray
    command.append("--minimized")
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Wallpaper Engine GUI\n"
        "Comment=Iniciar o aplicativo de wallpapers com a sessão\n"
        f"Exec={' '.join(_quote(arg) for arg in command)}\n"
        "Terminal=false\n"
    )
    entry.parent.mkdir(parents=True, exist_ok=True)
    temporary = entry.with_suffix(".desktop.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(entry)
