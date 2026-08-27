from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from xml.sax.saxutils import escape

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - depends on desktop install
    fitz = None

from sams_accounting_desktop.services.tally_client import (
    TallyImportResult,
    build_voucher_import_request,
    format_tally_amount,
    format_tally_date,
    normalize_tally_text,
    parse_import_result,
    post_tally_xml,
)


DATE_PATTERN = re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
AMOUNT_PATTERN = re.compile(r"(?<![A-Za-z])(?:Rs\.?\s*)?([+-]?\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|[+-]?\d+(?:\.\d{1,2})?)\s*(CR|DR)?\b", re.IGNORECASE)
CREDIT_HINTS = (" credit ", " deposit ", " receipt ", " received ", " cr ")
DEBIT_HINTS = (" debit ", " withdrawal ", " payment ", " paid ", " dr ", " upi/", " imps/", " neft/")


@dataclass(frozen=True)
class BankPdfTransaction:
    voucher_date: date
    description: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    balance: Decimal | None = None
    raw_text: str = ""

    @property
    def amount(self) -> Decimal:
        return self.debit if self.debit > Decimal("0.00") else self.credit

    @property
    def voucher_type(self) -> str:
        return "Payment" if self.debit > Decimal("0.00") else "Receipt"


def extract_bank_pdf_text(file_path: str) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF installed nahi hai. requirements install karke phir PDF parse karein.")

    chunks: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            chunks.append(page.get_text("text"))
    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError("PDF se selectable text nahi mila. Scanned/image PDF ke liye Image PDF OCR workflow use karein.")
    return text


def parse_bank_pdf_transactions(file_path: str) -> list[BankPdfTransaction]:
    return parse_bank_statement_text(extract_bank_pdf_text(file_path))


def parse_bank_statement_text(text: str) -> list[BankPdfTransaction]:
    transactions: list[BankPdfTransaction] = []
    pending_line = ""

    for raw_line in text.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue
        if DATE_PATTERN.search(line):
            if pending_line:
                transaction = parse_transaction_line(pending_line)
                if transaction is not None:
                    transactions.append(transaction)
            pending_line = line
        elif pending_line:
            pending_line = f"{pending_line} {line}"

    if pending_line:
        transaction = parse_transaction_line(pending_line)
        if transaction is not None:
            transactions.append(transaction)

    if not transactions:
        raise ValueError("PDF text mila, lekin transaction rows detect nahi hui. Table me dates/amounts selectable hone chahiye.")
    return transactions


def parse_transaction_line(line: str) -> BankPdfTransaction | None:
    date_match = DATE_PATTERN.search(line)
    if not date_match:
        return None
    voucher_date = parse_bank_date(date_match.group(1))
    if voucher_date is None:
        return None

    amount_matches = []
    for match in AMOUNT_PATTERN.finditer(line):
        if not match.group(1):
            continue
        if date_match.start() <= match.start() and match.end() <= date_match.end():
            continue
        if looks_like_date_fragment(match.group(1), line, match.start()):
            continue
        amount_matches.append(match)
    amounts = [parse_amount(match.group(1)) for match in amount_matches]
    amounts = [amount for amount in amounts if amount is not None]
    if not amounts:
        return None

    balance = amounts[-1] if len(amounts) >= 2 else None
    transaction_amount = amounts[-2] if len(amounts) >= 2 else amounts[-1]
    if transaction_amount <= Decimal("0.00"):
        return None

    direction = detect_direction(line, amount_matches)
    debit = transaction_amount if direction == "debit" else Decimal("0.00")
    credit = transaction_amount if direction == "credit" else Decimal("0.00")

    first_amount_start = amount_matches[0].start() if amount_matches else len(line)
    description = line[date_match.end():first_amount_start].strip(" -|")
    description = description or line

    return BankPdfTransaction(
        voucher_date=voucher_date,
        description=description[:220],
        debit=debit.quantize(Decimal("0.01")),
        credit=credit.quantize(Decimal("0.01")),
        balance=balance.quantize(Decimal("0.01")) if balance is not None else None,
        raw_text=line,
    )


def detect_direction(line: str, amount_matches: list[re.Match]) -> str:
    padded = f" {line.casefold()} "
    if any(hint in padded for hint in CREDIT_HINTS):
        return "credit"
    if any(hint in padded for hint in DEBIT_HINTS):
        return "debit"
    for match in amount_matches:
        marker = (match.group(2) or "").casefold()
        if marker == "cr":
            return "credit"
        if marker == "dr":
            return "debit"
    return "debit"


def parse_bank_date(value: str) -> date | None:
    cleaned = value.replace("/", "-")
    for pattern in ("%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    return None


def parse_amount(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", "").strip()).copy_abs().quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def looks_like_date_fragment(value: str, line: str, start: int) -> bool:
    window = line[max(0, start - 2): start + len(value) + 8]
    return bool(DATE_PATTERN.search(window))


def normalize_space(value: str) -> str:
    return " ".join((value or "").replace("\u00a0", " ").split())


def create_tally_bank_voucher(
    tally_url: str,
    *,
    voucher_type: str,
    voucher_date: date,
    bank_ledger: str,
    opposite_ledger: str,
    amount: Decimal,
    narration: str = "",
    voucher_number: str = "",
) -> TallyImportResult:
    xml = build_bank_voucher_import_request(
        voucher_type=voucher_type,
        voucher_date=voucher_date,
        bank_ledger=bank_ledger,
        opposite_ledger=opposite_ledger,
        amount=amount,
        narration=narration,
        voucher_number=voucher_number,
    )
    return parse_import_result(post_tally_xml(tally_url, xml))


def build_bank_voucher_import_request(
    *,
    voucher_type: str,
    voucher_date: date,
    bank_ledger: str,
    opposite_ledger: str,
    amount: Decimal,
    narration: str = "",
    voucher_number: str = "",
) -> str:
    voucher_type_name = normalize_tally_text(voucher_type) or "Payment"
    bank_ledger_name = normalize_tally_text(bank_ledger)
    opposite_ledger_name = normalize_tally_text(opposite_ledger)
    if not bank_ledger_name:
        raise ValueError("Bank ledger required hai.")
    if not opposite_ledger_name:
        raise ValueError("Opposite ledger required hai.")
    tally_amount = format_tally_amount(Decimal(amount))
    payment_mode = voucher_type_name.casefold() == "payment"
    bank_amount = f"-{tally_amount}" if payment_mode else tally_amount
    opposite_amount = tally_amount if payment_mode else f"-{tally_amount}"
    bank_positive = "Yes" if payment_mode else "No"
    opposite_positive = "No" if payment_mode else "Yes"
    voucher_number_xml = (
        f"<VOUCHERNUMBER>{escape(voucher_number.strip())}</VOUCHERNUMBER>"
        if voucher_number.strip()
        else ""
    )

    voucher_xml = (
        f"<VOUCHER VCHTYPE=\"{escape(voucher_type_name)}\" ACTION=\"Create\" OBJVIEW=\"Accounting Voucher View\">"
        f"<DATE>{format_tally_date(voucher_date)}</DATE>"
        f"<NARRATION>{escape(narration.strip())}</NARRATION>"
        f"<VOUCHERTYPENAME>{escape(voucher_type_name)}</VOUCHERTYPENAME>"
        f"{voucher_number_xml}"
        "<PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>"
        f"<EFFECTIVEDATE>{format_tally_date(voucher_date)}</EFFECTIVEDATE>"
        "<ALLLEDGERENTRIES.LIST>"
        f"<LEDGERNAME>{escape(opposite_ledger_name)}</LEDGERNAME>"
        f"<ISDEEMEDPOSITIVE>{opposite_positive}</ISDEEMEDPOSITIVE>"
        f"<AMOUNT>{opposite_amount}</AMOUNT>"
        "</ALLLEDGERENTRIES.LIST>"
        "<ALLLEDGERENTRIES.LIST>"
        f"<LEDGERNAME>{escape(bank_ledger_name)}</LEDGERNAME>"
        f"<ISDEEMEDPOSITIVE>{bank_positive}</ISDEEMEDPOSITIVE>"
        f"<AMOUNT>{bank_amount}</AMOUNT>"
        "</ALLLEDGERENTRIES.LIST>"
        "</VOUCHER>"
    )
    return build_voucher_import_request(voucher_xml=voucher_xml)
