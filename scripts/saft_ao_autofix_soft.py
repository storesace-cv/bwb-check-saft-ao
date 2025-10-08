#!/usr/bin/env python3
"""Wrapper para manter compatibilidade com o script legado."""

from saftao.commands.autofix_soft import main

if __name__ == "__main__":  # pragma: no cover - compatibilidade
    raise SystemExit(main())
