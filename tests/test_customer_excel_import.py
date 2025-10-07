"""Tests for importing missing customers from Excel into MasterFiles."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from openpyxl import Workbook

from saftao.autofix.soft import (
    _DEFAULT_CUSTOMER_FILENAME,
    ensure_invoice_customers_exported,
)


NAMESPACE = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
NS = {"n": NAMESPACE}


def _create_sample_xml(path: Path) -> None:
    content = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <Header></Header>
  <MasterFiles>
    <Customer>
      <CustomerID>EXISTING</CustomerID>
      <AccountID>EXISTING</AccountID>
      <CustomerTaxID>123456789</CustomerTaxID>
      <CompanyName>Cliente Existente</CompanyName>
      <BillingAddress>
        <AddressDetail>Morada existente</AddressDetail>
        <City>Luanda</City>
        <Country>AO</Country>
      </BillingAddress>
      <SelfBillingIndicator>0</SelfBillingIndicator>
    </Customer>
  </MasterFiles>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 1/1</InvoiceNo>
        <CustomerID>1001</CustomerID>
      </Invoice>
      <Invoice>
        <InvoiceNo>FT 2/1</InvoiceNo>
        <CustomerID>EXISTING</CustomerID>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
"""
    path.write_text(content, encoding="utf-8")


def _create_excel(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Código",
        "Nome",
        "Contribuinte",
        "Localidade",
        "País",
        "Telemovel",
    ])
    sheet.append([
        "1001",
        "Cliente 1001",
        "245678901",
        "Luanda",
        "AO",
        "923456789",
    ])
    workbook.save(path)


def test_missing_customer_added_from_excel(tmp_path, monkeypatch):
    xml_path = tmp_path / "saf-t.xml"
    excel_path = tmp_path / "clientes.xlsx"
    _create_sample_xml(xml_path)
    _create_excel(excel_path)

    monkeypatch.setenv("BWB_SAFTAO_CUSTOMER_FILE", str(excel_path))

    issues = list(ensure_invoice_customers_exported(xml_path))

    assert issues, "should report the addition of the missing customer"
    assert "Cliente '1001'" in issues[0].message
    assert issues[0].details["customer_id"] == "1001"
    assert issues[0].details["source"] == str(excel_path)

    tree = etree.parse(str(xml_path))
    customers = tree.xpath(
        ".//n:MasterFiles/n:Customer[n:CustomerID='1001']",
        namespaces=NS,
    )
    assert len(customers) == 1
    customer = customers[0]
    assert customer.findtext("n:CustomerTaxID", namespaces=NS) == "245678901"
    assert customer.findtext("n:CompanyName", namespaces=NS) == "Cliente 1001"
    assert customer.findtext(
        "n:BillingAddress/n:City",
        namespaces=NS,
    ) == "Luanda"
    assert customer.findtext("n:Telephone", namespaces=NS) == "923456789"
    assert customer.findtext("n:SelfBillingIndicator", namespaces=NS) == "0"


def test_no_missing_customers_returns_empty(tmp_path, monkeypatch):
    xml_path = tmp_path / "saf-t.xml"
    content = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <MasterFiles>
    <Customer>
      <CustomerID>1001</CustomerID>
      <AccountID>1001</AccountID>
      <CustomerTaxID>123456789</CustomerTaxID>
      <CompanyName>Cliente 1001</CompanyName>
      <BillingAddress>
        <AddressDetail>Morada</AddressDetail>
        <City>Luanda</City>
        <Country>AO</Country>
      </BillingAddress>
      <SelfBillingIndicator>0</SelfBillingIndicator>
    </Customer>
  </MasterFiles>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <CustomerID>1001</CustomerID>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
"""
    xml_path.write_text(content, encoding="utf-8")

    monkeypatch.delenv("BWB_SAFTAO_CUSTOMER_FILE", raising=False)

    issues = ensure_invoice_customers_exported(xml_path)
    assert list(issues) == []


def test_default_excel_file_used_when_present(tmp_path, monkeypatch):
    xml_path = tmp_path / "saf-t.xml"
    _create_sample_xml(xml_path)

    default_dir = tmp_path / "addons"
    default_dir.mkdir()
    default_excel = default_dir / _DEFAULT_CUSTOMER_FILENAME
    _create_excel(default_excel)

    monkeypatch.delenv("BWB_SAFTAO_CUSTOMER_FILE", raising=False)
    import saftao.autofix.soft as soft_module

    monkeypatch.setattr(soft_module, "_DEFAULT_ADDONS_DIR", default_dir, raising=False)

    issues = list(ensure_invoice_customers_exported(xml_path))

    assert issues, "should report the addition of the missing customer"
    assert issues[0].details["source"] == str(default_excel)


def test_customer_inserted_before_tax_table(tmp_path, monkeypatch):
    xml_path = tmp_path / "saf-t.xml"
    content = f"""<?xml version='1.0' encoding='UTF-8'?>
<AuditFile xmlns=\"{NAMESPACE}\">
  <MasterFiles>
    <GeneralLedgerAccounts />
    <TaxTable>
      <TaxTableEntry>
        <TaxType>IVA</TaxType>
        <TaxCountryRegion>AO</TaxCountryRegion>
        <TaxCode>N</TaxCode>
        <Description>Normal</Description>
        <TaxPercentage>14</TaxPercentage>
      </TaxTableEntry>
    </TaxTable>
  </MasterFiles>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 3/1</InvoiceNo>
        <CustomerID>1001</CustomerID>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
"""
    xml_path.write_text(content, encoding="utf-8")

    excel_path = tmp_path / "clientes.xlsx"
    _create_excel(excel_path)

    monkeypatch.setenv("BWB_SAFTAO_CUSTOMER_FILE", str(excel_path))

    issues = list(ensure_invoice_customers_exported(xml_path))
    assert issues, "expected the missing customer to be added"

    tree = etree.parse(str(xml_path))
    child_tags = [
        child.tag.split("}", 1)[-1]
        for child in tree.xpath("/n:AuditFile/n:MasterFiles/*", namespaces=NS)
    ]

    assert child_tags == ["GeneralLedgerAccounts", "Customer", "TaxTable"]
