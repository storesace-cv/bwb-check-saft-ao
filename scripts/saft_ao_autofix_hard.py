#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SAF-T (AO) Auto-Fix com validação XSD e ordem de elementos
----------------------------------------------------------

- Corrige valores conforme regras estritas (q6 nos cálculos, q2 na exportação).
- Garante ordem mínima exigida no XSD para os blocos tocados:
  * Line: ... Quantity, UnitPrice, (DebitAmount|CreditAmount), Tax, ...
  * DocumentTotals: NetTotal, TaxPayable, GrossTotal
  * TaxTableEntry: TaxType, TaxCode, Description, TaxPercentage
- Valida contra SAFTAO1.01_01.xsd se estiver na CWD ou na pasta do script.
- Só grava *_corrigido.xml se o XSD passar; senão grava *_corrigido_invalido.xml.

Uso:
    python saft_ao_autofix.py MEU_FICHEIRO.xml
"""

import sys
from decimal import Decimal, ROUND_HALF_UP, getcontext, InvalidOperation
from pathlib import Path
from lxml import etree

# Precisão alta para cálculo
getcontext().prec = 28

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

NS_DEFAULT = "urn:OECD:StandardAuditFile-Tax:AO_1.01_01"
AMT2 = Decimal("0.01")
AMT6 = Decimal("0.000001")
HUNDRED = Decimal("100")


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


def parse_decimal(text: str, default: Decimal = Decimal("0")) -> Decimal:
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


# --- Helpers de ordenação (apenas para os blocos que tocamos) -----------------


def reorder_children(parent, nsuri: str, order_local_names: list):
    """Reordena os filhos de 'parent' seguindo a lista de nomes locais dada."""
    # bucket por nome local
    by_name = {name: [] for name in order_local_names}
    others = []
    for child in list(parent):
        # extrai localname
        if child.tag.startswith("{") and "}" in child.tag:
            local = child.tag.split("}", 1)[1]
        else:
            local = child.tag
        if local in by_name:
            by_name[local].append(child)
        else:
            others.append(child)

    # limpa e reanexa
    for child in list(parent):
        parent.remove(child)

    for name in order_local_names:
        for node in by_name[name]:
            parent.append(node)
    # restantes vão no fim (preservamos o que não controlamos)
    for node in others:
        parent.append(node)


def ensure_line_order(line_el, nsuri: str):
    """
    Mantém uma ordem mínima segura para os campos que tocamos.
    Nota: não impomos a ordem total do XSD, apenas garantimos que os elementos
    que mexemos estão no sítio certo relativamente entre si.
    """
    order = [
        "LineNumber",
        "ProductCode",
        "ProductDescription",
        "Quantity",
        "UnitOfMeasure",
        "UnitPrice",
        "TaxPointDate",
        "References",
        "Description",
        # montantes (um ou outro) antes do Tax
        "DebitAmount",
        "CreditAmount",
        "Tax",
        # o resto fica depois
        "TaxExemptionReason",
        "SettlementAmount",
        "CustomsInformation",
    ]
    reorder_children(line_el, nsuri, order)


def ensure_document_totals_order(doc_totals_el, nsuri: str):
    order = [
        # há mais elementos em DocumentTotals, mas garantimos os que mexemos
        "NetTotal",
        "TaxPayable",
        "GrossTotal",
    ]
    reorder_children(doc_totals_el, nsuri, order)


def ensure_taxtable_entry_order(entry_el, nsuri: str):
    order = [
        "TaxType",
        "TaxCode",
        "Description",
        "TaxPercentage",
    ]
    reorder_children(entry_el, nsuri, order)


# --- Construção / fixes -------------------------------------------------------


def ensure_tax_table_entry(root, nsuri: str, ttype: str, tcode: str, tperc_text: str):
    """
    Garante TaxTableEntry(type, code, percentage). Se não existir, cria um mínimo:
    TaxType, TaxCode, Description, TaxPercentage (com ordem certa).
    """
    ns = {"n": nsuri}
    mf = root.find(".//n:MasterFiles", namespaces=ns)
    if mf is None:
        mf = etree.SubElement(root, f"{{{nsuri}}}MasterFiles")
    tt = mf.find("./n:TaxTable", namespaces=ns)
    if tt is None:
        tt = etree.SubElement(mf, f"{{{nsuri}}}TaxTable")

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
                # garantir também a ordem correta
                ensure_taxtable_entry_order(entry, nsuri)
                return
        except Exception:
            continue

    # criar nova entrada mínima
    new = etree.SubElement(tt, f"{{{nsuri}}}TaxTableEntry")
    el = etree.SubElement(new, f"{{{nsuri}}}TaxType")
    el.text = ttype or "IVA"
    el = etree.SubElement(new, f"{{{nsuri}}}TaxCode")
    el.text = tcode or "NOR"
    el = etree.SubElement(new, f"{{{nsuri}}}Description")
    el.text = "Auto-added for consistency"
    el = etree.SubElement(new, f"{{{nsuri}}}TaxPercentage")
    el.text = fmt_pct(tperc_text)
    ensure_taxtable_entry_order(new, nsuri)


def fix_xml(tree: etree._ElementTree, path: Path) -> etree._ElementTree:
    nsuri = detect_ns(tree)
    ns = {"n": nsuri}
    root = tree.getroot()

    # Corrigir faturas
    invoices = root.findall(
        ".//n:SourceDocuments/n:SalesInvoices/n:Invoice", namespaces=ns
    )
    for inv in invoices:
        doc_totals = inv.find("./n:DocumentTotals", namespaces=ns)
        if doc_totals is None:
            doc_totals = etree.SubElement(inv, f"{{{nsuri}}}DocumentTotals")

        net_total = Decimal("0")
        tax_total = Decimal("0")

        lines = inv.findall("./n:Line", namespaces=ns)
        for ln in lines:
            qty = parse_decimal(get_text(ln.find("./n:Quantity", namespaces=ns)))
            unit = parse_decimal(get_text(ln.find("./n:UnitPrice", namespaces=ns)))
            base = q6(qty * unit)
            base2 = q2(base)

            # Debit/Credit coerente (exclusivo)
            debit_el = ln.find("./n:DebitAmount", namespaces=ns)
            credit_el = ln.find("./n:CreditAmount", namespaces=ns)
            if debit_el is not None and credit_el is None:
                debit_el.text = fmt2(base2)
            elif credit_el is not None and debit_el is None:
                credit_el.text = fmt2(base2)
            else:
                # ambos presentes ou ambos ausentes -> ficar só com DebitAmount
                if debit_el is None and credit_el is None:
                    debit_el = etree.SubElement(ln, f"{{{nsuri}}}DebitAmount")
                elif debit_el is not None and credit_el is not None:
                    ln.remove(credit_el)
                debit_el.text = fmt2(base2)

            # Tax
            tax = ln.find("./n:Tax", namespaces=ns)
            if tax is None:
                tax = etree.SubElement(ln, f"{{{nsuri}}}Tax")
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxType")
                el.text = "IVA"
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxCode")
                el.text = "NOR"
                el = etree.SubElement(tax, f"{{{nsuri}}}TaxPercentage")
                el.text = "14"

            ttype = get_text(tax.find("./n:TaxType", namespaces=ns)) or "IVA"
            tcode = get_text(tax.find("./n:TaxCode", namespaces=ns)) or "NOR"
            tperc_el = tax.find("./n:TaxPercentage", namespaces=ns)
            if tperc_el is None:
                tperc_el = etree.SubElement(tax, f"{{{nsuri}}}TaxPercentage")
                tperc_el.text = "14"
            else:
                tperc_el.text = fmt_pct(get_text(tperc_el) or "0")
            tperc = parse_decimal(tperc_el.text)

            vat = q6(base * tperc / HUNDRED)
            net_total += base
            tax_total += vat

            # Garantir TaxTable
            ensure_tax_table_entry(root, nsuri, ttype, tcode, str(tperc))

            # Ordem mínima na linha (elementos que tocamos)
            ensure_line_order(ln, nsuri)

        # Totais corrigidos e ordem
        net2 = q2(net_total)
        tax2 = q2(tax_total)
        gross2 = q2(net_total + tax_total)

        def set_total(tag: str, value: Decimal):
            el = doc_totals.find(f"./n:{tag}", namespaces=ns)
            if el is None:
                el = etree.SubElement(doc_totals, f"{{{nsuri}}}{tag}")
            el.text = fmt2(value)

        set_total("NetTotal", net2)
        set_total("TaxPayable", tax2)
        set_total("GrossTotal", gross2)
        ensure_document_totals_order(doc_totals, nsuri)

    return tree


# --- XSD -----------------------------------------------------------


def default_xsd_path() -> Path | None:
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


def validate_xsd(tree: etree._ElementTree, xsd_path: Path) -> tuple[bool, list]:
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


# --- Main ----------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Uso: python saft_ao_autofix.py MEU_FICHEIRO.xml")
        sys.exit(2)

    in_path = Path(sys.argv[1])
    if not in_path.exists():
        for base in (Path.cwd(), SCRIPT_DIR, PROJECT_ROOT):
            candidate = base / in_path.name
            if candidate.exists():
                in_path = candidate
                break
        else:
            print(f"[ERRO] Ficheiro não encontrado: {in_path}")
            sys.exit(2)

    try:
        tree = etree.parse(str(in_path))
    except Exception as ex:
        print(f"[ERRO] Falha no parse do XML: {ex}")
        sys.exit(2)

    tree = fix_xml(tree, in_path)

    # validar XSD se disponível
    xsd_path = default_xsd_path()
    out_ok = in_path.with_name(f"{in_path.stem}_corrigido{in_path.suffix}")
    out_bad = in_path.with_name(f"{in_path.stem}_corrigido_invalido{in_path.suffix}")

    if xsd_path and xsd_path.exists():
        ok, errs = validate_xsd(tree, xsd_path)
        if ok:
            tree.write(
                str(out_ok), pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
            print(f"[OK] XML corrigido (válido por XSD) criado em: {out_ok}")
            sys.exit(0)
        else:
            tree.write(
                str(out_bad), pretty_print=True, xml_declaration=True, encoding="UTF-8"
            )
            print(f"[ALERTA] XML corrigido criado em: {out_bad}, mas NÃO passou o XSD:")
            for m in errs[:20]:
                print(" -", m)
            if len(errs) > 20:
                print(f"   (+{len(errs)-20} erros adicionais)")
            sys.exit(2)
    else:
        # Sem XSD, gravamos mesmo assim (não garantimos)
        tree.write(
            str(out_ok), pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        print(f"[OK] XML corrigido criado em: {out_ok} (não foi possível validar XSD)")
        sys.exit(0)


if __name__ == "__main__":
    main()
