#!/usr/bin/env bash
# Shared package lists for the installer and container CI. Sourcing does not install anything.
family() {
    local release_file="${1:-/etc/os-release}"
    local id="" like=""
    if [ -r "$release_file" ]; then . "$release_file"; id="${ID:-}"; like="${ID_LIKE:-}"; fi
    case " $id $like " in
        *" ubuntu "*|*" debian "*|*" linuxmint "*|*" pop "*) echo debian ;;
        *" fedora "*|*" rhel "*|*" centos "*) echo fedora ;;
        *" opensuse "*|*" opensuse-tumbleweed "*|*" opensuse-leap "*|*" suse "*|*" sles "*) echo opensuse ;;
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
                libswresample-dev libgmp-dev libdbus-1-dev libgtk-3-dev zlib1g-dev libegl-dev \
                curl ca-certificates python3 python3-venv python3-pip ffmpeg x11-utils ;;
        fedora)
            echo gcc gcc-c++ make cmake git pkgconf-pkg-config curl ca-certificates dbus-devel gtk3-devel zlib-devel libglvnd-devel libXrandr-devel libXinerama-devel libXcursor-devel libXi-devel mesa-libGL-devel \
                glew-devel freeglut-devel SDL2-devel lz4-devel ffmpeg-free ffmpeg-free-devel libXxf86vm-devel glm-devel \
                glfw-devel mpv mpv-devel pulseaudio-libs-devel fftw-devel gmp-devel freetype-devel wayland-devel \
                wayland-protocols-devel libxkbcommon-devel python3 python3-pip xorg-x11-utils ;;
        arch)
            echo base-devel cmake git pkgconf curl ca-certificates dbus gtk3 zlib libxrandr libxinerama libxcursor libxi mesa glew freeglut sdl2-compat lz4 ffmpeg \
                libxxf86vm glm glfw mpv libpulse fftw freetype2 wayland wayland-protocols libxkbcommon python \
                python-pip xorg-xprop xorg-xwininfo ;;
        opensuse)
            echo gcc gcc-c++ make cmake git curl ca-certificates pkgconf-pkg-config glm-devel \
                'pkgconfig(xrandr)' 'pkgconfig(xinerama)' 'pkgconfig(xcursor)' 'pkgconfig(xi)' \
                'pkgconfig(gl)' 'pkgconfig(egl)' 'pkgconfig(glew)' 'pkgconfig(glut)' \
                'pkgconfig(sdl2)' 'pkgconfig(liblz4)' 'pkgconfig(libavcodec)' 'pkgconfig(libavformat)' \
                'pkgconfig(libavutil)' 'pkgconfig(libswscale)' 'pkgconfig(libswresample)' \
                'pkgconfig(xxf86vm)' 'pkgconfig(glfw3)' 'pkgconfig(mpv)' 'pkgconfig(libpulse)' \
                'pkgconfig(fftw3)' 'pkgconfig(freetype2)' 'pkgconfig(wayland-client)' \
                'pkgconfig(wayland-protocols)' 'pkgconfig(xkbcommon)' 'pkgconfig(dbus-1)' \
                'pkgconfig(gtk+-3.0)' 'pkgconfig(zlib)' gmp-devel python3 python3-pip ffmpeg xprop xwininfo ;;
        *) return 2 ;;
    esac
}

install_packages() {
    local fam=$1; local -a privilege=() pkgs;
    [ "$EUID" = 0 ] || privilege=(sudo); read -r -a pkgs <<< "$(packages "$fam")"
    say "Pacotes do sistema (${#pkgs[@]}) para $fam"
    case "$fam" in
        debian) run "${privilege[@]}" apt-get update; run "${privilege[@]}" apt-get install -y "${pkgs[@]}" ;;
        fedora) run "${privilege[@]}" dnf install -y "${pkgs[@]}" ;;
        opensuse) run "${privilege[@]}" zypper --non-interactive refresh; run "${privilege[@]}" zypper --non-interactive install --no-recommends "${pkgs[@]}" ;;
        arch)   run "${privilege[@]}" pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    esac
}

