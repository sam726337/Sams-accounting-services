import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from sams_accounting_desktop.config import TIMEOUT_SECONDS


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


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].upper()


def post_tally_xml(tally_url: str, xml: str) -> str:
    request = urllib.request.Request(
        tally_url.rstrip("/"),
        data=xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "User-Agent": "SamsAccountingDesktop/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_company_names(raw_response: str) -> list[str]:
    try:
        root = ET.fromstring(raw_response)
    except ET.ParseError:
        return []

    companies: list[str] = []
    seen: set[str] = set()
    for element in root.iter():
        if tag_name(element) not in {"COMPANY", "NAME", "CMPNAME"}:
            continue
        name = clean_text(element.attrib.get("NAME") or element.text)
        if name and name not in seen:
            seen.add(name)
            companies.append(name)
    return companies


def parse_ledgers(raw_response: str, query: str = "") -> list[str]:
    root = ET.fromstring(raw_response)
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
