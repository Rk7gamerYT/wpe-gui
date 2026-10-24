#!/usr/bin/env bash
# Runs the extension inside a throwaway headless GNOME Shell, so it can be tested without logging out.
# Settings and D-Bus are isolated: nothing here touches your real session.
#
# Spanning one window over all monitors: WPE_LAYOUT=span
# Several monitors: WPE_VIRTUAL_MONITORS="1080x1920 1920x1080" (default: one 1920x1080 monitor).
#   WPE_WALLPAPER=/path/to/workshop/content/431960/<id> \
#   WPE_ASSETS=/path/to/wallpaper_engine/assets ./test-shell.sh
#
# Output: <state dir>/test.log (scene dump), shot-apps.png and shot-overview.png (screenshots), shell.log
set -euo pipefail
: "${WPE_WALLPAPER:?set WPE_WALLPAPER to a wallpaper folder}" "${WPE_ASSETS:?set WPE_ASSETS to the Wallpaper Engine assets folder}"
HERE=$(cd "$(dirname "$0")" && pwd)
export WPE_STATE=${WPE_STATE:-$(mktemp -d)}
UUID=wpe-background@wpe-gui
mkdir -p "$WPE_STATE"/{data/gnome-shell/extensions,config/glib-2.0/settings,state,cache,Desktop}
ln -sfn "$HERE/../$UUID" "$WPE_STATE/data/gnome-shell/extensions/$UUID"
touch "$WPE_STATE/Desktop/Documento.txt"; mkdir -p "$WPE_STATE/Desktop/Projetos"
printf 'XDG_DESKTOP_DIR="%s/Desktop"\n' "$WPE_STATE" > "$WPE_STATE/config/user-dirs.dirs"
cat > "$WPE_STATE/config/glib-2.0/settings/keyfile" <<KEYS
[org/gnome/shell]
enabled-extensions=['$UUID', 'ding@rastersoft.com'${WPE_EXTENSIONS:+, $WPE_EXTENSIONS}]
disable-user-extensions=false
welcome-dialog-last-shown-version='99'
KEYS
# unique Wayland socket per run, so overlapping runs never collide
export WPE_DISPLAY=wpe-$$-$RANDOM
export XDG_DATA_HOME=$WPE_STATE/data XDG_CONFIG_HOME=$WPE_STATE/config GSETTINGS_BACKEND=keyfile
export XDG_DATA_DIRS=$WPE_STATE/data:/usr/local/share:/usr/share XDG_STATE_HOME=$WPE_STATE/state XDG_CACHE_HOME=$WPE_STATE/cache
export WPE_VIRTUAL_MONITORS=${WPE_VIRTUAL_MONITORS:-1920x1080}
MON_FLAGS=""; for m in $WPE_VIRTUAL_MONITORS; do MON_FLAGS="$MON_FLAGS --virtual-monitor $m"; done
echo "state dir: $WPE_STATE | monitors: $WPE_VIRTUAL_MONITORS"
timeout 150 dbus-run-session -- bash -c "
  gnome-shell --headless --wayland --wayland-display=$WPE_DISPLAY --unsafe-mode $MON_FLAGS > '$WPE_STATE/shell.log' 2>&1 &
  SH=\$!; sleep 8
  bash '$HERE/session-test.sh' > '$WPE_STATE/test.log' 2>&1
  kill \$SH 2>/dev/null; wait \$SH 2>/dev/null || true"
cat "$WPE_STATE/test.log"
grep '\[wpe-background\]' "$WPE_STATE/shell.log" | cut -d: -f4- || true
