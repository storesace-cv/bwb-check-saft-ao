"""Tests ensuring the AGT log parser stub is available for future work."""

from __future__ import annotations

from pathlib import Path

import pytest

from saftao import agt_logs


def test_parse_error_workbook_stub(tmp_path: Path) -> None:
    dummy = tmp_path / "report.xlsx"
    dummy.write_bytes(b"PK\x03\x04")  # minimal ZIP header for XLSX placeholder

    with pytest.raises(NotImplementedError):
        list(agt_logs.parse_error_workbook(dummy))


def test_agt_log_entry_dataclass_repr() -> None:
    entry = agt_logs.AgtLogEntry(code="ERR", message="Mensagem", source="linha 1")

    repr_text = repr(entry)

    assert "ERR" in repr_text
    assert "Mensagem" in repr_text
