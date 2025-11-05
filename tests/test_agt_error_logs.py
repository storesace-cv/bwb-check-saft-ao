from __future__ import annotations

from pathlib import Path

from saftao.validator import validate_file

from tests.test_validator_detection import _write_invalid_xml


LOG_MESSAGE_HINTS = {
    "AuditFile.MasterFiles.ns:CustomerID": "CUSTOMER_WRONG_NAMESPACE",
    "AuditFile.SourceDocuments.SalesInvoices.Invoice.CustomerID": "INVOICE_CUSTOMER_MISSING",
    "AuditFile.Header.TaxRegistrationNumber": "HEADER_TAX_ID_INVALID",
    "AuditFile.Header.CompanyAddress.BuildingNumber": "HEADER_BUILDING_NUMBER_INVALID",
    "AuditFile.Header.CompanyAddress.PostalCode": "HEADER_POSTAL_CODE_INVALID",
    "AuditFile.SourceDocuments.SalesInvoices.Invoice.Line.Tax.TaxCountryRegion": "TAX_COUNTRY_REGION_MISSING",
    "AuditFile.SourceDocuments.Payments.Payment.Line.Tax.TaxCountryRegion": "TAX_COUNTRY_REGION_MISSING",
    "AuditFile.SourceDocuments.WorkingDocuments.WorkDocument.Line.Tax.TaxCountryRegion": "TAX_COUNTRY_REGION_MISSING",
}


def _iter_agt_log_messages() -> list[tuple[str, str]]:
    base = Path(__file__).parent / "saft-error-logs"
    messages: list[tuple[str, str]] = []
    for path in sorted(base.glob("*.txt")):
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.startswith("("):
                    continue
                messages.append((path.name, line.strip()))
    return messages


def test_every_agt_log_entry_has_known_mapping() -> None:
    missing = [
        (name, message)
        for name, message in _iter_agt_log_messages()
        if not any(hint in message for hint in LOG_MESSAGE_HINTS)
    ]

    assert not missing, (
        "Foi encontrado um novo erro AGT sem mapeamento. "
        "Actualize o validador e o dicionário LOG_MESSAGE_HINTS: "
        f"{missing}"
    )


def test_known_agt_errors_are_reported(tmp_path) -> None:
    xml_path = tmp_path / "invalid.xml"
    _write_invalid_xml(xml_path)

    detected_codes = {issue.code for issue in validate_file(xml_path)}
    expected_codes = set(LOG_MESSAGE_HINTS.values())

    assert expected_codes <= detected_codes
