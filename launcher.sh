#!/usr/bin/env bash
# Wrapper leve para arrancar a interface gráfica Tkinter.
# Mantido para compatibilidade com fluxos anteriores que invocavam
# ``launcher.sh`` quando a aplicação ainda dependia de Qt/PySide.
# Agora apenas reencaminha para ``launcher.py`` sem qualquer configuração Qt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=${PYTHON:-python3}

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/launcher.py" "$@"
