from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import random
import tempfile

from openpyxl import Workbook

from sams_accounting_desktop.config import APP_NAME, APP_VERSION
from sams_accounting_desktop.services.bank_pdf_service import parse_bank_pdf_transactions
from sams_accounting_desktop.services.purchase_reconciliation import (
    TallyPurchaseRow,
    parse_gst_purchase_excel,
    reconcile_gst_purchases_with_tally,
)
from sams_accounting_desktop.services.sales_generator import (
    build_fixed_sale_preview_entries,
    build_random_sale_preview_entries,
)
from sams_accounting_desktop.services.tally_client import parse_company_names, parse_import_result
from sams_accounting_desktop.state import is_valid_contact, is_valid_license_key


checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, bool(condition), detail))


check("branding", APP_NAME == "Sams Accounting Desktop", f"{APP_NAME} {APP_VERSION}")
check("email validation", is_valid_contact("qa@example.com"))
check("mobile validation", is_valid_contact("98765 43210"))
check("invalid contact rejected", not is_valid_contact("123"))
check("demo license accepted", is_valid_license_key("SAM-DEMO"))
check("invalid license rejected", not is_valid_license_key("INVALID"))

random_entries = build_random_sale_preview_entries(
    party_name="",
    stock_item_name="Professional Service",
    sale_ledger="Sales",
    voucher_type="Sales",
    cash_bank_ledger="Bank Current A/c",
    cgst_ledger="Output CGST",
    sgst_ledger="Output SGST",
    round_off_ledger="Round Off",
    narration_prefix="QA",
    from_date=date(2026, 8, 1),
    to_date=date(2026, 8, 31),
    number_of_bills=10,
    taxable_amount=Decimal("10000.00"),
    min_amount=Decimal("100.00"),
    max_amount=Decimal("2000.00"),
    cgst_rate=Decimal("9.00"),
    sgst_rate=Decimal("9.00"),
    rng=random.Random(726337),
)
check("random sales count", len(random_entries) == 10, str(len(random_entries)))
check(
    "random sales taxable total",
    sum(Decimal(row["taxable_amount"]) for row in random_entries) == Decimal("10000.00"),
)
check(
    "random sales date range",
    all(date(2026, 8, 1) <= row["voucher_date"] <= date(2026, 8, 31) for row in random_entries),
)

fixed_rows = [
    {"voucher_date": date(2026, 8, 2), "amount": Decimal("1180.00"), "narration": "Invoice A"},
    {"voucher_date": date(2026, 8, 3), "amount": Decimal("2360.00"), "narration": "Invoice B"},
]
fixed_entries = build_fixed_sale_preview_entries(
    fixed_rows,
    party_name="ABC Traders",
    stock_item_name="Professional Service",
    sale_ledger="Sales",
    voucher_type="Sales",
    cash_bank_ledger="",
    cgst_ledger="Output CGST",
    sgst_ledger="Output SGST",
    round_off_ledger="Round Off",
    narration_prefix="QA",
    cgst_rate=Decimal("9.00"),
    sgst_rate=Decimal("9.00"),
)
check("fixed sales count", len(fixed_entries) == 2, str(len(fixed_entries)))
check(
    "fixed sales gross total",
    sum(Decimal(row["amount"]) for row in fixed_entries) == Decimal("3540.00"),
)

demo_pdf = Path("demo-video/demo-bank-statement-windows.pdf")
bank_rows = parse_bank_pdf_transactions(str(demo_pdf))
check("bank PDF sample parse", len(bank_rows) == 4, f"{len(bank_rows)} transactions")
check(
    "bank PDF debit/credit detected",
    any(row.debit > 0 for row in bank_rows) and any(row.credit > 0 for row in bank_rows),
)

temp_dir = Path(tempfile.mkdtemp(prefix="sams-accounting-qa-"))
gst_file = temp_dir / "gst-purchase-qa.xlsx"
workbook = Workbook()
sheet = workbook.active
sheet.append([
    "GSTIN of supplier",
    "Trade/Legal name",
    "Invoice number",
    "Invoice date",
    "Invoice value",
    "Taxable value",
    "Central tax",
    "State/UT tax",
])
sheet.append([
    "27ABCDE1234F1Z5",
    "ABC Traders",
    "INV-1001",
    date(2026, 8, 5),
    1180,
    1000,
    90,
    90,
])
workbook.save(gst_file)
gst_rows = parse_gst_purchase_excel(gst_file)
check("GST Excel sample parse", len(gst_rows) == 1, str(gst_file))

tally_row = TallyPurchaseRow(
    date=date(2026, 8, 5),
    voucher_number="PV-1001",
    voucher_type_name="Purchase",
    party_ledger_name="ABC Traders",
    narration="QA purchase",
    amount=Decimal("1180.00"),
    supplier_invoice_number="INV-1001",
    supplier_gstin="27ABCDE1234F1Z5",
    taxable_value=Decimal("1000.00"),
    cgst=Decimal("90.00"),
    sgst=Decimal("90.00"),
)
reco = reconcile_gst_purchases_with_tally(gst_rows, [tally_row])
check("purchase reconciliation exact match", reco[0]["status"] == "matched", reco[0]["status"])

company_xml = "<ENVELOPE><COMPANY><NAME>QA Company</NAME></COMPANY></ENVELOPE>"
check("Tally company XML parse", parse_company_names(company_xml) == ["QA Company"])
import_xml = "<ENVELOPE><BODY><DATA><IMPORTRESULT><CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS></IMPORTRESULT></DATA></BODY></ENVELOPE>"
import_result = parse_import_result(import_xml)
check("Tally import response parse", import_result.success and import_result.created == 1)

failed = [item for item in checks if not item[1]]
for name, passed, detail in checks:
    print(f"{'PASS' if passed else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))
print(f"SUMMARY | passed={len(checks) - len(failed)} failed={len(failed)} total={len(checks)}")
print(f"TEMP_OUTPUT | {temp_dir}")
raise SystemExit(1 if failed else 0)
