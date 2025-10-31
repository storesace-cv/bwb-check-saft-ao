from pathlib import Path

import pytest

from saftao.autofix.workdocument_balance import (
    repair_workdocument_balance,
    repair_workdocument_balance_in_file,
)


def test_repair_inserts_missing_closing_between_documents(tmp_path: Path) -> None:
    xml = (
        "<AuditFile>\n"
        "  <SourceDocuments>\n"
        "    <WorkingDocuments>\n"
        "      <WorkDocument>\n"
        "        <DocumentNumber>1</DocumentNumber>\n"
        "      </WorkDocument>\n"
        "      <WorkDocument>\n"
        "        <DocumentNumber>2</DocumentNumber>\n"
        "      <WorkDocument>\n"
        "        <DocumentNumber>3</DocumentNumber>\n"
        "      </WorkDocument>\n"
        "    </WorkingDocuments>\n"
        "  </SourceDocuments>\n"
        "</AuditFile>\n"
    )
    path = tmp_path / "doc.xml"
    path.write_text(xml, encoding="utf-8")

    changed = repair_workdocument_balance_in_file(path)

    assert changed is True
    result = path.read_text(encoding="utf-8")
    assert result.count("<WorkDocument>") == 3
    assert result.count("</WorkDocument>") == 3


def test_repair_removes_duplicate_closing() -> None:
    xml = (
        "<WorkingDocuments>\n"
        "  <WorkDocument>\n"
        "    <DocumentNumber>1</DocumentNumber>\n"
        "  </WorkDocument>\n"
        "  </WorkDocument>\n"
        "</WorkingDocuments>\n"
    )
    fixed, changed = repair_workdocument_balance(xml)

    assert changed is True
    assert fixed.count("</WorkDocument>") == 1


@pytest.mark.parametrize(
    "xml",
    [
        "<WorkingDocuments>\n  <WorkDocument></WorkDocument>\n</WorkingDocuments>\n",
        (
            "<WorkingDocuments>\n"
            "  <WorkDocument>\n"
            "    <DocumentNumber>1</DocumentNumber>\n"
            "  </WorkDocument>\n"
            "</WorkingDocuments>\n"
        ),
    ],
)
def test_repair_keeps_balanced_documents_intact(xml: str) -> None:
    fixed, changed = repair_workdocument_balance(xml)

    assert changed is False
    assert fixed == xml
