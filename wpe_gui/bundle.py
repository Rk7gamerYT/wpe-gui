"""Register the integrations that are already shipped inside the single-file bundle."""
import os
from pathlib import Path
import shutil
import subprocess


def ensure_integrations():
    root = os.environ.get('WPE_BUNDLE_ROOT')
    if not root:
        return
    from . import autostart, desktop_entry
    from .kde import is_kde
    root = Path(root)
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if is_kde():
        for source, target in [(root / 'kde/wallpaper', data / 'plasma/wallpapers/org.wpegui.wallpaper'),
                               (root / 'kde/kwin', data / 'kwin/scripts/wpe-gui')]:
            shutil.copytree(source, target, dirs_exist_ok=True)
    elif 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
        if shutil.which('gnome-extensions'):
            subprocess.run(['bash', str(root / 'extension/install.sh')], capture_output=True, timeout=30)
    desktop_entry.install()
    if autostart.enabled():
        autostart.set_enabled(True)
