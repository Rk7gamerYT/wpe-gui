#!/usr/bin/env bash
# Instalação completa a partir de um único comando, sem git clone manual.
set -euo pipefail

APP_DIR="${WPE_APP_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/wpe-gui/app}"
ARCHIVE_URL="${WPE_ARCHIVE_URL:-https://github.com/Rk7gamerYT/wpe-gui/archive/refs/heads/main.tar.gz}"
for option in "$@"; do
    if [[ "$option" == --dry-run ]]; then
        printf 'Baixar projeto: %s\nInstalar aplicativo em: %s\n' "$ARCHIVE_URL" "$APP_DIR"
        echo 'Instalar dependências, compilar motor com patches, configurar caminhos e integrar KDE/GNOME.'
        exit 0
    fi
done
if [[ $EUID == 0 ]]; then
    echo 'Execute como seu usuário normal, sem sudo. A senha será solicitada para os pacotes.' >&2
    exit 1
fi
for program in curl tar; do
    command -v "$program" >/dev/null || { echo "Instale $program antes de continuar." >&2; exit 1; }
done
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/.wpe-managed-install" ]]; then
    echo "A pasta $APP_DIR já existe e não pertence a este instalador. Escolha outra com WPE_APP_DIR." >&2
    exit 1
fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
trap 'echo "A instalação não terminou. Corrija o erro acima e execute o mesmo comando novamente." >&2' ERR
printf '\nBaixando Wallpaper Engine GUI...\n'
curl --fail --location --retry 3 --output "$work/app.tar.gz" "$ARCHIVE_URL"
mkdir "$work/source"
tar -xzf "$work/app.tar.gz" --strip-components=1 -C "$work/source"
[[ -f "$work/source/install.sh" && -f "$work/source/wpe-gui.sh" ]] || {
    echo 'Download inválido: instalador não encontrado.' >&2; exit 1;
}
mkdir -p "$APP_DIR"
cp -a "$work/source/." "$APP_DIR/"
touch "$APP_DIR/.wpe-managed-install"
cd "$APP_DIR"
bash ./install.sh --yes "$@"
printf '\nInstalação concluída. Abra “Wallpaper Engine” no menu de aplicativos.\n'
printf 'Para atualizar, execute novamente este mesmo comando.\n'
