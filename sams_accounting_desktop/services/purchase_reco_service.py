from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Sequence

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_export import (
    export_reconciliation_to_excel,
    export_reconciliation_to_pdf,
)
from sams_accounting_desktop.services.purchase_reconciliation import (
    GstPurchaseRow,
    parse_gst_purchase_excel,
    reconcile_gst_purchases_with_tally,
)
from sams_accounting_desktop.services.tally_purchase_client import TallyPurchaseVoucher, fetch_tally_purchase_vouchers


@dataclass
class PurchaseRecoRun:
    gst_rows: list[GstPurchaseRow]
    tally_vouchers: list[TallyPurchaseVoucher]
    reconciliation: dict

    @property
    def results(self) -> list[dict]:
        return self.reconciliation.get("results", [])

    @property
    def tally_only(self) -> list[TallyPurchaseVoucher]:
        return self.reconciliation.get("tally_only", [])

    @property
    def summary(self) -> dict:
        return self.reconciliation.get("summary", {})


def load_gst_purchase_rows(excel_paths: Sequence[str | Path]) -> list[GstPurchaseRow]:
    if not excel_paths:
        raise ValueError("Kam se kam ek GST purchase Excel file select karein.")

    rows: list[GstPurchaseRow] = []
    errors: list[str] = []
    for path in excel_paths:
        try:
            rows.extend(parse_gst_purchase_excel(path))
        except Exception as exc:
            errors.append(f"{Path(path).name}: {exc}")

    if errors:
        raise ValueError("GST Excel parse error: " + " | ".join(errors))
    if not rows:
        raise ValueError("GST purchase Excel files me valid rows nahi mili.")
    return rows


def run_purchase_reco(
    excel_paths: Sequence[str | Path],
    *,
    tally_url: str = DEFAULT_TALLY_URL,
    from_date: date | None = None,
    to_date: date | None = None,
    amount_tolerance: Decimal = Decimal("1.00"),
    tax_tolerance: Decimal = Decimal("1.00"),
    progress_callback: Callable[[int, int], None] | None = None,
) -> PurchaseRecoRun:
    gst_rows = load_gst_purchase_rows(excel_paths)
    tally_vouchers = fetch_tally_purchase_vouchers(tally_url, from_date=from_date, to_date=to_date)
    reconciliation = reconcile_gst_purchases_with_tally(
        gst_rows,
        tally_vouchers,
        amount_tolerance=amount_tolerance,
        tax_tolerance=tax_tolerance,
        progress_callback=progress_callback,
    )
    return PurchaseRecoRun(
        gst_rows=gst_rows,
        tally_vouchers=tally_vouchers,
        reconciliation=reconciliation,
    )


def export_purchase_reco_excel(run: PurchaseRecoRun, file_path: str | Path | None = None) -> bytes | None:
    return export_reconciliation_to_excel(run.results, str(file_path) if file_path else None)


def export_purchase_reco_pdf(run: PurchaseRecoRun, file_path: str | Path | None = None) -> bytes | None:
    return export_reconciliation_to_pdf(run.results, str(file_path) if file_path else None)
