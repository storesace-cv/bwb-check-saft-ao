from __future__ import annotations

from pathlib import Path

from lxml import etree

from saftao.commands.validator_strict import validate_business_rules
from saftao.validator import validate_file

NAMESPACE = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"


def _write_invalid_xml(path: Path) -> None:
    path.write_text(
        f"""<?xml version='1.0' encoding='UTF-8'?>
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
""",
        encoding="utf-8",
    )


def test_validator_reports_expected_errors(tmp_path):
    xml_path = tmp_path / "invalid.xml"
    _write_invalid_xml(xml_path)

    issues = list(validate_file(xml_path))

    codes = {issue.code for issue in issues}
    assert codes == {
        "CUSTOMER_WRONG_NAMESPACE",
        "INVOICE_CUSTOMER_MISSING",
        "HEADER_TAX_ID_INVALID",
        "TAX_COUNTRY_REGION_MISSING",
    }

    header_issue = next(i for i in issues if i.code == "HEADER_TAX_ID_INVALID")
    assert header_issue.details["suggested_value"] == "123456789"

    invoice_issue = next(i for i in issues if i.code == "INVOICE_CUSTOMER_MISSING")
    assert invoice_issue.details["customer_id"] == "1000"


class _DummyLogger:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    def log(self, code: str, message: str, **kwargs: object) -> None:
        entry = {"code": code, "message": message}
        entry.update(kwargs)
        self.entries.append(entry)


def test_validator_strict_includes_additional_issues(tmp_path):
    xml_path = tmp_path / "invalid.xml"
    _write_invalid_xml(xml_path)

    tree = etree.parse(str(xml_path))
    logger = _DummyLogger()

    ok = validate_business_rules(tree, logger)

    assert not ok
    codes = {entry["code"] for entry in logger.entries}
    assert {
        "CUSTOMER_WRONG_NAMESPACE",
        "INVOICE_CUSTOMER_MISSING",
        "HEADER_TAX_ID_INVALID",
        "TAX_COUNTRY_REGION_MISSING",
    }.issubset(codes)
