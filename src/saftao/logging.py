"""Funções utilitárias para registo estruturado em Excel.

O objectivo deste módulo é unificar as múltiplas implementações de
``ExcelLogger`` existentes nos scripts *legacy*. Enquanto a migração para o
pacote ``saftao`` não fica concluída, disponibilizamos uma implementação leve
que garante compatibilidade com a interface esperada pelas novas ferramentas
como a GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, Sequence


class RowLike(Protocol):
    """Protocolo para linhas serializáveis em formato tabular."""

    def as_cells(self) -> Iterable[str]:
        """Devolve os valores ordenados a escrever na folha."""


@dataclass(slots=True)
class ExcelLoggerConfig:
    """Configuração usada pelo :class:`ExcelLogger`."""

    columns: Sequence[str]
    filename: str = "saft-ao-report.xlsx"


class ExcelLogger:
    """Grava registos em Excel utilizando :mod:`openpyxl`.

    A implementação é propositadamente simples: cada chamada a
    :meth:`write_rows` cria um novo *workbook* com o cabeçalho fornecido em
    :class:`ExcelLoggerConfig` e grava as linhas recebidas. Esta abordagem é
    suficiente para suportar os *stubs* do pacote até que a refatoração total
    esteja concluída.
    """

    def __init__(self, config: ExcelLoggerConfig) -> None:
        self.config = config

    def write_rows(self, rows: Iterable[RowLike | Iterable[str]]) -> Path:
        """Persistir ``rows`` num ficheiro Excel e devolver o caminho final."""

        from openpyxl import Workbook

        destination = Path(self.config.filename)
        destination.parent.mkdir(parents=True, exist_ok=True)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Log"

        if self.config.columns:
            worksheet.append(list(self.config.columns))

        for row in rows:
            if hasattr(row, "as_cells"):
                cells = list(row.as_cells())  # type: ignore[arg-type]
            else:
                cells = list(row)  # type: ignore[arg-type]
            worksheet.append(cells)

        workbook.save(destination)
        return destination


__all__ = ["RowLike", "ExcelLoggerConfig", "ExcelLogger"]

