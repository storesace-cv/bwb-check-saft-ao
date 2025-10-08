"""Utilities for parsing AGT validation error logs.

This module will eventually expose helpers capable of reading the
spreadsheets produced pela AGT (em formato ``.xlsx``) e converter cada
linha em estruturas de dados ricas consumidas pelo validador.  Enquanto a
migração dos scripts legados não estiver concluída mantemos as funções
como *stubs* para que a API pública esteja preparada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class AgtLogEntry:
    """Representa uma linha do relatório de erros devolvido pela AGT."""

    code: str
    message: str
    source: str | None = None


def parse_error_workbook(path: Path) -> Iterable[AgtLogEntry]:
    """Ler o ficheiro Excel emitido pela AGT e produzir entradas estruturadas.

    Parameters
    ----------
    path:
        Caminho para o ficheiro ``.xlsx`` extraído do portal da AGT.

    Returns
    -------
    Iterable[AgtLogEntry]
        Sequência de entradas correspondentes a cada linha do relatório.

    Notes
    -----
    A implementação será preenchida assim que a migração dos scripts
    ``validator_saft_ao.py`` para o pacote `saftao` estiver concluída.
    Até lá, a função actua como *stub* para permitir que o restante código
    possa importar esta API sem falhas.
    """

    raise NotImplementedError("Workbook parsing ainda não foi implementado")


__all__ = ["AgtLogEntry", "parse_error_workbook"]
