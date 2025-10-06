"""Command line entry points for SAFT AO utilities."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Return the base argument parser shared across commands."""

    parser = argparse.ArgumentParser(description="SAFT AO tooling")
    parser.add_argument("input", type=Path, help="Path to the SAFT AO file")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the command line interface.

    This function exists as a placeholder for a future unified CLI that will
    coordinate validation and auto-fix subcommands.
    """

    raise NotImplementedError("CLI entry point not yet implemented")
