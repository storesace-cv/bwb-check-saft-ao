from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from saftao.commands import autofix_soft


class _DummyLogger:
    instance: "_DummyLogger | None" = None

    def __init__(self, base_name: str, output_dir: Path | None = None) -> None:  # pragma: no cover - trivial
        self.base_name = base_name
        self.output_dir = output_dir
        self.records: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        _DummyLogger.instance = self

    def log(self, *args, **kwargs) -> None:  # pragma: no cover - trivial
        self.records.append((args, kwargs))

    def flush(self) -> None:  # pragma: no cover - trivial
        pass


def test_main_uses_cli_xsd_override(tmp_path, monkeypatch):
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01">
  <Header />
  <MasterFiles />
  <SourceDocuments />
</AuditFile>
"""
    )

    xsd_path = tmp_path / "custom.xsd"
    xsd_path.write_text(
        """<?xml version='1.0' encoding='UTF-8'?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" />
"""
    )

    monkeypatch.setattr(autofix_soft, "ExcelLogger", _DummyLogger)
    monkeypatch.setattr(
        autofix_soft, "repair_workdocument_balance_in_file", lambda _path: False
    )
    monkeypatch.setattr(
        autofix_soft, "fix_xml", lambda tree, _path, _logger: tree
    )

    captured: dict[str, Path] = {}

    def _fake_validate(tree, path):  # pragma: no cover - executed in test
        captured["path"] = path
        return True, []

    monkeypatch.setattr(autofix_soft, "validate_xsd", _fake_validate)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(SystemExit) as exc:
        autofix_soft.main(
            [
                str(xml_path),
                "--xsd",
                str(xsd_path),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert exc.value.code == 0
    assert captured["path"] == xsd_path.resolve()

    logger = _DummyLogger.instance
    assert logger is not None
    assert any(
        record_args[:2] == ("XSD_FOUND", "XSD encontrado")
        and record_kwargs.get("new_value") == str(xsd_path.resolve())
        for record_args, record_kwargs in logger.records
    )
