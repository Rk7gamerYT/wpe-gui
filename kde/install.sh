#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
data="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$data/plasma/wallpapers/org.wpegui.wallpaper" "$data/kwin/scripts/wpe-gui"
cp -a "$root/wallpaper/." "$data/plasma/wallpapers/org.wpegui.wallpaper/"
cp -a "$root/kwin/." "$data/kwin/scripts/wpe-gui/"
echo 'Plugin Plasma e extensão KWin instalados para o usuário atual.'
echo 'A extensão KWin é carregada pelo wpe-gui enquanto o aplicativo está aberto.'
