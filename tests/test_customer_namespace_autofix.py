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


def _build_xml_tree() -> etree._ElementTree:
    xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\" xmlns:ns=\"{NAMESPACE}\">
  <Header>
    <TaxRegistrationNumber>AO123456789</TaxRegistrationNumber>
  </Header>
  <MasterFiles>
    <ns:Customer>
      <ns:CustomerID>1000</ns:CustomerID>
      <ns:CustomerTaxID>999999990</ns:CustomerTaxID>
      <ns:CompanyName>Cliente Teste</ns:CompanyName>
      <ns:SelfBillingIndicator>0</ns:SelfBillingIndicator>
    </ns:Customer>
  </MasterFiles>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 1/1</InvoiceNo>
        <CustomerID>1000</CustomerID>
        <Line>
          <LineNumber>1</LineNumber>
          <Tax>
            <TaxType>IVA</TaxType>
            <TaxCode>NOR</TaxCode>
          </Tax>
        </Line>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
"""
    return etree.ElementTree(etree.fromstring(xml.encode("utf-8")))


def _assert_namespace_normalised(root: etree._Element) -> None:
    customers = root.xpath(".//n:MasterFiles/n:Customer", namespaces=NS)
    assert customers, "expected a customer element"
    for customer in customers:
        for element in customer.iter():
            qname = etree.QName(element)
            if qname.namespace == NAMESPACE:
                assert element.prefix is None


def _assert_tax_country_region(root: etree._Element) -> None:
    values = root.xpath(
        ".//n:SourceDocuments//n:Tax/n:TaxCountryRegion/text()",
        namespaces=NS,
    )
    assert values == ["AO"]


def test_soft_autofix_normalises_customer_and_tax_registration(tmp_path):
    tree = _build_xml_tree()
    logger = _DummyLogger()

    autofix_soft.fix_xml(tree, Path(tmp_path / "dummy.xml"), logger)

    root = tree.getroot()
    _assert_namespace_normalised(root)
    _assert_tax_country_region(root)

    tax_value = root.xpath(
        "string(.//n:Header/n:TaxRegistrationNumber)",
        namespaces=NS,
    )
    assert tax_value == "123456789"

    codes = [record[0][0] for record in logger.records]
    assert "FIX_CUSTOMER_NAMESPACE" in codes
    assert "FIX_TAX_REGISTRATION" in codes


def test_hard_autofix_normalises_customer_and_tax_registration(tmp_path):
    tree = _build_xml_tree()

    autofix_hard.fix_xml(tree, Path(tmp_path / "dummy.xml"))

    root = tree.getroot()
    _assert_namespace_normalised(root)
    _assert_tax_country_region(root)

    tax_value = root.xpath(
        "string(.//n:Header/n:TaxRegistrationNumber)",
        namespaces=NS,
    )
    assert tax_value == "123456789"
