#!/usr/bin/env python3
"""Wrapper para manter compatibilidade com o script legado."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Garante que a pasta ``src`` está no ``sys.path``."""

    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    src_path = project_root / "src"

    if src_path.exists():
        sys.path.insert(0, str(src_path))


_ensure_src_on_path()

from saftao.commands.autofix_soft import main


if __name__ == "__main__":  # pragma: no cover - compatibilidade
    raise SystemExit(main())
