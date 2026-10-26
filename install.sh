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
family() {
    local id="" like=""
    if [ -r /etc/os-release ]; then . /etc/os-release; id="${ID:-}"; like="${ID_LIKE:-}"; fi
    case " $id $like " in
        *" ubuntu "*|*" debian "*|*" linuxmint "*|*" pop "*) echo debian ;;
        *" fedora "*|*" rhel "*|*" centos "*) echo fedora ;;
        *" arch "*|*" manjaro "*|*" endeavouros "*|*" cachyos "*) echo arch ;;
        *) echo unknown ;;
    esac
}

packages() {
    case "$1" in
        debian)
            local mpv=libmpv2
            apt-cache show libmpv2 > /dev/null 2>&1 || mpv=libmpv1
            echo build-essential cmake git pkg-config libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libgl-dev \
                libglew-dev freeglut3-dev libsdl2-dev liblz4-dev libavcodec-dev libavformat-dev libavutil-dev \
                libswscale-dev libxxf86vm-dev libglm-dev libglfw3-dev libmpv-dev mpv "$mpv" libpulse-dev libpulse0 \
                libfftw3-dev libfreetype-dev libwayland-dev wayland-protocols libxkbcommon-dev \
                python3 python3-venv python3-pip ffmpeg x11-utils ;;
        fedora)
            echo gcc gcc-c++ cmake git libXrandr-devel libXinerama-devel libXcursor-devel libXi-devel mesa-libGL-devel \
                glew-devel freeglut-devel SDL2-devel lz4-devel ffmpeg ffmpeg-free-devel libXxf86vm-devel glm-devel \
                glfw-devel mpv mpv-devel pulseaudio-libs-devel fftw-devel gmp-devel freetype-devel wayland-devel \
                wayland-protocols-devel libxkbcommon-devel python3 python3-pip xorg-x11-utils ;;
        arch)
            echo base-devel cmake git libxrandr libxinerama libxcursor libxi mesa glew freeglut sdl2 lz4 ffmpeg \
                libxxf86vm glm glfw mpv libpulse fftw freetype2 wayland wayland-protocols libxkbcommon python \
                python-pip xorg-xprop xorg-xwininfo ;;
    esac
}

install_packages() {
    local fam=$1; local -a pkgs; read -r -a pkgs <<< "$(packages "$fam")"
    say "Pacotes do sistema (${#pkgs[@]}) para $fam"
    case "$fam" in
        debian) run sudo apt-get update; run sudo apt-get install -y "${pkgs[@]}" ;;
        fedora) run sudo dnf install -y "${pkgs[@]}" ;;
        arch)   run sudo pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    esac
}

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
    run mkdir -p "$BIN_DIR"
    run ln -sf "$ENGINE_DIR/build/output/linux-wallpaperengine" "$BIN_DIR/linux-wallpaperengine"
    case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR não está no seu PATH; adicione-o ao ~/.profile." ;; esac
}

# --- app ------------------------------------------------------------------------------------------------------
install_app() {
    say "Aplicativo (ambiente Python, ícone e menu)"
    run "$HERE/wpe-gui.sh" --install-desktop
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
Falta só o Wallpaper Engine do Steam instalado (é dele que vêm o wallpapers e os assets):
veja "Wallpaper Engine no Steam" em docs/INSTALL.md.
Abra o app pelo menu de aplicativos ("Wallpaper Engine") ou com ./wpe-gui.sh
EOF
