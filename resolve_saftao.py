#!/usr/bin/env python3
"""Ponto de entrada para a aplicação gráfica Resolve SAF-T AO."""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def main() -> None:
    _ensure_src_on_path()
    from saftao.resolve_saftao import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
