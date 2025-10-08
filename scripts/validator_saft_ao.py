#!/usr/bin/env python3
"""Wrapper para manter compatibilidade com o script legado.

Delegamos toda a lógica para :mod:`saftao.commands.validator_strict` para que
as distribuições antigas continuem a funcionar enquanto o pacote ``saftao`` é
utilizado como fonte de verdade.
"""

from __future__ import annotations

import sys
from pathlib import Path

# NOTE: Quando o pacote é utilizado diretamente a partir do repositório ainda
# não instalado (``pip install .``), o Python não encontra automaticamente o
# diretório ``src``. Para manter a compatibilidade com o comportamento legado do
# script, adicionamos o caminho do ``src`` ao ``sys.path`` antes de importar o
# comando principal.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from saftao.commands.validator_strict import main

if __name__ == "__main__":  # pragma: no cover - compatibilidade
    raise SystemExit(main())
