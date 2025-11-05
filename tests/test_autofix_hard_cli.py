from __future__ import annotations

from pathlib import Path

import pytest

from saftao.commands import autofix_hard


def test_main_uses_cli_xsd_override(tmp_path, monkeypatch, capsys):
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

    monkeypatch.setattr(
        autofix_hard, "repair_workdocument_balance_in_file", lambda _path: False
    )
    monkeypatch.setattr(autofix_hard, "fix_xml", lambda tree, _path: tree)

    captured: dict[str, Path] = {}

    def _fake_validate(tree, path):  # pragma: no cover - executed in test
        captured["path"] = path
        return True, []

    monkeypatch.setattr(autofix_hard, "validate_xsd", _fake_validate)

    default_called = False

    def _fake_default():  # pragma: no cover - executed in test
        nonlocal default_called
        default_called = True
        return None

    monkeypatch.setattr(autofix_hard, "default_xsd_path", _fake_default)

    output_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc:
        autofix_hard.main(
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
    assert not default_called

    stdout = capsys.readouterr().out
    assert str(xsd_path.resolve()) in stdout
