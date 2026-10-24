# Runs inside the throwaway session (see test-shell.sh): starts the engine and an ordinary app, then reports.
ev() { gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval "$1" 2>&1 | cut -c1-500; }
shot() { gdbus call --session --dest org.gnome.Shell.Screenshot --object-path /org/gnome/Shell/Screenshot --method org.gnome.Shell.Screenshot.Screenshot false false "$1" > /dev/null 2>&1; }
DISP=$(ev "GLib.getenv('DISPLAY')" | grep -oE ":[0-9]+" | head -1)
XA=$(ev "GLib.getenv('XAUTHORITY')" | grep -oE "/[^\"']+" | head -1)
( export XAUTHORITY=$XA DISPLAY=$DISP XDG_SESSION_TYPE=x11; unset WAYLAND_DISPLAY
  nice -n 10 timeout 45 linux-wallpaperengine --silent --fps 15 --assets-dir "$WPE_ASSETS" \
    --window 0x0x1920x1080 --bg "$WPE_WALLPAPER" > "$WPE_STATE/engine.log" 2>&1 & )
sleep 8
( unset DISPLAY XAUTHORITY; export WAYLAND_DISPLAY=wpe-test XDG_SESSION_TYPE=wayland
  gnome-text-editor --new-window > "$WPE_STATE/editor.log" 2>&1 & )
sleep 6
shot "$WPE_STATE/shot-apps.png"
echo "== layer order (bottom to top)"
ev "Main.layoutManager._backgroundGroup.get_children().map(c => c.constructor.name+'('+c.x+','+c.y+' '+c.width+'x'+c.height+')').join(' < ')"
echo "== minimize the wallpaper (must be restored)"
ev "(() => { const w = global.get_window_actors().map(a => a.meta_window).find(w => w.get_title() === 'wallpaperengine'); w.minimize(); return 'minimize()'; })()"; sleep 2
ev "(() => { const a = global.get_window_actors().find(a => a.meta_window.get_title() === 'wallpaperengine'); return 'minimized='+a.meta_window.minimized+' visible='+a.visible; })()"
echo "== overview"; ev "Main.overview.show(); 'ok'"; sleep 3; shot "$WPE_STATE/shot-overview.png"
