# Runs inside the throwaway session (see test-shell.sh): starts the engine and an ordinary app, then reports.
ev() { gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval "$1" 2>&1 | cut -c1-500; }
shot() { gdbus call --session --dest org.gnome.Shell.Screenshot --object-path /org/gnome/Shell/Screenshot --method org.gnome.Shell.Screenshot.Screenshot false false "$1" > /dev/null 2>&1; }
DISP=$(ev "GLib.getenv('DISPLAY')" | grep -oE ":[0-9]+" | head -1)
XA=$(ev "GLib.getenv('XAUTHORITY')" | grep -oE "/[^\"']+" | head -1)
if [ -n "${WPE_APP:-}" ]; then
  # Drive the app's own Engine (per-monitor processes, layouts) instead of launching the engine by hand
  ( export XAUTHORITY=$XA DISPLAY=$DISP QT_QPA_PLATFORM=wayland WAYLAND_DISPLAY=wpe-test
    "${WPE_PYTHON:-python3}" "$(dirname "$0")/app-test.py" > "$WPE_STATE/app.log" 2>&1 & )
else
# One engine window per monitor, positioned from the geometry the shell reports
MONS=$(ev "JSON.stringify(Main.layoutManager.monitors.map(m => [m.x, m.y, m.width, m.height]))" | grep -oE "\[\[.*\]\]" | sed 's/\\//g')
echo "== monitors: $MONS"
# Extra engine arguments, shell-quoted in WPE_ENGINE_ARGS (values may contain spaces)
eval "EXTRA=(${WPE_ENGINE_ARGS:-})"
# The engine accepts a single --window per process, so start one process per monitor
i=0
# WPE_LAYOUT=span: a single window covering every monitor
GEOMS=$(python3 -c "
import json, sys
mons = json.loads(sys.argv[1])
if sys.argv[2] == 'span':
    x1 = min(m[0] for m in mons); y1 = min(m[1] for m in mons)
    x2 = max(m[0] + m[2] for m in mons); y2 = max(m[1] + m[3] for m in mons)
    mons = [[x1, y1, x2 - x1, y2 - y1]]
print(' '.join('%dx%dx%dx%d' % tuple(m) for m in mons))" "$MONS" "${WPE_LAYOUT:-independent}")
echo "== geometries: $GEOMS"
for geom in $GEOMS; do
  ( export XAUTHORITY=$XA DISPLAY=$DISP XDG_SESSION_TYPE=x11; unset WAYLAND_DISPLAY
    nice -n 10 timeout ${WPE_ENGINE_SECONDS:-45} linux-wallpaperengine ${WPE_SILENT---silent} --fps 15 --assets-dir "$WPE_ASSETS" \
      --window "$geom" --bg "$WPE_WALLPAPER" "${EXTRA[@]}" > "$WPE_STATE/engine-$i.log" 2>&1 & )
  i=$((i+1))
done
fi
sleep ${WPE_SETTLE:-8}
( unset DISPLAY XAUTHORITY; export WAYLAND_DISPLAY=wpe-test XDG_SESSION_TYPE=wayland
  gnome-text-editor --new-window > "$WPE_STATE/editor.log" 2>&1 & )
sleep 6
shot "$WPE_STATE/shot-apps.png"
echo "== processos do motor"
ps -eo pid,stat,etime,pcpu,comm,args | grep -E "[l]inux-wallpaper|[c]ef|[c]hrome|[s]ubprocess" | cut -c1-180
PID=$(ps -eo pid,comm,args | awk '$2=="linux-wallpaper" && /0x0x1920x1080|1080x0x1920x1080|0x0x1080x1920|0x0x3000x1920/ {print $1; exit}')
echo "== pilha do motor (pid ${PID:-?})"
[ -n "$PID" ] && gdb -p "$PID" -batch -ex "thread apply all bt 14" 2>&1 | grep -E "^#|^Thread" | cut -c1-200 | head -40
echo "== audio streams (PipeWire)"
pw-dump 2>/dev/null | python3 -c "
import json,sys
for o in json.load(sys.stdin):
    i=o.get('info',{}); p=i.get('props',{})
    if p.get('media.class')=='Stream/Output/Audio':
        props=[x for x in i.get('params',{}).get('Props',[])]
        print(p.get('application.name'), '| state=%s' % i.get('state'), '| mute/vol:', [(x.get('mute'), x.get('volume'), x.get('channelVolumes')) for x in props][:1], '| node.dont-reconnect/target:', p.get('target.object'))
"
echo "== wallpaper actors vs monitors"
ev "global.get_window_actors().filter(a => a.meta_window.get_title() === 'wallpaperengine').map(a => 'actor '+a.x+','+a.y+' '+a.width+'x'+a.height+' monitor='+a.meta_window.get_monitor()+' parent='+a.get_parent().constructor.name).join(' | ')"
echo "== app.log"; cat "$WPE_STATE/app.log" 2>/dev/null | cut -c1-300
echo "== layer order (bottom to top)"
ev "Main.layoutManager._backgroundGroup.get_children().map(c => c.constructor.name+'('+c.x+','+c.y+' '+c.width+'x'+c.height+')').join(' < ')"
echo "== minimize the wallpaper (must be restored)"
ev "(() => { const w = global.get_window_actors().map(a => a.meta_window).find(w => w.get_title() === 'wallpaperengine'); w.minimize(); return 'minimize()'; })()"; sleep 2
ev "(() => { const a = global.get_window_actors().find(a => a.meta_window.get_title() === 'wallpaperengine'); return 'minimized='+a.meta_window.minimized+' visible='+a.visible; })()"
echo "== overview"; ev "Main.overview.show(); 'ok'"; sleep 3; shot "$WPE_STATE/shot-overview.png"
