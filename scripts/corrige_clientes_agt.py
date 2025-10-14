"""Interface de linha de comando para corrigir listagens de clientes com base na AGT."""
from __future__ import annotations

import argparse
from pathlib import Path

from tools.corrige_clientes_agt import LAST_SUMMARY, corrigir_excel, set_fetch_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Corrige ficheiros Excel de clientes com dados da AGT")
    parser.add_argument(
        "--input",
        dest="input",
        default="docs/listagem_de_clientes_exemplo.xlsx",
        help="Caminho para o ficheiro de clientes",
    )
    parser.add_argument(
        "--rate",
        dest="rate",
        type=float,
        default=5.0,
        help="Limite de pedidos por segundo",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=10.0,
        help="Timeout por pedido (segundos)",
    )
    parser.add_argument(
        "--no-cache",
        dest="no_cache",
        action="store_true",
        help="Desativa o cache em memória dos NIFs",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Caminho final do ficheiro corrigido ou pasta de destino",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Ficheiro de entrada não encontrado: {input_path}")

    set_fetch_settings(rate_limit=args.rate, timeout=args.timeout, use_cache=not args.no_cache)

    output_path: Path | None = None
    if args.output:
        output_candidate = Path(args.output).expanduser()
        if output_candidate.exists() and output_candidate.is_dir():
            output_candidate = output_candidate / (
                f"{input_path.stem}_corrigido{input_path.suffix or '.xlsx'}"
            )
        elif output_candidate.suffix == "":
            # Interpretar caminhos sem sufixo como directório pretendido
            output_candidate = output_candidate / (
                f"{input_path.stem}_corrigido{input_path.suffix or '.xlsx'}"
            )
        output_candidate.parent.mkdir(parents=True, exist_ok=True)
        output_path = output_candidate

    final_path = corrigir_excel(
        str(input_path), str(output_path) if output_path is not None else None
    )
    summary = LAST_SUMMARY or {}

    print(f"Linhas processadas: {summary.get('linhas', 0)}")
    print(f"NIFs válidos: {summary.get('validos', 0)}")
    print(f"NIFs inválidos: {summary.get('invalidos', 0)}")
    print(
        "NIFs duplicados: "
        f"{summary.get('nifs_duplicados', 0)} "
        f"(marcados: {summary.get('duplicados_marcados', 0)})"
    )
    print(f"Ficheiro gravado em: {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
