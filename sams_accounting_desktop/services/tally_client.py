from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from sams_accounting_desktop.config import TIMEOUT_SECONDS
from sams_accounting_desktop.services.sales_generator import (
    extract_gst_rate_from_stock_item_name,
    split_gst_rate,
)


COMPANY_PROBE_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>Company</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="Company">
            <TYPE>Company</TYPE>
            <FETCH>Name</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

VOUCHER_TYPES_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>List of Voucher Types</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="List of Voucher Types" ISMODIFY="No">
            <TYPE>VoucherType</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

STOCK_ITEMS_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>List of Stock Items</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="List of Stock Items" ISMODIFY="No">
            <TYPE>StockItem</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
            <FETCH>Name,GSTDetails.*</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

NUMERIC_CHARACTER_REFERENCE_PATTERN = re.compile(r"&#(?:x[0-9a-fA-F]+|\d+);")
RAW_INVALID_XML_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
DEFAULT_PARTY_STATE = "Madhya Pradesh"
DEFAULT_PARTY_COUNTRY = "India"


@dataclass
class TallyImportResult:
    success: bool
    message: str
    created: int = 0
    altered: int = 0
    ignored: int = 0
    errors: int = 0
    raw_response: str = ""


@dataclass(frozen=True)
class TallyMasterRecord:
    name: str
    parent: str = ""


@dataclass(frozen=True)
class TallyStockItemMaster:
    name: str
    cgst_rate: Decimal = Decimal("0.00")
    sgst_rate: Decimal = Decimal("0.00")
    igst_rate: Decimal = Decimal("0.00")

    @property
    def total_gst_rate(self) -> Decimal:
        if self.igst_rate > Decimal("0.00"):
            return self.igst_rate
        return (self.cgst_rate + self.sgst_rate).quantize(Decimal("0.01"))

LEDGERS_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>List of Ledgers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="List of Ledgers" ISMODIFY="No">
            <TYPE>Ledger</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
            <NATIVEMETHOD>Parent</NATIVEMETHOD>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

GROUPS_XML = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>COLLECTION</TYPE>
    <ID>List of Groups</ID>
  </HEADER>
  <BODY>
    <DESC>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="List of Groups" ISMODIFY="No">
            <TYPE>Group</TYPE>
            <NATIVEMETHOD>Name</NATIVEMETHOD>
            <NATIVEMETHOD>Parent</NATIVEMETHOD>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].upper()


def is_valid_xml_character(codepoint: int) -> bool:
    return (
        codepoint in {0x09, 0x0A, 0x0D}
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def remove_invalid_character_reference(match: re.Match[str]) -> str:
    reference = match.group(0)
    value = reference[2:-1]
    try:
        codepoint = int(value[1:], 16) if value.lower().startswith("x") else int(value)
    except ValueError:
        return ""
    return reference if is_valid_xml_character(codepoint) else ""


def sanitize_tally_xml(raw_response: str) -> str:
    without_bad_references = NUMERIC_CHARACTER_REFERENCE_PATTERN.sub(
        remove_invalid_character_reference,
        raw_response,
    )
    return RAW_INVALID_XML_CHARACTER_PATTERN.sub("", without_bad_references)


def parse_tally_xml(raw_response: str) -> ET.Element:
    return ET.fromstring(sanitize_tally_xml(raw_response))


def post_tally_xml(tally_url: str, xml: str, timeout: int | None = None) -> str:
    request = urllib.request.Request(
        tally_url.rstrip("/"),
        data=xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "User-Agent": "SamsAccountingDesktop/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout or TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_company_names(raw_response: str) -> list[str]:
    try:
        root = parse_tally_xml(raw_response)
    except ET.ParseError:
        return []

    companies: list[str] = []
    seen: set[str] = set()

    for element in root.iter():
        if tag_name(element) != "COMPANY":
            continue
        name = clean_text(element.attrib.get("NAME") or element.text)
        if not name:
            for child in element:
                if tag_name(child) == "NAME":
                    name = clean_text(child.text)
                    break
        if name.isdigit():
            continue
        if name and name not in seen:
            seen.add(name)
            companies.append(name)

    if companies:
        return companies

    for element in root.iter():
        if tag_name(element) not in {"NAME", "CMPNAME"}:
            continue
        name = clean_text(element.attrib.get("NAME") or element.text)
        if name.isdigit():
            continue
        if name and name not in seen:
            seen.add(name)
            companies.append(name)
    return companies


def parse_ledgers(raw_response: str, query: str = "") -> list[str]:
    root = parse_tally_xml(raw_response)
    ledgers: list[str] = []
    seen: set[str] = set()

    for element in root.iter():
        if tag_name(element) != "LEDGER":
            continue
        name = clean_text(element.attrib.get("NAME"))
        if not name:
            for child in element:
                if tag_name(child) == "NAME":
                    name = clean_text(child.text)
                    break
        if name and name not in seen:
            seen.add(name)
            ledgers.append(name)

    if not ledgers:
        for element in root.iter():
            if tag_name(element) in {"DSPDISPNAME", "DSPACCNAME", "LEDGERNAME", "NAME"}:
                name = clean_text(element.text)
                if name and name not in seen:
                    seen.add(name)
                    ledgers.append(name)

    needle = query.strip().lower()
    if needle:
        ledgers = [ledger for ledger in ledgers if needle in ledger.lower()]
    return ledgers


def parse_tally_master_records(raw_response: str, object_tag: str) -> list[TallyMasterRecord]:
    root = parse_tally_xml(raw_response)
    object_tag = object_tag.upper()
    records: list[TallyMasterRecord] = []
    seen: set[str] = set()

    for element in root.iter():
        if tag_name(element) != object_tag:
            continue

        name = clean_text(element.attrib.get("NAME"))
        parent = clean_text(element.attrib.get("PARENT"))
        for child in element:
            child_tag = tag_name(child)
            if child_tag == "NAME" and not name:
                name = clean_text(child.text)
            elif child_tag == "PARENT":
                parent = clean_text(child.text)

        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            records.append(TallyMasterRecord(name=name, parent=parent))

    return sorted(records, key=lambda record: record.name.casefold())


def parse_tally_stock_item_masters(
    raw_response: str,
    *,
    as_of_date: date | None = None,
) -> list[TallyStockItemMaster]:
    root = parse_tally_xml(raw_response)
    as_of_date = as_of_date or date.today()
    records: list[TallyStockItemMaster] = []

    for item in root.iter():
        if tag_name(item) != "STOCKITEM":
            continue
        name = clean_text(item.attrib.get("NAME"))
        if not name:
            name = next(
                (clean_text(child.text) for child in item if tag_name(child) == "NAME"),
                "",
            )
        if not name:
            continue

        rate_snapshots: list[tuple[date, int, dict[str, Decimal]]] = []
        for position, detail in enumerate(
            element for element in item.iter() if tag_name(element) == "GSTDETAILS.LIST"
        ):
            raw_date = next(
                (clean_text(child.text) for child in detail if tag_name(child) == "APPLICABLEFROM"),
                "",
            )
            try:
                applicable_from = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
            except (TypeError, ValueError):
                applicable_from = date.min
            if applicable_from > as_of_date:
                continue

            rates: dict[str, Decimal] = {}
            for rate_list in detail.iter():
                if tag_name(rate_list) != "RATEDETAILS.LIST":
                    continue
                duty_head = next(
                    (clean_text(child.text) for child in rate_list if tag_name(child) == "GSTRATEDUTYHEAD"),
                    "",
                )
                raw_rate = next(
                    (clean_text(child.text) for child in rate_list if tag_name(child) == "GSTRATE"),
                    "0",
                )
                try:
                    rate = Decimal(raw_rate.replace(",", "")).quantize(Decimal("0.01"))
                except Exception:
                    rate = Decimal("0.00")
                duty_key = re.sub(r"[^a-z]", "", duty_head.casefold())
                if duty_key == "cgst":
                    rates["cgst"] = rate
                elif duty_key in {"sgst", "sgstutgst", "statetax"}:
                    rates["sgst"] = rate
                elif duty_key in {"igst", "integratedtax"}:
                    rates["igst"] = rate

            rate_snapshots.append((applicable_from, position, rates))

        current_rates = max(rate_snapshots, default=(date.min, 0, {}), key=lambda row: (row[0], row[1]))[2]
        records.append(
            TallyStockItemMaster(
                name=name,
                cgst_rate=current_rates.get("cgst", Decimal("0.00")),
                sgst_rate=current_rates.get("sgst", Decimal("0.00")),
                igst_rate=current_rates.get("igst", Decimal("0.00")),
            )
        )

    return sorted(records, key=lambda record: record.name.casefold())


def filter_tally_ledger_names_by_groups(
    ledger_masters: list[TallyMasterRecord],
    group_masters: list[TallyMasterRecord],
    allowed_groups: tuple[str, ...],
) -> list[str]:
    allowed = {group.casefold() for group in allowed_groups}
    group_parents = {group.name.casefold(): group.parent.casefold() for group in group_masters}
    matches: list[str] = []

    for ledger in ledger_masters:
        current_group = ledger.parent.casefold()
        visited: set[str] = set()
        while current_group and current_group not in visited:
            if current_group in allowed:
                matches.append(ledger.name)
                break
            visited.add(current_group)
            current_group = group_parents.get(current_group, "")

    return sorted(set(matches), key=str.casefold)


def test_tally_connection(tally_url: str) -> tuple[bool, str, list[str]]:
    try:
        response = post_tally_xml(tally_url, COMPANY_PROBE_XML)
    except urllib.error.URLError as exc:
        return False, f"Tally not reachable at {tally_url}: {exc.reason}", []
    except TimeoutError:
        return False, f"Tally timed out at {tally_url}", []

    if "<LINEERROR>" in response.upper():
        return False, "Tally responded, but returned an XML line error.", []

    companies = parse_company_names(response)
    if companies:
        return True, f"Tally connected. Active company: {companies[0]}", companies
    if "ENVELOPE" in response.upper() or "COMPANY" in response.upper():
        return True, f"Tally connected at {tally_url}", []
    return True, f"Tally responded at {tally_url}", []


def fetch_tally_ledgers(tally_url: str, query: str = "") -> list[str]:
    response = post_tally_xml(tally_url, LEDGERS_XML)
    if "<LINEERROR>" in response.upper():
        raise RuntimeError("Tally returned an XML line error while fetching ledgers.")
    return parse_ledgers(response, query=query)


def fetch_tally_ledger_masters(tally_url: str, query: str = "") -> list[TallyMasterRecord]:
    response = post_tally_xml(tally_url, LEDGERS_XML)
    line_error = extract_line_error(response)
    if line_error:
        raise RuntimeError(line_error)
    records = parse_tally_master_records(response, "LEDGER")
    needle = query.strip().casefold()
    if needle:
        records = [record for record in records if needle in record.name.casefold()]
    return records


def fetch_tally_groups(tally_url: str) -> list[TallyMasterRecord]:
    response = post_tally_xml(tally_url, GROUPS_XML)
    line_error = extract_line_error(response)
    if line_error:
        raise RuntimeError(line_error)
    return parse_tally_master_records(response, "GROUP")


def fetch_tally_voucher_types(tally_url: str, query: str = "") -> list[str]:
    response = post_tally_xml(tally_url, VOUCHER_TYPES_XML)
    line_error = extract_line_error(response)
    if line_error:
        raise RuntimeError(line_error)
    items = parse_named_collection(response, "VOUCHERTYPE", ("NAME", "VOUCHERTYPENAME"))
    needle = query.strip().lower()
    if needle:
        items = [item for item in items if needle in item.lower()]
    return items


def fetch_tally_stock_items(tally_url: str, query: str = "") -> list[str]:
    return [record.name for record in fetch_tally_stock_item_masters(tally_url, query=query)]


def fetch_tally_stock_item_masters(tally_url: str, query: str = "") -> list[TallyStockItemMaster]:
    response = post_tally_xml(tally_url, STOCK_ITEMS_XML)
    line_error = extract_line_error(response)
    if line_error:
        raise RuntimeError(line_error)
    items = parse_tally_stock_item_masters(response)
    needle = query.strip().casefold()
    if needle:
        items = [item for item in items if needle in item.name.casefold()]
    return items


def parse_named_collection(raw_response: str, object_tag: str, fallback_tags: tuple[str, ...]) -> list[str]:
    try:
        root = parse_tally_xml(raw_response)
    except ET.ParseError:
        return []

    items: list[str] = []
    seen: set[str] = set()
    object_tag = object_tag.upper()
    fallback_tag_names = {name.upper() for name in fallback_tags}

    for element in root.iter():
        if tag_name(element) != object_tag:
            continue
        name = clean_text(element.attrib.get("NAME"))
        if not name:
            for child in element:
                if tag_name(child) in fallback_tag_names:
                    name = clean_text(child.text)
                    break
        if name and name not in seen:
            seen.add(name)
            items.append(name)

    if items:
        return sorted(items)

    for element in root.iter():
        if tag_name(element) not in fallback_tag_names:
            continue
        name = clean_text(element.text)
        if name and name not in seen:
            seen.add(name)
            items.append(name)
    return sorted(items)


def create_tally_item_invoice_voucher(
    tally_url: str,
    *,
    voucher_type: str,
    voucher_date: date,
    party_ledger: str,
    sales_ledger: str,
    stock_item_name: str,
    taxable_amount: Decimal,
    total_amount: Decimal,
    cgst_ledger: str = "",
    sgst_ledger: str = "",
    cgst_rate: Decimal | None = None,
    sgst_rate: Decimal | None = None,
    round_off_ledger: str = "",
    round_off_amount: Decimal = Decimal("0.00"),
    narration: str = "",
    voucher_number: str = "",
) -> TallyImportResult:
    party_ledger_name = normalize_tally_text(party_ledger)
    party_state = DEFAULT_PARTY_STATE
    party_country = DEFAULT_PARTY_COUNTRY if ledger_name_is_cash_like(party_ledger_name) else ""

    if party_ledger_name and not ledger_name_is_cash_like(party_ledger_name):
        try:
            party_state = fetch_tally_ledger_state(tally_url, party_ledger_name) or DEFAULT_PARTY_STATE
        except Exception:
            party_state = DEFAULT_PARTY_STATE

    xml = build_item_invoice_voucher_import_request(
        voucher_type=voucher_type,
        voucher_date=voucher_date,
        party_ledger=party_ledger,
        sales_ledger=sales_ledger,
        stock_item_name=stock_item_name,
        taxable_amount=taxable_amount,
        total_amount=total_amount,
        party_state=party_state,
        party_country=party_country,
        cgst_ledger=cgst_ledger,
        sgst_ledger=sgst_ledger,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        round_off_ledger=round_off_ledger,
        round_off_amount=round_off_amount,
        narration=narration,
        voucher_number=voucher_number,
    )
    return parse_import_result(post_tally_xml(tally_url, xml))


def fetch_tally_ledger_state(tally_url: str, ledger_name: str) -> str:
    escaped_name = escape(ledger_name)
    xml = (
        "<ENVELOPE>"
        "<HEADER>"
        "<VERSION>1</VERSION>"
        "<TALLYREQUEST>EXPORT</TALLYREQUEST>"
        "<TYPE>OBJECT</TYPE>"
        "<SUBTYPE>Ledger</SUBTYPE>"
        f"<ID TYPE=\"Name\">{escaped_name}</ID>"
        "</HEADER>"
        "<BODY>"
        "<DESC>"
        "<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>"
        "<FETCHLIST>"
        "<FETCH>StateName</FETCH>"
        "<FETCH>LedStateName</FETCH>"
        "<FETCH>MailingState</FETCH>"
        "</FETCHLIST>"
        "</DESC>"
        "</BODY>"
        "</ENVELOPE>"
    )
    response = post_tally_xml(tally_url, xml)
    line_error = extract_line_error(response)
    if line_error:
        raise RuntimeError(line_error)
    try:
        root = parse_tally_xml(response)
    except ET.ParseError:
        return ""
    for wanted in ("LEDSTATENAME", "STATENAME", "STATE", "MAILINGSTATE"):
        for element in root.iter():
            if tag_name(element) == wanted:
                value = clean_text(element.text)
                if value:
                    return value
    return ""


def build_item_invoice_voucher_import_request(
    *,
    voucher_type: str,
    voucher_date: date,
    party_ledger: str,
    sales_ledger: str,
    stock_item_name: str,
    taxable_amount: Decimal,
    total_amount: Decimal,
    party_state: str = "",
    party_country: str = "",
    cgst_ledger: str = "",
    sgst_ledger: str = "",
    cgst_rate: Decimal | None = None,
    sgst_rate: Decimal | None = None,
    round_off_ledger: str = "",
    round_off_amount: Decimal = Decimal("0.00"),
    narration: str = "",
    voucher_number: str = "",
) -> str:
    voucher_type = normalize_tally_text(voucher_type)
    if not voucher_type:
        raise ValueError("Voucher type is required.")

    party_ledger_name = party_ledger.strip()
    sales_ledger_name = sales_ledger.strip()
    stock_item = stock_item_name.strip()
    cgst_ledger_name = cgst_ledger.strip()
    sgst_ledger_name = sgst_ledger.strip()
    round_off_ledger_name = round_off_ledger.strip()
    if cgst_rate is None or sgst_rate is None:
        total_gst_rate = extract_gst_rate_from_stock_item_name(stock_item)
        cgst_rate, sgst_rate = split_gst_rate(
            total_gst_rate,
            has_cgst=bool(cgst_ledger_name),
            has_sgst=bool(sgst_ledger_name),
        )
    else:
        cgst_rate = Decimal(cgst_rate).quantize(Decimal("0.01")) if cgst_ledger_name else Decimal("0.00")
        sgst_rate = Decimal(sgst_rate).quantize(Decimal("0.01")) if sgst_ledger_name else Decimal("0.00")

    taxable_text = format_tally_amount(taxable_amount)
    total_text = format_tally_amount(total_amount)
    party_state_name = normalize_tally_text(party_state)
    party_state_xml = ""
    if party_state_name:
        escaped_state = escape(party_state_name)
        party_state_xml = (
            f"<PLACEOFSUPPLY>{escaped_state}</PLACEOFSUPPLY>"
            f"<STATENAME>{escaped_state}</STATENAME>"
        )
    party_country_name = normalize_tally_text(party_country)
    party_country_xml = ""
    if party_country_name:
        party_country_xml = f"<COUNTRYNAME>{escape(party_country_name)}</COUNTRYNAME>"
    voucher_number_xml = (
        f"<VOUCHERNUMBER>{escape(voucher_number.strip())}</VOUCHERNUMBER>"
        if voucher_number.strip()
        else ""
    )

    bill_allocations_xml = ""
    if voucher_number.strip():
        bill_allocations_xml = (
            "<BILLALLOCATIONS.LIST>"
            f"<NAME>{escape(voucher_number.strip())}</NAME>"
            "<BILLTYPE>New Ref</BILLTYPE>"
            f"<AMOUNT>-{total_text}</AMOUNT>"
            "</BILLALLOCATIONS.LIST>"
        )

    gst_ledger_entries = ""
    if cgst_ledger_name:
        cgst_amount = (taxable_amount * (cgst_rate / Decimal("100.00"))).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        gst_ledger_entries += (
            "<LEDGERENTRIES.LIST>"
            "<BASICRATEOFINVOICETAX.LIST TYPE=\"Number\">"
            f"<BASICRATEOFINVOICETAX>{format_tax_rate(cgst_rate)}</BASICRATEOFINVOICETAX>"
            "</BASICRATEOFINVOICETAX.LIST>"
            "<ROUNDTYPE></ROUNDTYPE>"
            f"<LEDGERNAME>{escape(cgst_ledger_name)}</LEDGERNAME>"
            "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{format_tally_amount(cgst_amount)}</AMOUNT>"
            "</LEDGERENTRIES.LIST>"
        )
    if sgst_ledger_name:
        sgst_amount = (taxable_amount * (sgst_rate / Decimal("100.00"))).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        gst_ledger_entries += (
            "<LEDGERENTRIES.LIST>"
            "<BASICRATEOFINVOICETAX.LIST TYPE=\"Number\">"
            f"<BASICRATEOFINVOICETAX>{format_tax_rate(sgst_rate)}</BASICRATEOFINVOICETAX>"
            "</BASICRATEOFINVOICETAX.LIST>"
            "<ROUNDTYPE></ROUNDTYPE>"
            f"<LEDGERNAME>{escape(sgst_ledger_name)}</LEDGERNAME>"
            "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{format_tally_amount(sgst_amount)}</AMOUNT>"
            "</LEDGERENTRIES.LIST>"
        )
    if round_off_ledger_name and round_off_amount != Decimal("0.00"):
        round_off_text = format_tally_amount(abs(round_off_amount))
        round_off_positive = round_off_amount >= Decimal("0.00")
        gst_ledger_entries += (
            "<LEDGERENTRIES.LIST>"
            "<ROUNDTYPE>Normal Rounding</ROUNDTYPE>"
            f"<LEDGERNAME>{escape(round_off_ledger_name)}</LEDGERNAME>"
            f"<ISDEEMEDPOSITIVE>{'No' if round_off_positive else 'Yes'}</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{'' if round_off_positive else '-'}{round_off_text}</AMOUNT>"
            "</LEDGERENTRIES.LIST>"
        )

    voucher_xml = (
        f"<VOUCHER VCHTYPE=\"{escape(voucher_type)}\" ACTION=\"Create\" OBJVIEW=\"Invoice Voucher View\">"
        f"<DATE>{format_tally_date(voucher_date)}</DATE>"
        f"<NARRATION>{escape(narration.strip())}</NARRATION>"
        f"<VOUCHERTYPENAME>{escape(voucher_type)}</VOUCHERTYPENAME>"
        f"{voucher_number_xml}"
        "<PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>"
        "<ISINVOICE>Yes</ISINVOICE>"
        "<OBJVIEW>Invoice Voucher View</OBJVIEW>"
        f"<PARTYLEDGERNAME>{escape(party_ledger_name)}</PARTYLEDGERNAME>"
        f"{party_state_xml}"
        f"{party_country_xml}"
        f"<EFFECTIVEDATE>{format_tally_date(voucher_date)}</EFFECTIVEDATE>"
        "<LEDGERENTRIES.LIST>"
        f"<LEDGERNAME>{escape(party_ledger_name)}</LEDGERNAME>"
        "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>"
        "<ISPARTYLEDGER>Yes</ISPARTYLEDGER>"
        "<ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>"
        f"<AMOUNT>-{total_text}</AMOUNT>"
        f"{bill_allocations_xml}"
        "</LEDGERENTRIES.LIST>"
        f"{gst_ledger_entries}"
        "<ALLINVENTORYENTRIES.LIST>"
        f"<STOCKITEMNAME>{escape(stock_item)}</STOCKITEMNAME>"
        "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>"
        f"<AMOUNT>{taxable_text}</AMOUNT>"
        "<ACCOUNTINGALLOCATIONS.LIST>"
        f"<LEDGERNAME>{escape(sales_ledger_name)}</LEDGERNAME>"
        "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>"
        f"<AMOUNT>{taxable_text}</AMOUNT>"
        "</ACCOUNTINGALLOCATIONS.LIST>"
        "</ALLINVENTORYENTRIES.LIST>"
        "</VOUCHER>"
    )
    return build_voucher_import_request(voucher_xml=voucher_xml)


def build_voucher_import_request(*, voucher_xml: str) -> str:
    return (
        "<ENVELOPE>"
        "<HEADER>"
        "<VERSION>1</VERSION>"
        "<TALLYREQUEST>Import</TALLYREQUEST>"
        "<TYPE>Data</TYPE>"
        "<ID>Vouchers</ID>"
        "</HEADER>"
        "<BODY><DESC>"
        "</DESC><DATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">"
        f"{voucher_xml}"
        "</TALLYMESSAGE></DATA></BODY>"
        "</ENVELOPE>"
    )


def extract_line_error(raw_response: str) -> str:
    try:
        root = parse_tally_xml(raw_response)
    except ET.ParseError:
        return ""

    errors: list[str] = []
    for element in root.iter():
        if tag_name(element) in {"LINEERROR", "ERROR"}:
            text = clean_text(element.text)
            if text:
                errors.append(text)
    return " | ".join(errors)


def parse_import_result(raw_response: str) -> TallyImportResult:
    line_error = extract_line_error(raw_response)
    if line_error:
        return TallyImportResult(
            success=False,
            message=f"Tally Prime rejected the voucher: {line_error}",
            errors=1,
            raw_response=raw_response,
        )

    try:
        root = parse_tally_xml(raw_response)
    except ET.ParseError:
        return TallyImportResult(
            success=False,
            message="Tally Prime returned an unreadable XML response.",
            errors=1,
            raw_response=raw_response,
        )

    created = read_int_from_root(root, "CREATED")
    altered = read_int_from_root(root, "ALTERED")
    ignored = read_int_from_root(root, "IGNORED")
    errors = read_int_from_root(root, "ERRORS")
    last_vch_id = read_first_text_from_root(root, "LASTVCHID")

    success = (created + altered) > 0 and errors == 0
    if success:
        message = f"Voucher synced to Tally Prime. Created: {created}, Altered: {altered}, Ignored: {ignored}."
    else:
        message = (
            "Tally Prime processed the import request, but no voucher was created. "
            f"Created: {created}, Altered: {altered}, Ignored: {ignored}, Errors: {errors}."
        )
        if last_vch_id:
            message += f" Last voucher id reported by Tally: {last_vch_id}."
        if created == 0 and altered == 0 and ignored == 0 and errors == 0:
            message += (
                " Common causes: voucher type is not invoice-compatible, stock item unit/rate format mismatch, "
                "or any master name does not exactly match Tally."
            )

    return TallyImportResult(
        success=success,
        message=message,
        created=created,
        altered=altered,
        ignored=ignored,
        errors=errors,
        raw_response=raw_response,
    )


def read_int_from_root(root: ET.Element, wanted_tag: str) -> int:
    wanted = wanted_tag.upper()
    for element in root.iter():
        if tag_name(element) != wanted:
            continue
        try:
            return int(clean_text(element.text) or "0")
        except ValueError:
            return 0
    return 0


def read_first_text_from_root(root: ET.Element, wanted_tag: str) -> str:
    wanted = wanted_tag.upper()
    for element in root.iter():
        if tag_name(element) == wanted:
            return clean_text(element.text)
    return ""


def normalize_tally_text(value: str | None) -> str:
    return clean_text(value)


def ledger_name_is_cash_like(ledger_name: str) -> bool:
    normalized_name = normalize_tally_text(ledger_name).lower()
    return normalized_name in {"cash", "cash in hand", "cash-in-hand"}


def format_tax_rate(rate: Decimal) -> str:
    rate_text = format(rate.quantize(Decimal("0.01")), "f")
    if "." in rate_text:
        rate_text = rate_text.rstrip("0").rstrip(".")
    return rate_text or "0"


def format_tally_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def format_tally_amount(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{normalized:.2f}"
