#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Ferramenta de auto-correcção SAF-T (AO) (*soft*).

Principais funcionalidades:

- Garante que ``TaxCountryRegion`` existe em todas as linhas ``Tax`` com o
  valor ``AO`` por omissão, preservando jurisdições específicas quando
  indicadas.
- Corrige valores conforme regras estritas (q6 nos cálculos, q2 na exportação,
  2 casas decimais).
- Garante a ordem mínima exigida no XSD para os blocos tocados:
  * ``Line``: ``... Quantity, UnitPrice, (DebitAmount|CreditAmount), Tax, ...``
  * ``DocumentTotals``: ``TaxPayable, NetTotal, GrossTotal``
  * ``TaxTableEntry``: ``TaxType, TaxCode, Description, TaxPercentage``
- Recalcula ``GrossTotal`` com a identidade completa::

      Gross = q2(NetTotal - SettlementAmount + TaxPayable - WithholdingTaxAmount)

- Normaliza ``TaxTable``: ``TaxPercentage`` → inteiro se exato; senão 2 casas.
- Valida contra ``SAFTAO1.01_01.xsd`` se estiver na CWD ou na pasta do script.
- Grava sempre:
  * XML: cria versões numeradas do ficheiro original ``*_v.xx.xml``. Quando a
    validação XSD falha é acrescentado ``_invalido`` ao nome.
  * LOG Excel: ``NOME_XML_YYYYMMDDTHHMMSSZ_autofix.xlsx`` (ações aplicadas,
    antes/depois) na pasta de saída.
- Permite definir uma pasta de destino alternativa através de ``--output-dir``.

Uso::

    python saft_ao_autofix_soft.py MEU_FICHEIRO.xml [--output-dir PASTA_DESTINO]
"""

import argparse
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]

from saftao.autofix.soft import (
    ensure_invoice_customers_exported_tree,
    normalize_invoice_type_vd_tree,
)

# Precisão alta
getcontext().prec = 28

NS_DEFAULT = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
AMT2 = Decimal("0.01")
AMT6 = Decimal("0.000001")
HUNDRED = Decimal("100")

# ------------------------- Utilitários numéricos -------------------------


def q2(v: Decimal) -> Decimal:
    return v.quantize(AMT2, rounding=ROUND_HALF_UP)


def q6(v: Decimal) -> Decimal:
    return v.quantize(AMT6, rounding=ROUND_HALF_UP)


def fmt2(x: Decimal) -> str:
    return f"{x:.2f}"


def fmt_pct(txt: str) -> str:
    """Percentagem coerente: inteiro → '14'; senão 2 casas → '14.25'."""
    try:
        v = Decimal(txt)
    except Exception:
        return txt
    if v == v.to_integral():
        return str(int(v))
    return f"{v:.2f}"


def parse_decimal(text: Optional[str], default: Decimal = Decimal("0")) -> Decimal:
    if text is None:
        return default
    try:
        return Decimal(text.strip())
    except (InvalidOperation, ValueError):
        return default


def detect_ns(tree: etree._ElementTree) -> str:
    root = tree.getroot()
    if root.tag.startswith("{") and "}" in root.tag:
        return root.tag.split("}")[0][1:]
    return NS_DEFAULT


def get_text(el):
    return None if el is None else (el.text or "").strip()


# ------------------------- Logger Excel ----------------------------------


class ExcelLogger:
    """
    Logger em Excel (.xlsx) criado na pasta indicada (ou CWD por omissão).
    Colunas:
      timestamp, action_code, message, xpath, invoice, line,
      field, old_value, new_value, note, extra
    """

    COLUMNS = [
        "timestamp",
        "action_code",
        "message",
        "xpath",
        "invoice",
        "line",
        "field",
        "old_value",
        "new_value",
        "note",
        "extra",
    ]

    def __init__(self, base_name: str, output_dir: Path | None = None):
        from openpyxl import Workbook

        self.stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        target_dir = (
            Path(output_dir).expanduser() if output_dir is not None else Path.cwd()
        )
        self.path = target_dir / f"{base_name}_{self.stamp}_autofix.xlsx"
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "AutoFix Log"
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
            "I": 20,
            "J": 40,
            "K": 40,
        }
        for col, w in widths.items():
            self.ws.column_dimensions[col].width = w

    def log(
        self,
        action_code: str,
        message: str,
        *,
        xpath: str = "",
        invoice: str = "",
        line: str = "",
        field: str = "",
        old_value: str = "",
        new_value: str = "",
        note: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ):
        import json

        extra_text = ""
        if extra:
            extra_text = json.dumps(extra, ensure_ascii=False, separators=(",", ":"))
        row = [
            datetime.utcnow().isoformat(),
            action_code,
            message,
            xpath,
            invoice,
            line,
            field,
            old_value,
            new_value,
            note,
            extra_text,
        ]
        self.ws.append(row)

    def flush(self):
        self.wb.save(self.path)


# ------------------------- Helpers de ordenação --------------------------


def localname(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def reorder_children(parent, order_local_names: List[str]):
    by_name = {name: [] for name in order_local_names}
    others = []
    for child in list(parent):
        name = localname(child.tag)
        if name in by_name:
            by_name[name].append(child)
        else:
            others.append(child)
    # limpar e reanexar
    for child in list(parent):
        parent.remove(child)
    for name in order_local_names:
        for node in by_name[name]:
            parent.append(node)
    for node in others:
        parent.append(node)


def ensure_line_order(line_el):
    order = [
        "LineNumber",
        "OrderReferences",
        "ProductCode",
        "ProductDescription",
        "Quantity",
        "UnitOfMeasure",
        "UnitPrice",
        "TaxBase",
        "TaxPointDate",
        "References",
        "Description",
        "ProductSerialNumber",
        "DebitAmount",
        "CreditAmount",
        "Tax",
        "TaxExemptionReason",
        "TaxExemptionCode",
        "SettlementAmount",
        "CustomsInformation",
    ]
    reorder_children(line_el, order)


def ensure_document_totals_order(doc_totals_el):
    # ORDEM CORRETA segundo XSD: TaxPayable → NetTotal → GrossTotal
    order = ["TaxPayable", "NetTotal", "GrossTotal"]
    reorder_children(doc_totals_el, order)


def ensure_taxtable_entry_order(entry_el):
    order = ["TaxType", "TaxCode", "Description", "TaxPercentage"]
    reorder_children(entry_el, order)


# ------------------------- Normalização TaxCountryRegion -----------------


def _position_tax_country_region(tax_el, nsuri: str, region_el):
    """Coloca ``TaxCountryRegion`` imediatamente após ``TaxCode``."""

    ns = {"n": nsuri}
    tax_code = tax_el.find("./n:TaxCode", namespaces=ns)
    if region_el.getparent() is tax_el:
        tax_el.remove(region_el)

    if tax_code is not None:
        children = list(tax_el)
        try:
            index = children.index(tax_code) + 1
        except ValueError:
            index = len(children)
        tax_el.insert(index, region_el)
    else:
        tax_el.append(region_el)


def ensure_tax_country_region(
    tax_el,
    nsuri: str,
    logger: ExcelLogger,
    *,
    owner: str,
    line: int | str | None,
    xpath: str,
    default: str = "AO",
) -> None:
    """Garantir presença e valor de ``TaxCountryRegion`` num bloco ``Tax``."""

    ns = {"n": nsuri}
    region_el = tax_el.find("./n:TaxCountryRegion", namespaces=ns)
    created = False
    if region_el is None:
        region_el = etree.Element(f"{{{nsuri}}}TaxCountryRegion")
        created = True

    _position_tax_country_region(tax_el, nsuri, region_el)

    current = get_text(region_el) or ""
    if not current:
        region_el.text = default
        action_code = "ADD_NODE" if created else "FIX_TAXCOUNTRYREGION"
        message = (
            "Adicionado TaxCountryRegion em Tax (valor por omissão)"
            if created
            else "TaxCountryRegion definido para valor por omissão"
        )
        logger.log(
            action_code,
            message,
            invoice=owner,
            line="" if line is None else str(line),
            field="TaxCountryRegion",
            old_value="" if created else current,
            new_value=default,
            xpath=xpath,
        )
    # Valor não vazio é preservado (por exemplo, jurisdição estrangeira).


# ------------------------- Construção / fixes ----------------------------


def normalize_taxtable_percentages(root, nsuri: str, logger: ExcelLogger):
    """
    Normaliza TaxPercentage em todas as TaxTableEntry (inteiro se exato; senão
    2 casas) e assegura ordem.
    """
    ns = {"n": nsuri}
    changed = False
    for entry in root.findall(
        ".//n:MasterFiles/n:TaxTable/n:TaxTableEntry", namespaces=ns
    ):
        pct_el = entry.find("./n:TaxPercentage", namespaces=ns)
        if pct_el is not None:
            old = get_text(pct_el) or ""
            new = fmt_pct(old or "0")
            if old != new:
                logger.log(
                    "FIX_TAXTABLE_PCT",
                    "TaxTableEntry.TaxPercentage formatado",
                    field="TaxPercentage",
                    old_value=old,
                    new_value=new,
                )
                pct_el.text = new
                changed = True
        ensure_taxtable_entry_order(entry)
    if changed:
        logger.log(
            "ORDER_ENSURE",
            "Ordenação aplicada nas TaxTableEntry",
            note="TaxType, TaxCode, Description, TaxPercentage",
        )


def ensure_tax_table_entry(
    root,
    nsuri: str,
    ttype: str,
    tcode: str,
    tperc_text: str,
    logger: ExcelLogger,
    inv_no: str,
    ln_idx: int,
    ln_xpath: str,
):
    ns = {"n": nsuri}
    mf = root.find(".//n:MasterFiles", namespaces=ns)
    if mf is None:
        mf = etree.SubElement(root, f"{{{nsuri}}}MasterFiles")
        logger.log("ADD_NODE", "Criado MasterFiles", note="MasterFiles inexistente")

    tt = mf.find("./n:TaxTable", namespaces=ns)
    if tt is None:
        tt = etree.SubElement(mf, f"{{{nsuri}}}TaxTable")
        logger.log("ADD_NODE", "Criado TaxTable", note="TaxTable inexistente")

    # já existe?
    for entry in tt.findall("./n:TaxTableEntry", namespaces=ns):
        e_type = get_text(entry.find("./n:TaxType", namespaces=ns)) or "IVA"
        e_code = get_text(entry.find("./n:TaxCode", namespaces=ns)) or "NOR"
        e_pct = get_text(entry.find("./n:TaxPercentage", namespaces=ns)) or "0"
        try:
            if (
                e_type == ttype
                and e_code == tcode
                and Decimal(e_pct) == Decimal(tperc_text)
            ):
                ensure_taxtable_entry_order(entry)
                return
        except Exception:
            continue

    new = etree.SubElement(tt, f"{{{nsuri}}}TaxTableEntry")
    el = etree.SubElement(new, f"{{{nsuri}}}TaxType")
    el.text = ttype or "IVA"
    el = etree.SubElement(new, f"{{{nsuri}}}TaxCode")
    el.text = tcode or "NOR"
    el = etree.SubElement(new, f"{{{nsuri}}}Description")
    el.text = "Auto-added for consistency"
    el = etree.SubElement(new, f"{{{nsuri}}}TaxPercentage")
    el.text = fmt_pct(tperc_text)
    ensure_taxtable_entry_order(new)
    logger.log(
        "ADD_TAXTABLEENTRY",
        "Adicionada entrada à TaxTable",
        invoice=inv_no,
        line=str(ln_idx),
        field="TaxTableEntry",
        old_value="",
        new_value=f"{ttype}/{tcode}/{fmt_pct(tperc_text)}",
        note="Entrada criada para alinhar com a Tax usada na linha",
        xpath=ln_xpath,
    )


def fix_xml(
    tree: etree._ElementTree, in_path: Path, logger: ExcelLogger
) -> etree._ElementTree:
    nsuri = detect_ns(tree)
    ns = {"n": nsuri}
    root = tree.getroot()

    vd_issues = normalize_invoice_type_vd_tree(tree)
    for issue in vd_issues:
        logger.log(
            issue.code,
            "InvoiceType normalizado para FR",
            invoice=issue.details.get("invoice", ""),
            field="InvoiceType",
            old_value="VD",
            new_value="FR",
            note=issue.message,
        )

    # 1) Normalizar TaxTable (percentagens e ordem)
    normalize_taxtable_percentages(root, nsuri, logger)

    # 2) Corrigir faturas
    invoices = root.findall(
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice", namespaces=ns
    )
    for inv in invoices:
        inv_no = get_text(inv.find("./n:InvoiceNo", namespaces=ns)) or ""
        doc_totals = inv.find("./n:DocumentTotals", namespaces=ns)
        if doc_totals is None:
            doc_totals = etree.SubElement(inv, f"{{{nsuri}}}DocumentTotals")
            logger.log("ADD_NODE", "Criado DocumentTotals", invoice=inv_no)

        net_total = Decimal("0")
        tax_total = Decimal("0")

        lines = inv.findall("./n:Line", namespaces=ns)
        for idx, ln in enumerate(lines, start=1):
            ln_xpath = etree.ElementTree(root).getpath(ln)

            qty = parse_decimal(get_text(ln.find("./n:Quantity", namespaces=ns)))
            unit = parse_decimal(get_text(ln.find("./n:UnitPrice", namespaces=ns)))
            base = q6(qty * unit)
            base2 = q2(base)

            debit_el = ln.find("./n:DebitAmount", namespaces=ns)
            credit_el = ln.find("./n:CreditAmount", namespaces=ns)

            # Ajuste de montante por linha (preferimos manter o campo já existente)
            if debit_el is not None and credit_el is None:
                old = get_text(debit_el) or ""
                new = fmt2(base2)
                if old != new:
                    logger.log(
                        "FIX_LINE_AMOUNT",
                        "DebitAmount ajustado para q2(qty*unit)",
                        invoice=inv_no,
                        line=str(idx),
                        field="DebitAmount",
                        old_value=old,
                        new_value=new,
                        xpath=ln_xpath,
                    )
                debit_el.text = new
            elif credit_el is not None and debit_el is None:
                old = get_text(credit_el) or ""
                new = fmt2(base2)
                if old != new:
                    logger.log(
                        "FIX_LINE_AMOUNT",
                        "CreditAmount ajustado para q2(qty*unit)",
                        invoice=inv_no,
                        line=str(idx),
                        field="CreditAmount",
                        old_value=old,
                        new_value=new,
                        xpath=ln_xpath,
                    )
                credit_el.text = new
            else:
                # ambos presentes ou ambos ausentes -> ficar só com DebitAmount
                if debit_el is None and credit_el is not None:
                    ln.remove(credit_el)
                    debit_el = etree.SubElement(ln, f"{{{nsuri}}}DebitAmount")
                    logger.log(
                        "REMOVE_NODE",
                        "Removido CreditAmount (duplicado)",
                        invoice=inv_no,
                        line=str(idx),
                        field="CreditAmount",
                        xpath=ln_xpath,
                    )
                    logger.log(
                        "ADD_NODE",
                        "Adicionado DebitAmount na linha",
                        invoice=inv_no,
                        line=str(idx),
                        field="DebitAmount",
                        xpath=ln_xpath,
                    )
                elif debit_el is None and credit_el is None:
                    debit_el = etree.SubElement(ln, f"{{{nsuri}}}DebitAmount")
                    logger.log(
                        "ADD_NODE",
                        "Adicionado DebitAmount na linha",
                        invoice=inv_no,
                        line=str(idx),
                        field="DebitAmount",
                        xpath=ln_xpath,
                    )
                debit_el.text = fmt2(base2)

            # Tax
            tax = ln.find("./n:Tax", namespaces=ns)
            if tax is None:
                tax = etree.SubElement(ln, f"{{{nsuri}}}Tax")
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxType")
                el.text = "IVA"
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxCode")
                el.text = "NOR"
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxCountryRegion")
                el.text = "AO"
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxPercentage")
                el.text = "14"
                logger.log(
                    "ADD_NODE",
                    "Criado bloco Tax na linha",
                    invoice=inv_no,
                    line=str(idx),
                    field="Tax",
                    xpath=ln_xpath,
                )

            ttype = get_text(tax.find("./n:TaxType", namespaces=ns)) or "IVA"
            tcode = get_text(tax.find("./n:TaxCode", namespaces=ns)) or "NOR"
            tperc_el = tax.find("./n:TaxPercentage", namespaces=ns)
            if tperc_el is None:
                tperc_el = etree.SubElement(tax, f"{{{nsuri}}}TaxPercentage")
                tperc_el.text = "14"
                logger.log(
                    "ADD_NODE",
                    "Adicionado TaxPercentage em Tax",
                    invoice=inv_no,
                    line=str(idx),
                    field="TaxPercentage",
                    new_value="14",
                    xpath=ln_xpath,
                )
            else:
                old = get_text(tperc_el) or ""
                new = fmt_pct(old or "0")
                if old != new:
                    logger.log(
                        "FIX_TAX_PERCENT",
                        "Formatado TaxPercentage (inteiro ou 2 casas)",
                        invoice=inv_no,
                        line=str(idx),
                        field="TaxPercentage",
                        old_value=old,
                        new_value=new,
                        xpath=ln_xpath,
                )
                tperc_el.text = new

            ensure_tax_country_region(
                tax,
                nsuri,
                logger,
                owner=inv_no,
                line=idx,
                xpath=ln_xpath,
            )

            tperc = parse_decimal(tperc_el.text)
            vat = q6(base * tperc / HUNDRED)
            net_total += base
            tax_total += vat

            ensure_tax_table_entry(
                root, nsuri, ttype, tcode, str(tperc), logger, inv_no, idx, ln_xpath
            )
            ensure_line_order(ln)

        # Totais (com Settlement e Withholding)
        net2 = q2(net_total)
        tax2 = q2(tax_total)

        settlement_amount = Decimal("0")
        withholding_amount = Decimal("0")

        sett_el = doc_totals.find("./n:Settlement/n:SettlementAmount", namespaces=ns)
        if sett_el is not None and (sett_el.text or "").strip():
            settlement_amount = parse_decimal(sett_el.text)

        for w in doc_totals.findall("./n:WithholdingTax", namespaces=ns):
            wamt_el = w.find("./n:WithholdingTaxAmount", namespaces=ns)
            if wamt_el is not None and (wamt_el.text or "").strip():
                withholding_amount += parse_decimal(wamt_el.text)

        gross2 = q2(net2 - settlement_amount + tax2 - withholding_amount)

        def set_total(tag: str, value: Decimal):
            el = doc_totals.find(f"./n:{tag}", namespaces=ns)
            old = get_text(el) if el is not None else ""
            if el is None:
                el = etree.SubElement(doc_totals, f"{{{nsuri}}}{tag}")
            new = fmt2(value)
            if old != new:
                logger.log(
                    "FIX_TOTAL",
                    f"{tag} ajustado",
                    invoice=inv_no,
                    field=tag,
                    old_value=old or "",
                    new_value=new,
                    note="Identidade completa: Net - Settlement + Tax - Withholding",
                )
            el.text = new

        set_total("TaxPayable", tax2)
        set_total("NetTotal", net2)
        set_total("GrossTotal", gross2)
        ensure_document_totals_order(doc_totals)

    payments = root.findall(
        ".//n:SourceDocuments/n:Payments/n:Payment", namespaces=ns
    )
    for payment in payments:
        pay_ref = get_text(payment.find("./n:PaymentRefNo", namespaces=ns)) or ""
        lines = payment.findall("./n:Line", namespaces=ns)
        for idx, line in enumerate(lines, start=1):
            line_xpath = etree.ElementTree(root).getpath(line)
            tax = line.find("./n:Tax", namespaces=ns)
            if tax is None:
                continue
            ensure_tax_country_region(
                tax,
                nsuri,
                logger,
                owner=pay_ref,
                line=idx,
                xpath=line_xpath,
            )

    work_docs = root.findall(
        ".//n:SourceDocuments/n:WorkingDocuments/n:WorkDocument",
        namespaces=ns,
    )
    for work_doc in work_docs:
        doc_no = get_text(
            work_doc.find("./n:DocumentNumber", namespaces=ns)
        ) or ""
        lines = work_doc.findall("./n:Line", namespaces=ns)
        for idx, line in enumerate(lines, start=1):
            line_xpath = etree.ElementTree(root).getpath(line)
            tax = line.find("./n:Tax", namespaces=ns)
            if tax is None:
                continue
            ensure_tax_country_region(
                tax,
                nsuri,
                logger,
                owner=doc_no,
                line=idx,
                xpath=line_xpath,
            )

    try:
        customer_issues = ensure_invoice_customers_exported_tree(tree)
    except Exception as exc:
        logger.log(
            "AUTOADD_CUSTOMER_FAIL",
            "Falha ao adicionar clientes em falta",
            note=str(exc),
        )
        raise

    for issue in customer_issues:
        extra: Dict[str, Any] | None = None
        if issue.details:
            extra = {
                key: value
                for key, value in issue.details.items()
                if key in {"customer_id", "source"}
            }
        logger.log(
            issue.code,
            "Cliente adicionado ao MasterFiles",
            field="Customer",
            note=issue.message,
            extra=extra,
        )

    return tree


# ------------------------- XSD -------------------------------------------


def default_xsd_path():
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


def validate_xsd(tree: etree._ElementTree, xsd_path: Path):
    try:
        schema_doc = etree.parse(str(xsd_path))
        schema = etree.XMLSchema(schema_doc)
        ok = schema.validate(tree)
        errors = []
        if not ok:
            for e in schema.error_log:
                errors.append(f"line {e.line}: {e.message}")
        return ok, errors
    except Exception as ex:
        return False, [f"XSD validation exception: {ex}"]


def next_version_paths(source: Path, output_dir: Path) -> tuple[Path, Path, str]:
    """Calculate the next available versioned output paths for the XML."""

    version = 2
    while True:
        suffix = f"_v.{version:02d}"
        ok_path = output_dir / f"{source.stem}{suffix}{source.suffix}"
        bad_path = output_dir / f"{source.stem}{suffix}_invalido{source.suffix}"
        if not ok_path.exists() and not bad_path.exists():
            return ok_path, bad_path, suffix
        version += 1


# ------------------------- Main ------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Auto-Fix SAF-T (AO) soft")
    parser.add_argument("xml", help="Ficheiro SAF-T a corrigir.")
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Pasta onde gravar o XML corrigido e o log.",
    )
    args = parser.parse_args(argv)

    in_path = Path(args.xml)
    if not in_path.exists():
        for base in (Path.cwd(), SCRIPT_DIR, PROJECT_ROOT):
            candidate = base / in_path.name
            if candidate.exists():
                in_path = candidate
                break
        else:
            print(f"[ERRO] Ficheiro não encontrado: {in_path}")
            sys.exit(2)

    in_path = in_path.resolve()

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
    else:
        output_dir = in_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[ERRO] Não foi possível criar a pasta de destino '{output_dir}': {exc}")
        sys.exit(2)
    output_dir = output_dir.resolve()

    logger = ExcelLogger(base_name=in_path.stem, output_dir=output_dir)
    logger.log("INFO_START", "Início do Auto-Fix (soft)", extra={"xml": str(in_path)})

    try:
        tree = etree.parse(str(in_path))
    except Exception as ex:
        print(f"[ERRO] Falha no parse do XML: {ex}")
        logger.log("XML_PARSE_ERROR", "Falha no parse do XML", note=str(ex))
        logger.flush()
        sys.exit(2)

    try:
        tree = fix_xml(tree, in_path, logger)
    except Exception as exc:
        print(f"[ERRO] Falha ao aplicar correcções: {exc}")
        logger.log("FIX_ERROR", "Falha ao aplicar correcções", note=str(exc))
        logger.flush()
        sys.exit(2)

    xsd_path = default_xsd_path()
    out_ok, out_bad, version_suffix = next_version_paths(in_path, output_dir)
    version_label = version_suffix.lstrip("_")

    if xsd_path and xsd_path.exists():
        logger.log("XSD_FOUND", "XSD encontrado", new_value=str(xsd_path))
        ok, errs = validate_xsd(tree, xsd_path)
        if ok:
            tree.write(
                str(out_ok), pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
            msg = f"[OK] XML {version_label} (válido por XSD) criado em: {out_ok}"
            print(msg)
            logger.log("INFO_END", "Fim do Auto-Fix (XSD OK)", note=msg)
            logger.flush()
            sys.exit(0)
        else:
            tree.write(
                str(out_bad), pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
            print(
                f"[ALERTA] XML {version_label} criado em: {out_bad}, mas NÃO passou o XSD:"
            )
            for m in errs[:50]:
                print(" -", m)
                logger.log("XSD_ERROR", "Erro de XSD", note=m)
            if len(errs) > 50:
                more = f"(+{len(errs)-50} erros adicionais)"
                print("   " + more)
                logger.log("XSD_ERROR", "Resumo", note=more)
            logger.log("INFO_END", "Fim do Auto-Fix (XSD FAIL)")
            logger.flush()
            sys.exit(2)
    else:
        tree.write(
            str(out_ok), pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        msg = (
            f"[OK] XML {version_label} criado em: {out_ok} "
            "(não foi possível validar XSD)"
        )
        print(msg)
        logger.log("XSD_MISSING", "XSD não encontrado; validação XSD ignorada")
        logger.log("INFO_END", "Fim do Auto-Fix (sem XSD)", note=msg)
        logger.flush()
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover - execução directa
    raise SystemExit(main())
