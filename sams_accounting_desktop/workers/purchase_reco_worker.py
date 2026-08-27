from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QThread, Signal

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_reco_service import run_purchase_reco


class PurchaseRecoWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str, object)

    def __init__(
        self,
        excel_paths: Sequence[str | Path],
        *,
        tally_url: str = DEFAULT_TALLY_URL,
        from_date: date | None = None,
        to_date: date | None = None,
        amount_tolerance: Decimal = Decimal("1.00"),
        tax_tolerance: Decimal = Decimal("1.00"),
    ):
        super().__init__()
        self.excel_paths = [str(path) for path in excel_paths]
        self.tally_url = tally_url
        self.from_date = from_date
        self.to_date = to_date
        self.amount_tolerance = amount_tolerance
        self.tax_tolerance = tax_tolerance

    def run(self):
        try:
            result = run_purchase_reco(
                self.excel_paths,
                tally_url=self.tally_url,
                from_date=self.from_date,
                to_date=self.to_date,
                amount_tolerance=self.amount_tolerance,
                tax_tolerance=self.tax_tolerance,
                progress_callback=self.progress.emit,
            )
            summary = result.summary
            message = (
                f"GST {summary.get('gst_count', 0)} rows, Tally {summary.get('tally_count', 0)} purchases, "
                f"{summary.get('matched_count', 0)} matched."
            )
            self.finished.emit(True, message, result)
        except Exception as exc:
            self.finished.emit(False, str(exc), None)
