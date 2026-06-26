from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
import xml.etree.ElementTree as ET

from sams_accounting_desktop.config import PURCHASE_RECO_TIMEOUT_SECONDS
from sams_accounting_desktop.services.purchase_reconciliation import (
    normalize_gstin,
    parse_date_value,
    parse_decimal_value,
)
from sams_accounting_desktop.services.tally_client import clean_text, parse_tally_xml, post_tally_xml, tag_name


@dataclass
class TallyPurchaseVoucher:
    date: date | None
    voucher_number: str
    voucher_type_name: str
    party_ledger_name: str
    narration: str
    amount: Decimal
    guid: str = ""
    remote_id: str = ""
    voucher_key: str = ""
    master_id: str = ""
    alter_id: str = ""
    supplier_invoice_number: str = ""
    bill_references: list[str] | None = None
    supplier_gstin: str = ""
    taxable_value: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    cess: Decimal = Decimal("0.00")
    raw_xml: str = ""


def build_purchase_vouchers_xml(from_date: date | None = None, to_date: date | None = None) -> str:
    static_variables = ["<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"]
    if from_date is not None:
        static_variables.append(f"<SVFROMDATE TYPE=\"Date\">{from_date:%Y%m%d}</SVFROMDATE>")
    if to_date is not None:
        static_variables.append(f"<SVTODATE TYPE=\"Date\">{to_date:%Y%m%d}</SVTODATE>")

    return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>Sams Purchase Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        {''.join(static_variables)}
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="Sams Purchase Vouchers" ISMODIFY="No">
            <TYPE>Voucher</TYPE>
            <FETCH>
              Date,VoucherNumber,VoucherTypeName,PartyLedgerName,PartyName,Narration,Amount,Reference,Guid,
              RemoteID,MasterID,AlterID,VoucherKey,PartyGSTIN,BasicBuyersSalesTaxNo,
              AllLedgerEntries.*,LedgerEntries.*,BillAllocations.*,AccountingAllocations.*,AllInventoryEntries.*
            </FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""


def fetch_tally_purchase_vouchers(
    tally_url: str,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[TallyPurchaseVoucher]:
    response = post_tally_xml(
        tally_url,
        build_purchase_vouchers_xml(from_date=from_date, to_date=to_date),
        timeout=PURCHASE_RECO_TIMEOUT_SECONDS,
    )
    if "<LINEERROR>" in response.upper():
        raise RuntimeError("Tally returned an XML line error while fetching purchase vouchers.")
    return parse_tally_purchase_vouchers(response)


def parse_tally_purchase_vouchers(raw_response: str) -> list[TallyPurchaseVoucher]:
    root = parse_tally_xml(raw_response)
    vouchers: list[TallyPurchaseVoucher] = []
    for voucher in root.iter():
        if tag_name(voucher) != "VOUCHER" or not is_purchase_voucher(voucher):
            continue
        vouchers.append(parse_tally_purchase_voucher(voucher))
    return vouchers


def parse_tally_purchase_voucher(voucher: ET.Element) -> TallyPurchaseVoucher:
    party_ledger_name = first_text(voucher, "PARTYLEDGERNAME", "PARTYNAME", "BASICBASEPARTYNAME")
    ledger_entries = ledger_entry_elements(voucher)
    amount = voucher_total_amount(voucher, ledger_entries, party_ledger_name)
    taxes = tax_amounts(ledger_entries)
    supplier_invoice_number = first_valid_reference(
        first_text(voucher, "REFERENCE", "BASICREFERENCE", "PARTYINVNO", "BILLREF"),
        *bill_references(voucher),
    )
    bill_refs = unique_nonempty([supplier_invoice_number, *bill_references(voucher)])

    return TallyPurchaseVoucher(
        date=parse_date_value(first_text(voucher, "DATE")),
        voucher_number=first_text(voucher, "VOUCHERNUMBER"),
        supplier_invoice_number=supplier_invoice_number,
        voucher_type_name=first_text(voucher, "VOUCHERTYPENAME") or clean_text(voucher.attrib.get("VCHTYPE")),
        party_ledger_name=party_ledger_name,
        narration=first_text(voucher, "NARRATION"),
        amount=amount,
        guid=first_text(voucher, "GUID"),
        remote_id=clean_text(voucher.attrib.get("REMOTEID")) or first_text(voucher, "REMOTEID"),
        voucher_key=clean_text(voucher.attrib.get("VCHKEY")) or first_text(voucher, "VOUCHERKEY"),
        master_id=first_text(voucher, "MASTERID"),
        alter_id=first_text(voucher, "ALTERID"),
        bill_references=bill_refs,
        supplier_gstin=normalize_gstin(first_text(voucher, "PARTYGSTIN", "BASICBUYERSSALESTAXNO")),
        taxable_value=taxable_amount(ledger_entries, party_ledger_name),
        igst=taxes["igst"],
        cgst=taxes["cgst"],
        sgst=taxes["sgst"],
        cess=taxes["cess"],
        raw_xml=ET.tostring(voucher, encoding="unicode"),
    )


def is_purchase_voucher(voucher: ET.Element) -> bool:
    voucher_type = " ".join(
        [
            clean_text(voucher.attrib.get("VCHTYPE")),
            first_text(voucher, "VOUCHERTYPENAME"),
        ]
    ).upper()
    return "PURCHASE" in voucher_type and "ORDER" not in voucher_type


def first_text(element: ET.Element, *names: str) -> str:
    wanted = {name.upper() for name in names}
    for child in element:
        if tag_name(child) in wanted:
            value = clean_text(child.text)
            if value:
                return value
    return ""


def descendant_texts(element: ET.Element, name: str) -> list[str]:
    wanted = name.upper()
    return [clean_text(node.text) for node in element.iter() if tag_name(node) == wanted and clean_text(node.text)]


def ledger_entry_elements(voucher: ET.Element) -> list[ET.Element]:
    all_entries = [node for node in voucher if tag_name(node) == "ALLLEDGERENTRIES.LIST"]
    if all_entries:
        return all_entries
    return [node for node in voucher if tag_name(node) == "LEDGERENTRIES.LIST"]


def bill_references(voucher: ET.Element) -> list[str]:
    references: list[str] = []
    for node in voucher.iter():
        if tag_name(node) != "BILLALLOCATIONS.LIST":
            continue
        references.extend(descendant_texts(node, "NAME"))
    return [reference for reference in references if is_useful_reference(reference)]


def voucher_total_amount(voucher: ET.Element, entries: list[ET.Element], party_ledger_name: str) -> Decimal:
    party_amounts = [
        abs(entry_amount(entry))
        for entry in entries
        if is_party_entry(entry, party_ledger_name)
    ]
    if party_amounts:
        return max(party_amounts)
    direct_amount = abs(parse_decimal_value(first_text(voucher, "AMOUNT")))
    if direct_amount:
        return direct_amount
    return sum(abs(entry_amount(entry)) for entry in entries if is_party_entry(entry, party_ledger_name))


def taxable_amount(entries: list[ET.Element], party_ledger_name: str) -> Decimal:
    total = Decimal("0.00")
    for entry in entries:
        ledger_name = first_text(entry, "LEDGERNAME")
        if is_party_entry(entry, party_ledger_name) or is_tax_ledger(ledger_name) or is_rounding_ledger(ledger_name):
            continue
        total += abs(entry_amount(entry))
    return total.quantize(Decimal("0.01"))


def tax_amounts(entries: list[ET.Element]) -> dict[str, Decimal]:
    totals = {
        "igst": Decimal("0.00"),
        "cgst": Decimal("0.00"),
        "sgst": Decimal("0.00"),
        "cess": Decimal("0.00"),
    }
    for entry in entries:
        ledger_name = first_text(entry, "LEDGERNAME")
        tax_type = tax_ledger_type(ledger_name)
        if tax_type:
            totals[tax_type] += abs(entry_amount(entry))
    return {key: value.quantize(Decimal("0.01")) for key, value in totals.items()}


def is_party_entry(entry: ET.Element, party_ledger_name: str) -> bool:
    is_party = first_text(entry, "ISPARTYLEDGER").upper() == "YES"
    ledger_name = first_text(entry, "LEDGERNAME")
    return is_party or bool(party_ledger_name and normalize_ledger_name(ledger_name) == normalize_ledger_name(party_ledger_name))


def entry_amount(entry: ET.Element) -> Decimal:
    return parse_decimal_value(first_text(entry, "AMOUNT"))


def tax_ledger_type(ledger_name: str) -> str:
    normalized = normalize_ledger_name(ledger_name)
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    if "igst" in compact or "integratedtax" in compact:
        return "igst"
    if "cgst" in compact or "centraltax" in compact:
        return "cgst"
    if "sgst" in compact or "utgst" in compact or "statetax" in compact or "uttax" in compact:
        return "sgst"
    if "cess" in compact:
        return "cess"
    return ""


def is_tax_ledger(ledger_name: str) -> bool:
    return bool(tax_ledger_type(ledger_name))


def is_rounding_ledger(ledger_name: str) -> bool:
    normalized = normalize_ledger_name(ledger_name)
    return "round" in normalized


def normalize_ledger_name(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def first_valid_reference(*references: str) -> str:
    for reference in references:
        if is_useful_reference(reference):
            return reference
    return ""


def is_useful_reference(reference: str) -> bool:
    value = clean_text(reference)
    return bool(value and value.lower() not in {"not applicable", "primary batch"})


def unique_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output
