#!/usr/bin/env python3
"""Unified launcher for the SAF-T (AO) command line tooling."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Callable

Command = Callable[[], int | None]

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))


COMMANDS: dict[str, tuple[str, str, str]] = {
    "gui": ("saftao.gui", "main", "Interface gráfica unificada"),
    "validate": ("scripts.validator_saft_ao", "main", "Validação estrita do SAF-T"),
    "autofix-soft": (
        "scripts.saft_ao_autofix_soft",
        "main",
        "Correções automáticas conservadoras",
    ),
    "autofix-hard": (
        "scripts.saft_ao_autofix_hard",
        "main",
        "Correções automáticas agressivas",
    ),
}


def _load_command(name: str) -> Command:
    module_name, func_name, _ = COMMANDS[name]
    module = importlib.import_module(module_name)
    command = getattr(module, func_name)
    return command  # type: ignore[return-value]


def _run_command(name: str, args: list[str]) -> int:
    command = _load_command(name)
    old_argv = sys.argv[:]
    sys.argv = [f"{name}.py", *args]
    try:
        result = command()
    except SystemExit as exc:  # pragma: no cover - delegate exit handling
        code = exc.code if isinstance(exc.code, int) else 0
        return code
    finally:
        sys.argv = old_argv
    if isinstance(result, int):
        return result
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ponto único de entrada para as ferramentas SAF-T (AO)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_commands",
        help="Apresenta a lista de comandos disponíveis e termina",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=COMMANDS.keys(),
        help="Ferramenta a executar (omitir para abrir a interface gráfica)",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionais passados ao comando seleccionado",
    )

    ns = parser.parse_args(argv)

    if ns.list_commands:
        for key, (_, _, description) in COMMANDS.items():
            print(f"{key:14s} - {description}")
        return 0

    if ns.command is None:
        if ns.args:
            parser.error("é necessário indicar um comando antes dos argumentos")
        command = "gui"
    else:
        command = ns.command

    return _run_command(command, ns.args)


if __name__ == "__main__":
    sys.exit(main())
