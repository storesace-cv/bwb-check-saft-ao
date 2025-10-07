from __future__ import annotations

from pathlib import Path

from lxml import etree

from saftao.autofix.soft import normalize_invoice_type_vd

NAMESPACE = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
NS = {"n": NAMESPACE}


def _write_invoice(path: Path, invoice_type: str) -> None:
    path.write_text(
        f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>VD 1/1</InvoiceNo>
        <InvoiceType>{invoice_type}</InvoiceType>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
""",
        encoding="utf-8",
    )


def test_invoice_type_vd_is_normalised(tmp_path):
    xml_path = tmp_path / "vd.xml"
    _write_invoice(xml_path, "VD")

    issues = list(normalize_invoice_type_vd(xml_path))

    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "FIX_INVOICE_TYPE"
    assert issue.details["invoice"] == "VD 1/1"

    tree = etree.parse(str(xml_path))
    invoice_type = tree.xpath(
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice/n:InvoiceType/text()",
        namespaces=NS,
    )
    assert invoice_type == ["FR"]


def test_invoice_type_vd_noop_when_not_present(tmp_path):
    xml_path = tmp_path / "ft.xml"
    _write_invoice(xml_path, "FR")

    issues = list(normalize_invoice_type_vd(xml_path))

    assert issues == []

    tree = etree.parse(str(xml_path))
    invoice_type = tree.xpath(
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice/n:InvoiceType/text()",
        namespaces=NS,
    )
    assert invoice_type == ["FR"]
