"""Command line entry points for SAFT AO utilities."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from .commands import autofix_hard, autofix_soft, validator_strict

CommandCallable = Callable[[list[str] | None], int | None]


@dataclass(frozen=True)
class CommandSpec:
    """Metadata describing a CLI command exposed by :mod:`saftao.cli`."""

    name: str
    summary: str
    handler: CommandCallable
    legacy_script: str
    module: str

    def run(self, argv: list[str] | None) -> int:
        """Execute the command and normalise the resulting exit code."""

        try:
            result = self.handler(argv)
        except SystemExit as exc:  # legacy commands still rely on sys.exit
            code = exc.code
            if code is None:
                return 0
            if isinstance(code, int):
                return code
            print(str(code), file=sys.stderr)
            return 1
        if result is None:
            return 0
        return int(result)


_COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="validate",
        summary="Validação estrita SAF-T (AO) com geração de log Excel.",
        handler=validator_strict.main,
        legacy_script="scripts/validator_saft_ao.py",
        module="saftao.commands.validator_strict",
    ),
    CommandSpec(
        name="autofix-soft",
        summary="Auto-correcções não destrutivas para ficheiros SAF-T (AO).",
        handler=autofix_soft.main,
        legacy_script="scripts/saft_ao_autofix_soft.py",
        module="saftao.commands.autofix_soft",
    ),
    CommandSpec(
        name="autofix-hard",
        summary="Auto-correcções agressivas com validação XSD opcional.",
        handler=autofix_hard.main,
        legacy_script="scripts/saft_ao_autofix_hard.py",
        module="saftao.commands.autofix_hard",
    ),
)

_COMMAND_INDEX: Mapping[str, CommandSpec] = {spec.name: spec for spec in _COMMANDS}


def available_commands() -> Iterable[CommandSpec]:
    """Return the commands registered in the CLI."""

    return _COMMANDS


def build_parser() -> argparse.ArgumentParser:
    """Return the base argument parser shared across commands."""

    parser = argparse.ArgumentParser(description="Ferramentas SAF-T (AO)")
    subparsers = parser.add_subparsers(dest="command", metavar="comando")
    subparsers.required = True

    for spec in _COMMANDS:
        subparser = subparsers.add_parser(
            spec.name,
            help=spec.summary,
            description=spec.summary,
            add_help=False,
        )
        subparser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    return parser


def _normalise_args(namespace: argparse.Namespace) -> tuple[str, list[str]]:
    command = getattr(namespace, "command")
    remainder = getattr(namespace, "args", [])
    return command, list(remainder)


def run(command: str, argv: Sequence[str] | None = None) -> int:
    """Execute *command* forwarding ``argv`` to the underlying handler."""

    spec = _COMMAND_INDEX.get(command)
    if spec is None:
        raise ValueError(f"Comando desconhecido: {command}")
    forwarded = list(argv or [])
    if not forwarded:
        forwarded = None
    return spec.run(forwarded)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the command line interface."""

    parser = build_parser()
    namespace, extras = parser.parse_known_args(argv)
    command, remainder = _normalise_args(namespace)

    forwarded = remainder + extras
    if forwarded and forwarded[0] in {"-h", "--help"}:
        # Pedir ajuda específica do comando delegando para o handler.
        return run(command, ["--help"])  # type: ignore[arg-type]

    return run(command, forwarded)


if __name__ == "__main__":  # pragma: no cover - execução directa
    raise SystemExit(main())
