from __future__ import annotations

from pathlib import Path

from lxml import etree

from saftao.commands import autofix_hard, autofix_soft

NAMESPACE = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
NS = {"n": NAMESPACE}


class _DummyLogger:
    def __init__(self) -> None:
        self.records: list[tuple[tuple, dict]] = []

    def log(self, *args, **kwargs) -> None:  # pragma: no cover - trivial
        self.records.append((args, kwargs))


def _build_xml() -> str:
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <Header>
    <CompanyID>123456789</CompanyID>
  </Header>
  <MasterFiles />
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 1/1</InvoiceNo>
        <InvoiceType>FR</InvoiceType>
        <InvoiceDate>2023-01-01</InvoiceDate>
        <Line>
          <LineNumber>1</LineNumber>
          <Quantity>1</Quantity>
          <UnitPrice>100.00</UnitPrice>
          <DebitAmount>100.00</DebitAmount>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NOR</TaxCode>
            <TaxPercentage>14.00</TaxPercentage>
          </Tax>
        </Line>
        <Line>
          <LineNumber>2</LineNumber>
          <Quantity>1</Quantity>
          <UnitPrice>50.00</UnitPrice>
          <DebitAmount>50.00</DebitAmount>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>ISE</TaxCode>
            <TaxCountryRegion></TaxCountryRegion>
            <TaxPercentage>0.00</TaxPercentage>
            <TaxExemptionReason>M00</TaxExemptionReason>
          </Tax>
        </Line>
        <Line>
          <LineNumber>3</LineNumber>
          <Quantity>1</Quantity>
          <UnitPrice>25.00</UnitPrice>
          <DebitAmount>25.00</DebitAmount>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NS</TaxCode>
            <TaxPercentage>0.00</TaxPercentage>
          </Tax>
        </Line>
        <DocumentTotals>
          <TaxPayable>0.00</TaxPayable>
          <NetTotal>0.00</NetTotal>
          <GrossTotal>0.00</GrossTotal>
        </DocumentTotals>
      </Invoice>
    </SalesInvoices>
    <Payments>
      <Payment>
        <PaymentRefNo>RC 1</PaymentRefNo>
        <Line>
          <LineNumber>1</LineNumber>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NOR</TaxCode>
            <TaxPercentage>14.00</TaxPercentage>
          </Tax>
        </Line>
        <Line>
          <LineNumber>2</LineNumber>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NOR</TaxCode>
            <TaxCountryRegion>PT</TaxCountryRegion>
            <TaxPercentage>14.00</TaxPercentage>
          </Tax>
        </Line>
      </Payment>
    </Payments>
  </SourceDocuments>
</AuditFile>
"""


def _xpath(tree: etree._ElementTree, expression: str) -> list[str]:
    return [
        value.strip()
        for value in tree.xpath(expression, namespaces=NS)
    ]


def _parse(xml: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(xml.encode("utf-8")))


def test_soft_fix_adds_tax_country_region_in_all_tax_blocks():
    xml = _build_xml()
    tree = _parse(xml)

    autofix_soft.fix_xml(tree, Path("dummy.xml"), _DummyLogger())

    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='3']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:Payments/n:Payment[n:PaymentRefNo='RC 1']/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:Payments/n:Payment/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["PT"]


def test_hard_fix_preserves_foreign_tax_country_region_and_defaults_to_ao():
    xml = _build_xml()
    tree = _parse(xml)

    autofix_hard.fix_xml(tree, Path("dummy.xml"))

    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:SalesInvoices/n:Invoice/n:Line[n:LineNumber='3']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:Payments/n:Payment[n:PaymentRefNo='RC 1']/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:Payments/n:Payment/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["PT"]
