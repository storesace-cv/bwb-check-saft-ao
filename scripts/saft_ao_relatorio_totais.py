#!/usr/bin/env python3
"""Wrapper para o comando de relatório de totais."""

from __future__ import annotations

import sys
from pathlib import Path

# Garantir acesso ao pacote instalado na pasta ``src`` quando executado
# directamente a partir do repositório sem instalação prévia.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if _SRC_PATH.exists() and str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from saftao.commands.report import main

if __name__ == "__main__":  # pragma: no cover - compatibilidade com execução directa
    raise SystemExit(main())
