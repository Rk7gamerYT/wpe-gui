#!/usr/bin/env bash
# Instalador do wpe-gui: dependências, motor (linux-wallpaperengine) com os patches do projeto, ícone/menu e,
# as integrações do GNOME ou KDE Plasma para a sessão atual.
#
#   ./install.sh               instala tudo (pede a senha do sudo só para instalar pacotes)
#   ./install.sh --dry-run     só mostra o que faria, sem alterar nada
#   ./install.sh --help
#
# Testado: Ubuntu 26.04 (GNOME 50 e KDE Plasma 6, Wayland). As listas de Fedora e Arch vêm do README do motor e não foram
# testadas pelo autor, veja docs/INSTALL.md.
set -euo pipefail

ENGINE_REPO="https://github.com/Almamu/linux-wallpaperengine.git"
# Versão do motor em que os patches foram feitos e testados
ENGINE_REF="b016d7d1fdcf4e5fd2f9c9fa420a8aaa07fee02d"

DRY=0; ASSUME_YES=0; DO_DEPS=1; DO_ENGINE=1; DO_GNOME=1; DO_KDE=1
HERE=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
ENGINE_DIR="${WPE_ENGINE_DIR:-$HOME/.local/share/wpe-gui/linux-wallpaperengine}"
BIN_DIR="$HOME/.local/bin"

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; cat <<'EOF'

Opções:
  --dry-run     mostra os comandos sem executar
  --yes         não pergunta nada
  --no-deps     não instala pacotes do sistema (você já tem as dependências)
  --no-engine   não compila o motor (você já tem o linux-wallpaperengine com os patches)
  --no-gnome    não instala a extensão do GNOME
  --no-kde      não instala o plugin Plasma e a extensão KWin
Variáveis: WPE_ENGINE_DIR (onde clonar/compilar o motor)
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --no-deps) DO_DEPS=0 ;;
        --no-engine) DO_ENGINE=0 ;;
        --no-gnome) DO_GNOME=0 ;;
        --no-kde) DO_KDE=0 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Opção desconhecida: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33maviso:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31merro:\033[0m %s\n' "$*" >&2; exit 1; }
run()  { if [ "$DRY" = 1 ]; then printf '  + %s\n' "$*"; else "$@"; fi; }

# --- distro ---------------------------------------------------------------------------------------------------
source "$HERE/scripts/distro-packages.sh"

# --- motor ----------------------------------------------------------------------------------------------------
# Compiling C++ in parallel needs roughly 2 GB per job: more jobs than the memory allows can freeze the machine
build_jobs() {
    local cpus mem_gb jobs
    cpus=$(nproc 2>/dev/null || echo 2)
    mem_gb=$(awk '/MemAvailable/ {print int($2 / 1048576)}' /proc/meminfo 2>/dev/null || echo 4)
    jobs=$(( mem_gb / 2 )); [ "$jobs" -lt 1 ] && jobs=1; [ "$jobs" -gt "$cpus" ] && jobs=$cpus
    echo "$jobs"
}

build_engine() {
    say "Motor linux-wallpaperengine em $ENGINE_DIR"
    if [ ! -d "$ENGINE_DIR/.git" ]; then
        run mkdir -p "$(dirname "$ENGINE_DIR")"
        run git clone --recurse-submodules "$ENGINE_REPO" "$ENGINE_DIR"
    fi
    run git -C "$ENGINE_DIR" fetch --quiet origin
    run git -C "$ENGINE_DIR" checkout -q "$ENGINE_REF"
    run git -C "$ENGINE_DIR" submodule update --init --recursive

    local patch
    for patch in "$HERE"/patches/*.patch; do
        [ -f "$patch" ] || continue
        if [ "$DRY" = 1 ]; then
            printf '  + aplicar %s\n' "$(basename "$patch")"
        elif git -C "$ENGINE_DIR" apply --check "$patch" 2> /dev/null; then
            git -C "$ENGINE_DIR" apply "$patch" && echo "  patch aplicado: $(basename "$patch")"
        elif git -C "$ENGINE_DIR" apply --check --reverse "$patch" 2> /dev/null; then
            echo "  patch já aplicado: $(basename "$patch")"
        else
            die "o patch $(basename "$patch") não aplica em $ENGINE_REF; veja docs/INSTALL.md"
        fi
    done

    local jobs; jobs=$(build_jobs)
    echo "  compilando com $jobs job(s) (limitado pela memória livre: ~2 GB por job)"
    run mkdir -p "$ENGINE_DIR/build"
    if [ "$DRY" = 1 ]; then
        printf '  + (cd %s/build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j%s)\n' "$ENGINE_DIR" "$jobs"
    else
        (cd "$ENGINE_DIR/build" && cmake -DCMAKE_BUILD_TYPE=Release .. && nice -n 10 make -j"$jobs")
    fi
    if [ "$DRY" = 0 ] && [ ! -x "$ENGINE_DIR/build/output/linux-wallpaperengine" ]; then
        die "a compilação terminou sem gerar o motor; verifique os erros acima."
    fi
    run mkdir -p "$BIN_DIR"
    run ln -sf "$ENGINE_DIR/build/output/linux-wallpaperengine" "$BIN_DIR/linux-wallpaperengine"
    # The app also discovers this location when the desktop session omits it from PATH.
}

# --- app ------------------------------------------------------------------------------------------------------
install_app() {
    say "Aplicativo (ambiente Python, ícone e menu)"
    run "$HERE/wpe-gui.sh" --install-desktop
    run mkdir -p "$BIN_DIR"
    run ln -sf "$HERE/wpe-gui.sh" "$BIN_DIR/wpe-gui"
    say "Verificando o motor e configurando o aplicativo"
    if [ "$DO_ENGINE" = 1 ]; then
        run env PYTHONPATH="$HERE" "$HERE/.venv/bin/python" -m wpe_gui.install_config "$ENGINE_DIR/build/output/linux-wallpaperengine"
    else
        run env PYTHONPATH="$HERE" "$HERE/.venv/bin/python" -m wpe_gui.install_config
    fi
}

desktop_has() {
    local desktop="${XDG_CURRENT_DESKTOP:-}"
    case ":${desktop^^}:" in *":$1:"*) return 0 ;; *) return 1 ;; esac
}

install_kde() {
    say "KDE Plasma 6 (plugin de wallpaper e extensão KWin)"
    run "$HERE/kde/install.sh"
    warn "Se estiver atualizando o plugin, reinicie o Plasma após sair do app: systemctl --user restart plasma-plasmashell.service"
}

install_gnome() {
    command -v gnome-shell > /dev/null 2>&1 || { echo "  GNOME Shell não encontrado: pulando a extensão."; return; }
    say "Extensão do GNOME (wallpaper atrás das janelas)"
    run "$HERE/extension/install.sh"
    warn "Saia da sessão e entre de novo para o GNOME carregar a extensão."
    gnome-extensions list 2> /dev/null | grep -qi appindicator \
        || warn "Para o ícone da bandeja, instale e ative a extensão AppIndicator (veja docs/INSTALL.md)."
}

# --- main -----------------------------------------------------------------------------------------------------
FAM=$(family)
MODE_LABEL=""
[ "$DRY" = 1 ] && MODE_LABEL=", simulação"
say "wpe-gui: instalação  (distro: $FAM$MODE_LABEL)"
[ "$DRY" = 1 ] && echo "Modo --dry-run: nada será alterado."

if [ "$DO_DEPS" = 1 ] && [ "$FAM" = unknown ]; then
    die "Distro não reconhecida. Instale as dependências à mão (docs/INSTALL.md) e rode com --no-deps."
fi
if [ "$DRY" = 0 ] && [ "$EUID" = 0 ]; then
    die "execute como seu usuário normal, sem sudo; o instalador solicita a senha quando necessário."
fi
if [ "$DRY" = 0 ]; then
    LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/wpe-gui"
    mkdir -p "$LOG_DIR"
    exec > >(tee -a "$LOG_DIR/install.log") 2>&1
    trap 'echo "Instalação interrompida. Consulte o erro acima e o log em $LOG_DIR/install.log." >&2' ERR
fi
if [ "$DRY" = 0 ] && [ "$ASSUME_YES" = 0 ]; then
    read -r -p "Vou instalar pacotes com sudo e compilar o motor (leva alguns minutos). Continuar? [s/N] " ans
    case "$ans" in s|S|sim|y|Y) ;; *) echo "Cancelado."; exit 1 ;; esac
fi

[ "$DO_DEPS" = 1 ] && install_packages "$FAM"
[ "$DO_ENGINE" = 1 ] && build_engine
install_app
if desktop_has KDE; then
    [ "$DO_KDE" = 0 ] || install_kde
elif desktop_has GNOME; then
    [ "$DO_GNOME" = 0 ] || install_gnome
else
    echo "  Sessão sem GNOME/KDE detectado. Consulte docs/INSTALL.md para instalar a integração manualmente."
fi

say "Pronto"
cat <<'EOF'
Aplicativo e motor instalados e configurados.
Você precisa ter o Wallpaper Engine do Steam instalado (é dele que vêm os wallpapers e os assets):
veja "Wallpaper Engine no Steam" em docs/INSTALL.md.
Abra o app pelo menu de aplicativos ("Wallpaper Engine") ou com ./wpe-gui.sh
EOF
