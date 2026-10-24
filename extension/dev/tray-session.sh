# Runs inside the throwaway session (see test-shell.sh): the whole app (python -m wpe_gui) with an isolated
# HOME, runtime dir and temp dir, so it can never touch a real running instance (lock file, local socket, settings).
# Only the processes started here are ever signalled.
ev() { gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval "$1" 2>&1 | cut -c1-400; }
DISP=$(ev "GLib.getenv('DISPLAY')" | grep -oE ":[0-9]+" | head -1)
XA=$(ev "GLib.getenv('XAUTHORITY')" | grep -oE "/[^\"']+" | head -1)
H="$WPE_STATE/home"; RUN="$WPE_STATE/run"; TMP="$WPE_STATE/tmp"
mkdir -p "$H/.config/wpe-gui" "$RUN" "$TMP"; chmod 700 "$RUN"
printf '{"restoreOnStart": false, "windowed": true, "staticBackground": false}' > "$H/.config/wpe-gui/settings.json"
PIDS="$WPE_STATE/app.pids"; : > "$PIDS"

launch() {
  # exec inside the subshell: the recorded PID is the Python process itself, not a wrapper
  ( cd "$WPE_REPO" && HOME="$H" XDG_RUNTIME_DIR="$RUN" TMPDIR="$TMP" XAUTHORITY=$XA DISPLAY=$DISP QT_QPA_PLATFORM=wayland \
      WAYLAND_DISPLAY="/run/user/$(id -u)/$WPE_DISPLAY" bash -c 'echo $$ >> "$0"; exec "$@"' "$PIDS" "$WPE_PYTHON" -m wpe_gui "$@" >> "$WPE_STATE/app.log" 2>&1 & )
}
alive_count() { local n=0; for p in $(cat "$PIDS"); do kill -0 "$p" 2>/dev/null && n=$((n+1)); done; echo $n; }
alive() { [ "$(alive_count)" -gt 0 ] && echo "app vivo (processos: $(alive_count))" || echo "app NAO esta rodando"; }
stop_all() { for p in $(cat "$PIDS"); do kill -TERM "$p" 2>/dev/null; done; }
tray_items() { ev "Object.keys(Main.panel.statusArea).filter(k => /appindicator|indicator|wpe|Wallpaper/i.test(k)).join(',')"; }
app_windows() { ev "global.get_window_actors().map(a => a.meta_window).filter(w => /Wallpaper Engine/.test(w.get_title()||'')).map(w => w.get_title()+' minimized='+w.minimized).join(' | ')"; }
close_window() { ev "(() => { const w = global.get_window_actors().map(a => a.meta_window).find(w => /Wallpaper Engine/.test(w.get_title()||'')); if (w) w.delete(global.get_current_time()); return w ? 'ok' : 'sem janela'; })()" > /dev/null; }

[ -n "${WPE_TRAY_ONLY:-}" ] || { echo "== 1. abre o app";                    launch;  sleep 9; alive; echo -n "janela: "; app_windows; echo -n "itens do tray: "; tray_items
echo "== 2. fecha a janela (X)";            close_window; sleep 3; alive; echo -n "janela: "; app_windows; echo "(vazio = escondida)"
echo "== 3. abre de novo (2o lancamento)";  launch;  sleep 4; alive; echo -n "janela: "; app_windows
echo "== 4. fecha e encerra com SIGTERM";   close_window; sleep 2; stop_all; sleep 3; alive
}
[ "${WPE_TRAY_ONLY:-}" = 6 ] || { echo "== 5. inicia com --minimized";        : > "$PIDS"; launch --minimized; sleep 9; alive; echo -n "janela: "; app_windows; echo "(vazio = so na bandeja)"; echo -n "itens do tray: "; tray_items
stop_all; sleep 2
}

if [ "${WPE_TRAY_ONLY:-}" = 6 ]; then
  echo "== 6. opcao 'Iniciar escondido' ligada (sem --minimized)"
  printf '{"restoreOnStart": false, "windowed": true, "staticBackground": false, "startHidden": true}' > "$H/.config/wpe-gui/settings.json"
  : > "$PIDS"; launch
  seen=0; for i in $(seq 1 45); do [ -n "$(app_windows | grep -o 'Wallpaper Engine')" ] && seen=$((seen+1)); sleep 0.2; done
  alive; echo "vezes em que a janela apareceu durante a inicializacao: $seen (0 = nunca piscou)"; echo -n "itens do tray: "; tray_items
  echo "-- agora abre pelo segundo lancamento:"; launch; sleep 4; echo -n "janela: "; app_windows
  stop_all; sleep 2
fi
