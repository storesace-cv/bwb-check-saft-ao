"""Generate Excel reports with totals extracted from SAF-T (AO) files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from ..schema import load_audit_file
from ..utils.reporting import aggregate_documents, write_excel_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Gera um relatório em Excel com totais por tipo de documento e "
            "listagem de documentos não contabilísticos."
        )
    )
    parser.add_argument("saft", type=Path, help="Caminho para o ficheiro SAF-T (AO)")
    parser.add_argument(
        "output",
        type=Path,
        help="Destino do relatório Excel (.xlsx) a gerar",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    tree, root, namespace = load_audit_file(args.saft)
    data = aggregate_documents(root, namespace)
    write_excel_report(data, args.output)

    return 0


if __name__ == "__main__":  # pragma: no cover - execução directa
    raise SystemExit(main())
