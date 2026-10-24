#!/usr/bin/env bash
# Installs the GNOME Shell extension for the current user. Log out and back in afterwards
# (GNOME on Wayland can't load new extensions without restarting the session).
set -e
UUID=wpe-background@wpe-gui
DEST="$HOME/.local/share/gnome-shell/extensions/$UUID"
mkdir -p "$DEST"
cp "$(dirname "$0")/$UUID/"* "$DEST/"
gnome-extensions enable "$UUID" || echo "Habilite depois de relogar: gnome-extensions enable $UUID"
