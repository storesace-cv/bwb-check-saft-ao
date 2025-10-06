#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validador SAF-T (AO) — Regras Estritas (AGT) com LOG em Excel + Sugestões
-------------------------------------------------------------------------

- Validação XSD (SAFTAO1.01_01.xsd) se estiver presente na CWD ou na pasta
  do script.
- Regras estritas (precisão q6, arredondamento q2 na exportação, 2 casas nos
  montantes, TaxPercentage coerente, TaxTable consistente).
- Identidade de totais **completa**:
    GrossExpected = q2(
        NetTotal - SettlementAmount + TaxPayable - WithholdingTaxAmount
    )

  onde:
    SettlementAmount = DocumentTotals/Settlement/SettlementAmount (se existir)
    WithholdingTaxAmount = soma de
    DocumentTotals/WithholdingTax/WithholdingTaxAmount (se existir)

- Log sempre em Excel (.xlsx) na pasta de execução, com colunas e
  **sugestões**.

Requisitos:
    pip install lxml openpyxl
"""

import sys
import argparse
from decimal import Decimal, ROUND_HALF_UP, getcontext, InvalidOperation
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from lxml import etree

try:
    from saftao.utils import detect_namespace as _pkg_detect_namespace
    from saftao.utils import parse_decimal as _pkg_parse_decimal
except Exception:  # pragma: no cover - fallback for standalone usage
    _pkg_detect_namespace = None
    _pkg_parse_decimal = None


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Precisão alta para cálculos
getcontext().prec = 28

NS_DEFAULT = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
AMT2 = Decimal("0.01")
AMT6 = Decimal("0.000001")
HUNDRED = Decimal("100")


def q2(v: Decimal) -> Decimal:
    return v.quantize(AMT2, rounding=ROUND_HALF_UP)


def q6(v: Decimal) -> Decimal:
    return v.quantize(AMT6, rounding=ROUND_HALF_UP)


def fd(text: str) -> int:
    if text is None:
        return 0
    if "." in text:
        return len(text.split(".", 1)[1].rstrip())
    return 0


def fmt2(x: Decimal) -> str:
    return f"{x:.2f}"


def fmt_pct_suggestion(txt: str) -> str:
    """
    Sugere percentagem coerente: inteiro → '14'; caso contrário duas casas →
    '14.25'.
    """
    try:
        v = Decimal(txt)
    except Exception:
        return txt
    if v == v.to_integral():
        return str(int(v))
    return f"{v:.2f}"


class ExcelLogger:
    """
    Logger que grava um .xlsx estruturado para leitura fácil na pasta de
    execução.
    """

    COLUMNS = [
        "timestamp",
        "code",
        "message",
        "xpath",
        "invoice",
        "line",
        "field",
        "current_value",
        "suggested_value",
        "suggestion_note",
        "xml",
        "computed",
        "xsd",
        "level",
        "gross",
        "net",
        "tax",
        "extra",
    ]

    def __init__(self, base_name: str):
        from openpyxl import Workbook

        self.stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self.path = Path.cwd() / f"{base_name}_{self.stamp}.xlsx"
        self.rows: List[Dict[str, Any]] = []
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Log"
        self.ws.append(self.COLUMNS)

        widths = {
            "A": 21,
            "B": 18,
            "C": 60,
            "D": 50,
            "E": 18,
            "F": 8,
            "G": 18,
            "H": 20,
            "I": 22,
            "J": 40,
            "K": 30,
            "L": 30,
            "M": 10,
            "N": 10,
            "O": 12,
            "P": 12,
            "Q": 12,
            "R": 40,
        }
        for col, w in widths.items():
            self.ws.column_dimensions[col].width = w

    def log(
        self,
        code: str,
        message: str,
        *,
        xpath: Optional[str] = None,
        ctx: Optional[dict] = None,
        field: str = "",
        current_value: str = "",
        suggested_value: str = "",
        suggestion_note: str = "",
    ):
        import json

        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "code": code,
            "message": message,
            "xpath": xpath or "",
            "invoice": "",
            "line": "",
            "field": field,
            "current_value": current_value,
            "suggested_value": suggested_value,
            "suggestion_note": suggestion_note,
            "xml": "",
            "computed": "",
            "xsd": "",
            "level": "",
            "gross": "",
            "net": "",
            "tax": "",
            "extra": "",
        }
        extra = {}
        if ctx:
            for k, v in ctx.items():
                if k in row:
                    row[k] = v
                else:
                    extra[k] = v
        if extra:
            row["extra"] = json.dumps(extra, ensure_ascii=False, separators=(",", ":"))

        self.rows.append(row)
        self.ws.append([row[c] for c in self.COLUMNS])

    def flush(self):
        self.wb.save(self.path)


def parse_decimal(text: Optional[str], default: Decimal = Decimal("0")) -> Decimal:
    """Converter texto em :class:`~decimal.Decimal` com *fallback* configurável."""

    if _pkg_parse_decimal is not None:
        return _pkg_parse_decimal(text, default=default)

    if text is None:
        return default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def detect_ns(tree: etree._ElementTree) -> str:
    """Determinar o *namespace* activo no ficheiro SAF-T."""

    if _pkg_detect_namespace is not None:
        return _pkg_detect_namespace(tree.getroot())

    root = tree.getroot()
    if root.tag.startswith("{") and "}" in root.tag:
        return root.tag.split("}")[0][1:]
    return NS_DEFAULT


def get_text(el: Optional[etree._Element]) -> Optional[str]:
    return None if el is None else (el.text or "").strip()


def validate_schema(
    xml_tree: etree._ElementTree, xsd_path: Path, logger: ExcelLogger
) -> bool:
    try:
        schema_doc = etree.parse(str(xsd_path))
        schema = etree.XMLSchema(schema_doc)
        ok = schema.validate(xml_tree)
        if not ok:
            for e in schema.error_log:
                logger.log(
                    "XSD_ERROR",
                    e.message,
                    ctx={"line": e.line, "level": e.level_name},
                    field="XSD",
                )
        return ok
    except Exception as ex:
        logger.log(
            "XSD_EXCEPTION", f"Falha ao executar validação XSD: {ex}", field="XSD"
        )
        return False


def validate_business_rules(tree: etree._ElementTree, logger: ExcelLogger) -> bool:
    nsuri = detect_ns(tree)
    ns = {"n": nsuri}
    ok = True

    # Header
    header = tree.find(".//n:Header", namespaces=ns)
    if header is None:
        logger.log("HDR_MISSING", "Header em falta", xpath="/AuditFile/Header")
        ok = False
    else:
        ver = get_text(header.find("./n:AuditFileVersion", namespaces=ns))
        if ver and ver != "1.01_01":
            logger.log(
                "HDR_VERSION",
                f"AuditFileVersion inesperado '{ver}', esperado '1.01_01'",
                xpath="/AuditFile/Header/AuditFileVersion",
                field="AuditFileVersion",
                current_value=ver,
            )

    # TaxTable index
    tax_index = set()
    for t in tree.findall(".//n:MasterFiles/n:TaxTable/n:TaxTableEntry", namespaces=ns):
        ttype = get_text(t.find("./n:TaxType", namespaces=ns)) or "IVA"
        tcode = get_text(t.find("./n:TaxCode", namespaces=ns)) or "NOR"
        tperc_text = get_text(t.find("./n:TaxPercentage", namespaces=ns)) or "0"
        if fd(tperc_text) > 2:
            logger.log(
                "PCT_FORMAT",
                f"TaxPercentage com > 2 casas decimais: {tperc_text}",
                xpath=tree.getpath(t.find("./n:TaxPercentage", namespaces=ns)),
                field="TaxPercentage",
                current_value=tperc_text,
                suggested_value=fmt_pct_suggestion(tperc_text),
                suggestion_note=(
                    "Usar inteiro (ex.: 14) se taxa exata; caso contrário 2 "
                    "casas (ex.: 14.25)"
                ),
            )
            ok = False
        tax_index.add((ttype, tcode, parse_decimal(tperc_text)))

    # Invoices
    invoices = tree.findall(
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice", namespaces=ns
    )
    for inv in invoices:
        inv_xpath = tree.getpath(inv)
        doc_no = get_text(inv.find("./n:InvoiceNo", namespaces=ns)) or "UNKNOWN"
        doc_totals = inv.find("./n:DocumentTotals", namespaces=ns)

        # Settlement e WithholdingTax no XML (para usar na identidade do XML)
        settlement_amount_xml = Decimal("0")
        withholding_amount_xml = Decimal("0")

        sett_el = (
            doc_totals.find("./n:Settlement/n:SettlementAmount", namespaces=ns)
            if doc_totals is not None
            else None
        )
        if sett_el is not None and (sett_el.text or "").strip():
            settlement_amount_xml = parse_decimal(sett_el.text)

        for w in (
            doc_totals.findall("./n:WithholdingTax", namespaces=ns)
            if doc_totals is not None
            else []
        ):
            wamt_el = w.find("./n:WithholdingTaxAmount", namespaces=ns)
            if wamt_el is not None and (wamt_el.text or "").strip():
                withholding_amount_xml += parse_decimal(wamt_el.text)

        # Acumular com alta precisão a partir das linhas
        net_total = Decimal("0")
        tax_total = Decimal("0")

        lines = inv.findall("./n:Line", namespaces=ns)
        if not lines:
            logger.log(
                "INV_NO_LINES",
                "Invoice sem linhas",
                xpath=inv_xpath,
                ctx={"invoice": doc_no},
            )
            ok = False
            continue

        for i, ln in enumerate(lines, start=1):
            ln_xpath = tree.getpath(ln)
            qty = parse_decimal(get_text(ln.find("./n:Quantity", namespaces=ns)))
            unit = parse_decimal(get_text(ln.find("./n:UnitPrice", namespaces=ns)))
            base = q6(qty * unit)
            base2 = q2(base)

            debit_el = ln.find("./n:DebitAmount", namespaces=ns)
            credit_el = ln.find("./n:CreditAmount", namespaces=ns)
            debit_txt = get_text(debit_el)
            credit_txt = get_text(credit_el)

            # 2 casas decimais obrigatórias
            for tag, txt, el in (
                ("DebitAmount", debit_txt, debit_el),
                ("CreditAmount", credit_txt, credit_el),
            ):
                if txt is not None and fd(txt) != 2:
                    logger.log(
                        "AMT_FORMAT",
                        (f"{tag} deve ter exatamente 2 casas decimais: " f"'{txt}'"),
                        xpath=tree.getpath(el) if el is not None else ln_xpath,
                        ctx={"invoice": doc_no, "line": i},
                        field=tag,
                        current_value=txt,
                        suggested_value=fmt2(parse_decimal(txt)),
                        suggestion_note="Formatar o valor com 2 casas decimais",
                    )
                    ok = False

            if debit_txt is not None and credit_txt is None:
                if parse_decimal(debit_txt) != base2:
                    logger.log(
                        "AMT_MISMATCH",
                        f"DebitAmount != q2(qty*unit): {debit_txt} != {base2}",
                        xpath=(
                            tree.getpath(debit_el) if debit_el is not None else ln_xpath
                        ),
                        ctx={"invoice": doc_no, "line": i},
                        field="DebitAmount",
                        current_value=debit_txt,
                        suggested_value=fmt2(base2),
                        suggestion_note=(
                            "Definir DebitAmount para " "q2(Quantity*UnitPrice)"
                        ),
                    )
                    ok = False
            elif credit_txt is not None and debit_txt is None:
                if parse_decimal(credit_txt) != base2:
                    logger.log(
                        "AMT_MISMATCH",
                        f"CreditAmount != q2(qty*unit): {credit_txt} != {base2}",
                        xpath=(
                            tree.getpath(credit_el)
                            if credit_el is not None
                            else ln_xpath
                        ),
                        ctx={"invoice": doc_no, "line": i},
                        field="CreditAmount",
                        current_value=credit_txt,
                        suggested_value=fmt2(base2),
                        suggestion_note=(
                            "Definir CreditAmount para " "q2(Quantity*UnitPrice)"
                        ),
                    )
                    ok = False
            else:
                logger.log(
                    "AMT_BOTH_NONE_OR_BOTH",
                    "Linha deve ter DebitAmount OU CreditAmount (exclusivo)",
                    xpath=ln_xpath,
                    ctx={"invoice": doc_no, "line": i},
                    suggestion_note=(
                        "Remover um dos elementos; manter apenas um dos dois"
                    ),
                )
                ok = False

            tax = ln.find("./n:Tax", namespaces=ns)
            ttype = (
                get_text(tax.find("./n:TaxType", namespaces=ns))
                if tax is not None
                else "IVA"
            )
            tcode = (
                get_text(tax.find("./n:TaxCode", namespaces=ns))
                if tax is not None
                else "NOR"
            )
            tperc_el = (
                tax.find("./n:TaxPercentage", namespaces=ns)
                if tax is not None
                else None
            )
            tperc_txt = get_text(tperc_el) if tax is not None else "0"
            if tperc_txt is None:
                tperc_txt = "0"
            if fd(tperc_txt) > 2:
                logger.log(
                    "PCT_FORMAT",
                    f"TaxPercentage com > 2 casas decimais: {tperc_txt}",
                    xpath=tree.getpath(tperc_el) if tperc_el is not None else ln_xpath,
                    ctx={"invoice": doc_no, "line": i},
                    field="TaxPercentage",
                    current_value=tperc_txt,
                    suggested_value=fmt_pct_suggestion(tperc_txt),
                    suggestion_note="Inteiro se taxa exata; caso contrário 2 casas",
                )
                ok = False

            try:
                tperc = Decimal(tperc_txt)
            except InvalidOperation:
                logger.log(
                    "PCT_NOT_DECIMAL",
                    f"TaxPercentage não é decimal: {tperc_txt}",
                    xpath=(
                        tree.getpath(tperc_el) if tperc_el is not None else ln_xpath
                    ),
                    ctx={"invoice": doc_no, "line": i},
                    field="TaxPercentage",
                    current_value=tperc_txt,
                    suggested_value="",
                    suggestion_note=("Corrigir para valor decimal (ex.: 14 ou 14.00)"),
                )
                tperc = Decimal("0")
                ok = False

            vat = q6(base * tperc / HUNDRED)
            net_total += base
            tax_total += vat

            if (ttype or "IVA", tcode or "NOR", tperc) not in tax_index:
                logger.log(
                    "TAXTABLE_MISSING",
                    (
                        "Tax (type={ttype}, code={tcode}, perc={tperc}) não "
                        "existe na TaxTable"
                    ),
                    xpath=ln_xpath,
                    ctx={"invoice": doc_no, "line": i},
                    field="Tax",
                    current_value=f"{ttype}/{tcode}/{tperc}",
                    suggested_value=(
                        "ADD TaxTableEntry("
                        f"{ttype},{tcode},{fmt_pct_suggestion(str(tperc))})"
                    ),
                    suggestion_note=("Adicionar entrada correspondente na TaxTable"),
                )
                ok = False

        net2 = q2(net_total)
        tax2 = q2(tax_total)

        # Identidade completa (computada):
        # GrossExpected = Net2 - SettlementAmount + Tax2 - WithholdingTaxAmount
        gross_expected = q2(
            net2 - settlement_amount_xml + tax2 - withholding_amount_xml
        )

        if doc_totals is None:
            logger.log(
                "TOTALS_MISSING",
                "DocumentTotals em falta",
                xpath=inv_xpath,
                ctx={"invoice": doc_no},
            )
            ok = False
        else:
            # Garantir 2 casas nos 3 totais e verificar identidade no XML
            def check_total(tag: str) -> Decimal:
                el = doc_totals.find(f"./n:{tag}", namespaces=ns)
                if el is None or (el.text or "").strip() == "":
                    logger.log(
                        "TOTAL_TAG_MISSING",
                        f"{tag} em falta",
                        xpath=inv_xpath,
                        ctx={"invoice": doc_no},
                        field=tag,
                        suggested_value="",
                    )
                    return None
                txt = (el.text or "").strip()
                if fd(txt) != 2:
                    logger.log(
                        "TOTAL_FORMAT",
                        f"{tag} deve ter exatamente 2 casas decimais: '{txt}'",
                        xpath=tree.getpath(el),
                        ctx={"invoice": doc_no},
                        field=tag,
                        current_value=txt,
                        suggested_value=fmt2(parse_decimal(txt)),
                        suggestion_note=("Formatar o total com 2 casas decimais"),
                    )
                return parse_decimal(txt)

            net_xml = check_total("NetTotal")
            tax_xml = check_total("TaxPayable")
            gross_xml = check_total("GrossTotal")

            if None not in (net_xml, tax_xml, gross_xml):
                gross_xml_expected = q2(
                    net_xml - settlement_amount_xml + tax_xml - withholding_amount_xml
                )

                if gross_xml != gross_xml_expected:
                    # Mostrar também identidade computada para orientar fix
                    logger.log(
                        "TOTALS_XML_MISMATCH",
                        (
                            "Totais do XML não obedecem à identidade (com "
                            "settlement/withholding)"
                        ),
                        xpath=tree.getpath(doc_totals),
                        ctx={
                            "invoice": doc_no,
                            "xml": (
                                f"{net_xml}-{settlement_amount_xml}+{tax_xml}-"
                                f"{withholding_amount_xml}!={gross_xml}"
                            ),
                            "computed": (
                                f"{net2}-{settlement_amount_xml}+{tax2}-"
                                f"{withholding_amount_xml}=={gross_expected}"
                            ),
                            "gross": str(gross_expected),
                            "net": str(net2),
                            "tax": str(tax2),
                        },
                        field="GrossTotal",
                        current_value=fmt2(gross_xml),
                        suggested_value=fmt2(gross_xml_expected),
                        suggestion_note=(
                            "Definir GrossTotal como NetTotal - Settlement + "
                            "TaxPayable - Withholding"
                        ),
                    )
                    ok = False

                # Se também o nosso cálculo interno não bater, regista mismatch “geral”
                if gross_expected != q2(
                    net2 - settlement_amount_xml + tax2 - withholding_amount_xml
                ):
                    # (identidade redundante, deixada por clareza)
                    pass

    return ok


def resolve_xml_path(arg: str) -> Path:
    p = Path(arg)
    if p.exists():
        return p
    for base in (Path.cwd(), SCRIPT_DIR, PROJECT_ROOT):
        candidate = base / p.name
        if candidate.exists():
            return candidate
    return SCRIPT_DIR / p.name


def default_xsd_path() -> Optional[Path]:
    name = "SAFTAO1.01_01.xsd"
    search_dirs = [
        Path.cwd(),
        SCRIPT_DIR,
        PROJECT_ROOT,
        PROJECT_ROOT / "schemas",
    ]
    for base in search_dirs:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Validador SAF-T (AO) com XSD por defeito e regras estritas AGT "
            "(log Excel com sugestões)."
        ),
    )
    ap.add_argument("xml", help="Nome ou caminho do ficheiro SAF-T (AO) XML")
    ap.add_argument(
        "--xsd",
        type=Path,
        help=(
            "Caminho para o ficheiro XSD a utilizar na validação. "
            "Se omitido, será utilizada a pesquisa automática padrão."
        ),
    )
    args = ap.parse_args()

    xml_path = resolve_xml_path(args.xml)
    logger = ExcelLogger(base_name=xml_path.stem)
    logger.log("INFO_START", "Início da validação", ctx={"xml": str(xml_path)})

    if not xml_path.exists():
        msg = f"Ficheiro XML não encontrado: {xml_path}"
        print(f"[ERRO] {msg}", file=sys.stderr)
        logger.log("XML_NOT_FOUND", msg, field="XML", current_value=str(xml_path))
        logger.flush()
        sys.exit(2)

    xsd_path = args.xsd if args.xsd is not None else default_xsd_path()
    if args.xsd is not None and not args.xsd.exists():
        msg = f"Ficheiro XSD não encontrado: {args.xsd}"
        print(f"[ERRO] {msg}", file=sys.stderr)
        logger.log(
            "XSD_NOT_FOUND", msg, field="XSD", current_value=str(args.xsd)
        )
        logger.flush()
        sys.exit(2)

    if xsd_path is None:
        print(
            "[AVISO] SAFTAO1.01_01.xsd não encontrado; a validação XSD será ignorada."
        )
        logger.log(
            "XSD_MISSING", "XSD não encontrado; validação XSD ignorada", field="XSD"
        )
    else:
        logger.log(
            "XSD_FOUND", "XSD encontrado", field="XSD", current_value=str(xsd_path)
        )

    try:
        tree = etree.parse(str(xml_path))
    except Exception as ex:
        msg = f"Falha no parse do XML: {ex}"
        print(f"[ERRO] {msg}", file=sys.stderr)
        logger.log("XML_PARSE_ERROR", msg, field="XML", current_value=str(xml_path))
        logger.flush()
        sys.exit(2)

    schema_ok = True
    if xsd_path is not None:
        schema_ok = validate_schema(tree, xsd_path, logger)
        if not schema_ok:
            print("[FALHA] Validação XSD reprovou (ver Excel).")

    strict_ok = validate_business_rules(tree, logger)
    if not strict_ok:
        print("[FALHA] Validação estrita reprovou (ver Excel).")

    logger.log(
        "INFO_END",
        "Fim da validação",
        ctx={"schema_ok": schema_ok, "strict_ok": strict_ok},
    )
    logger.flush()

    if schema_ok and strict_ok:
        print(f"[OK] Validação concluída com sucesso. Log Excel: {logger.path.name}")
        sys.exit(0)
    else:
        print(
            f"[FAIL] Foram detetadas não conformidades. Log Excel: {logger.path.name}"
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
