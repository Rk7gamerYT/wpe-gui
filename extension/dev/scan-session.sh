# Runs inside the throwaway session (see scan-wallpapers.sh)
ev() { gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval "$1" 2>&1; }
DISP=$(ev "GLib.getenv('DISPLAY')" | grep -oE ":[0-9]+" | head -1)
XA=$(ev "GLib.getenv('XAUTHORITY')" | grep -oE "/[^\"']+" | head -1)
OUT="$WPE_STATE/scan.tsv"; : > "$OUT"
while read -r dir; do
  id=$(basename "$dir"); log="$WPE_STATE/scan-$id.log"
  # setsid: the engine gets its own process group, so only this one is killed (never a real wallpaper of the user)
  ( export XAUTHORITY=$XA DISPLAY=$DISP XDG_SESSION_TYPE=x11; unset WAYLAND_DISPLAY
    setsid timeout -s KILL 14 linux-wallpaperengine --silent --fps 15 --assets-dir "$WPE_ASSETS" --window 0x0x1920x1080 --bg "$dir" > "$log" 2>&1 &
    echo $! > "$WPE_STATE/pid" )
  sleep 6
  win=$(ev "global.get_window_actors().filter(a => a.meta_window.get_title() === 'wallpaperengine').length" | grep -oE "'[0-9]+'" | tr -d "'")
  gdbus call --session --dest org.gnome.Shell.Screenshot --object-path /org/gnome/Shell/Screenshot --method org.gnome.Shell.Screenshot.Screenshot false false "$WPE_STATE/shot-$id.png" > /dev/null 2>&1
  kill -KILL -- -"$(cat "$WPE_STATE/pid")" 2>/dev/null
  err=$(grep -iE "error|fail|cannot|not found|unsupported|exception|missing" "$log" | head -1 | cut -c1-160)
  printf "%s\t%s\t%s\n" "$id" "${win:-0}" "$err" >> "$OUT"
  sleep 1
done < "$WPE_IDS_FILE"
