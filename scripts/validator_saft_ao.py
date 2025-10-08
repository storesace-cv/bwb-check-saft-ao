#!/usr/bin/env python3
"""Wrapper para manter compatibilidade com o script legado.

Delegamos toda a lógica para :mod:`saftao.commands.validator_strict` para que
as distribuições antigas continuem a funcionar enquanto o pacote ``saftao`` é
utilizado como fonte de verdade.
"""

from saftao.commands.validator_strict import main

if __name__ == "__main__":  # pragma: no cover - compatibilidade
    raise SystemExit(main())
