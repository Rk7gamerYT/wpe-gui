#!/usr/bin/env bash
# Starts wpe-gui. Creates the virtualenv and installs the dependencies on the first run.
set -euo pipefail

# Resolve the real folder even when this script is launched through a symlink (e.g. ~/.local/bin/wpe-gui)
SELF=$(readlink -f "${BASH_SOURCE[0]}")
DIR=$(dirname "$SELF")
cd "$DIR"

if [ ! -x .venv/bin/python ]; then
    echo "Primeira execução: criando o ambiente Python (.venv)..."
    python3 -m venv .venv
    .venv/bin/pip install --quiet PySide6-Essentials
fi

# The Qt Wayland text-input warnings are harmless noise
export QT_LOGGING_RULES="${QT_LOGGING_RULES:-qt.qpa.wayland.textinput=false;qt.qpa.services=false}"
exec .venv/bin/python -m wpe_gui "$@"
