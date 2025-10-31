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
    <WorkingDocuments>
      <WorkDocument>
        <DocumentNumber>CM 1</DocumentNumber>
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
      </WorkDocument>
    </WorkingDocuments>
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
    assert _xpath(
        tree,
        ".//n:WorkingDocuments/n:WorkDocument[n:DocumentNumber='CM 1']/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:WorkingDocuments/n:WorkDocument/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["PT"]


def test_soft_fix_formats_workdocument_totals():
    xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <Header />
  <MasterFiles />
  <SourceDocuments>
    <WorkingDocuments>
      <WorkDocument>
        <DocumentNumber>WD 1</DocumentNumber>
        <Line>
          <LineNumber>1</LineNumber>
          <Quantity>1</Quantity>
          <UnitPrice>100</UnitPrice>
          <CreditAmount>100</CreditAmount>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NOR</TaxCode>
            <TaxPercentage>14</TaxPercentage>
          </Tax>
        </Line>
        <DocumentTotals>
          <TaxPayable>0</TaxPayable>
          <NetTotal>0</NetTotal>
          <GrossTotal>0</GrossTotal>
        </DocumentTotals>
      </WorkDocument>
    </WorkingDocuments>
  </SourceDocuments>
</AuditFile>
"""

    tree = _parse(xml)
    autofix_soft.fix_xml(tree, Path("dummy.xml"), _DummyLogger())

    totals = tree.xpath(
        ".//n:WorkingDocuments/n:WorkDocument[n:DocumentNumber='WD 1']/n:DocumentTotals",
        namespaces=NS,
    )[0]

    assert totals.findtext("n:TaxPayable", namespaces=NS) == "14.00"
    assert totals.findtext("n:NetTotal", namespaces=NS) == "100.00"
    assert totals.findtext("n:GrossTotal", namespaces=NS) == "114.00"


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
    assert _xpath(
        tree,
        ".//n:WorkingDocuments/n:WorkDocument[n:DocumentNumber='CM 1']/n:Line[n:LineNumber='1']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["AO"]
    assert _xpath(
        tree,
        ".//n:WorkingDocuments/n:WorkDocument/n:Line[n:LineNumber='2']/n:Tax/n:TaxCountryRegion/text()",
    ) == ["PT"]


def test_soft_fix_normalizes_tax_table_entries():
    xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <Header />
  <MasterFiles>
    <TaxTable>
      <TaxTableEntry>
        <TaxCountryRegion>AO</TaxCountryRegion>
        <Description>IVA 14%</Description>
        <TaxPercentage>14</TaxPercentage>
      </TaxTableEntry>
      <TaxTableEntry>
        <TaxType></TaxType>
        <TaxCountryRegion>AO</TaxCountryRegion>
        <TaxCode>RED</TaxCode>
        <Description>IVA 5%</Description>
        <TaxPercentage>5.00</TaxPercentage>
      </TaxTableEntry>
    </TaxTable>
  </MasterFiles>
</AuditFile>
"""

    tree = _parse(xml)
    logger = _DummyLogger()

    autofix_soft.fix_xml(tree, Path("dummy.xml"), logger)

    entries = tree.xpath(
        ".//n:MasterFiles/n:TaxTable/n:TaxTableEntry", namespaces=NS
    )
    assert len(entries) == 2

    def _child_names(entry):
        return [etree.QName(child.tag).localname for child in entry]

    first = entries[0]
    assert first.findtext("./n:TaxType", namespaces=NS) == "IVA"
    assert first.findtext("./n:TaxCode", namespaces=NS) == "NOR"
    assert _child_names(first)[:5] == [
        "TaxType",
        "TaxCountryRegion",
        "TaxCode",
        "Description",
        "TaxPercentage",
    ]

    second = entries[1]
    assert second.findtext("./n:TaxType", namespaces=NS) == "IVA"
    assert second.findtext("./n:TaxCode", namespaces=NS) == "RED"
    assert _child_names(second)[:5] == [
        "TaxType",
        "TaxCountryRegion",
        "TaxCode",
        "Description",
        "TaxPercentage",
    ]

    actions = [call_args[0] for call_args, _ in logger.records]
    assert actions.count("FIX_TAXTABLE_TAXTYPE") == 2
    assert "FIX_TAXTABLE_TAXCODE" in actions


def test_hard_fix_normalizes_tax_table_entries():
    xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <Header />
  <MasterFiles>
    <TaxTable>
      <TaxTableEntry>
        <TaxCountryRegion>AO</TaxCountryRegion>
        <Description>IVA 14%</Description>
        <TaxPercentage>14</TaxPercentage>
      </TaxTableEntry>
      <TaxTableEntry>
        <TaxType></TaxType>
        <TaxCountryRegion>AO</TaxCountryRegion>
        <TaxCode>RED</TaxCode>
        <Description>IVA 5%</Description>
        <TaxPercentage>5.00</TaxPercentage>
      </TaxTableEntry>
    </TaxTable>
  </MasterFiles>
</AuditFile>
"""

    tree = _parse(xml)

    autofix_hard.fix_xml(tree, Path("dummy.xml"))

    entries = tree.xpath(
        ".//n:MasterFiles/n:TaxTable/n:TaxTableEntry", namespaces=NS
    )
    assert len(entries) == 2

    first = entries[0]
    assert first.findtext("./n:TaxType", namespaces=NS) == "IVA"
    assert first.findtext("./n:TaxCode", namespaces=NS) == "NOR"

    second = entries[1]
    assert second.findtext("./n:TaxType", namespaces=NS) == "IVA"
    assert second.findtext("./n:TaxCode", namespaces=NS) == "RED"

    for entry in entries:
        names = [etree.QName(child.tag).localname for child in entry][:5]
        assert names == [
            "TaxType",
            "TaxCountryRegion",
            "TaxCode",
            "Description",
            "TaxPercentage",
        ]
