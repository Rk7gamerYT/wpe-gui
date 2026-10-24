#!/usr/bin/env bash
# Renders every scene wallpaper of a library one by one inside a throwaway headless GNOME Shell and reports
# which ones come out black or make the engine print errors.
#
#   WPE_ASSETS=/path/to/wallpaper_engine/assets WPE_IDS_FILE=ids.txt ./scan-wallpapers.sh
# Output: <state dir>/scan.tsv  (id <TAB> window <TAB> brightness <TAB> first error line)
set -euo pipefail
: "${WPE_ASSETS:?}" "${WPE_IDS_FILE:?one wallpaper folder per line}"
HERE=$(cd "$(dirname "$0")" && pwd)
export WPE_STATE=${WPE_STATE:-$(mktemp -d)}
UUID=wpe-background@wpe-gui
mkdir -p "$WPE_STATE"/{data/gnome-shell/extensions,config/glib-2.0/settings,state,cache}
ln -sfn "$HERE/../$UUID" "$WPE_STATE/data/gnome-shell/extensions/$UUID"
printf "[org/gnome/shell]\nenabled-extensions=['$UUID']\ndisable-user-extensions=false\nwelcome-dialog-last-shown-version='99'\n" > "$WPE_STATE/config/glib-2.0/settings/keyfile"
# unique Wayland socket per run, so overlapping runs never collide
export WPE_DISPLAY=wpe-$$-$RANDOM
export XDG_DATA_HOME=$WPE_STATE/data XDG_CONFIG_HOME=$WPE_STATE/config GSETTINGS_BACKEND=keyfile
export XDG_DATA_DIRS=$WPE_STATE/data:/usr/local/share:/usr/share XDG_STATE_HOME=$WPE_STATE/state XDG_CACHE_HOME=$WPE_STATE/cache
export WPE_IDS_FILE WPE_ASSETS HERE
echo "state dir: $WPE_STATE"
timeout "${WPE_SCAN_TIMEOUT:-1800}" dbus-run-session -- bash -c "
  gnome-shell --headless --wayland --wayland-display=$WPE_DISPLAY --unsafe-mode --virtual-monitor 1920x1080 > '$WPE_STATE/shell.log' 2>&1 &
  SH=\$!; sleep 8
  bash '$HERE/scan-session.sh' > '$WPE_STATE/scan.log' 2>&1
  kill \$SH 2>/dev/null; wait \$SH 2>/dev/null || true"
echo "done: $WPE_STATE/scan.tsv"
