from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.purchase_reco_service import (
    PurchaseRecoRun,
    export_purchase_reco_excel,
    export_purchase_reco_pdf,
)
from sams_accounting_desktop.ui.components import AppButton, KpiCard
from sams_accounting_desktop.workers.purchase_reco_worker import PurchaseRecoWorker


class PurchaseRecoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")
        self.selected_files: list[str] = []
        self.worker: PurchaseRecoWorker | None = None
        self.current_run: PurchaseRecoRun | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(18)

        layout.addWidget(self.header())
        layout.addLayout(self.summary_cards())
        layout.addWidget(self.controls())
        layout.addWidget(self.results_panel())

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(14)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Purchase Reco")
        title.setObjectName("pageTitle")
        subtitle = QLabel("GST purchase Excel vs Tally Purchase vouchers")
        subtitle.setObjectName("pageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        layout.addLayout(title_stack)
        layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("connectorStatusIdle")
        layout.addWidget(self.status_label)
        return header

    def summary_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        self.gst_card = KpiCard("GST rows", "0", "Loaded from Excel", "#2563eb")
        self.tally_card = KpiCard("Tally purchases", "0", "Fetched from localhost", "#0f766e")
        self.matched_card = KpiCard("Matched", "0", "Exact matches", "#15803d")
        self.review_card = KpiCard("Review", "0", "Probable or mismatch", "#c2410c")
        row.addWidget(self.gst_card)
        row.addWidget(self.tally_card)
        row.addWidget(self.matched_card)
        row.addWidget(self.review_card)
        return row

    def controls(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("recoPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        tally_label = QLabel("Tally URL")
        tally_label.setObjectName("mutedLabel")
        self.tally_url_input = QLineEdit(DEFAULT_TALLY_URL)
        self.tally_url_input.setObjectName("searchBox")
        form.addWidget(tally_label, 0, 0)
        form.addWidget(self.tally_url_input, 1, 0)

        amount_label = QLabel("Amount tolerance")
        amount_label.setObjectName("mutedLabel")
        self.amount_tolerance_input = QLineEdit("1.00")
        self.amount_tolerance_input.setObjectName("searchBox")
        form.addWidget(amount_label, 0, 1)
        form.addWidget(self.amount_tolerance_input, 1, 1)

        tax_label = QLabel("Tax tolerance")
        tax_label.setObjectName("mutedLabel")
        self.tax_tolerance_input = QLineEdit("1.00")
        self.tax_tolerance_input.setObjectName("searchBox")
        form.addWidget(tax_label, 0, 2)
        form.addWidget(self.tax_tolerance_input, 1, 2)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.select_button = AppButton("Select GST Excel", "secondary")
        self.select_button.clicked.connect(self.select_files)
        self.clear_button = AppButton("Clear", "secondary")
        self.clear_button.clicked.connect(self.clear_files)
        self.run_button = AppButton("Run Reco", "primary")
        self.run_button.clicked.connect(self.run_reco)
        self.export_excel_button = AppButton("Export Excel", "secondary")
        self.export_excel_button.clicked.connect(self.export_excel)
        self.export_pdf_button = AppButton("Export PDF", "secondary")
        self.export_pdf_button.clicked.connect(self.export_pdf)
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.run_button)
        button_row.addStretch()
        button_row.addWidget(self.export_excel_button)
        button_row.addWidget(self.export_pdf_button)
        layout.addLayout(button_row)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(80)
        layout.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setObjectName("healthProgress")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.set_export_enabled(False)
        return panel

    def results_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("recoPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Reco Results")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.results_table = QTableWidget(0, 10)
        self.results_table.setObjectName("resultTable")
        self.results_table.setHorizontalHeaderLabels(
            [
                "Status",
                "Supplier",
                "GST invoice",
                "GST date",
                "GST amount",
                "Tally voucher",
                "Tally date",
                "Tally amount",
                "Score",
                "Reasons",
            ]
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(False)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.results_table.setFocusPolicy(Qt.NoFocus)
        for column in range(9):
            self.results_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        self.results_table.setMinimumHeight(360)
        layout.addWidget(self.results_table)
        return panel

    def select_files(self):
        files, _filter = QFileDialog.getOpenFileNames(
            self,
            "Select GST Purchase Excel",
            "",
            "Excel files (*.xlsx *.xlsm)",
        )
        if not files:
            return
        self.selected_files = files
        self.file_list.clear()
        self.file_list.addItems([Path(path).name for path in files])

    def clear_files(self):
        self.selected_files = []
        self.file_list.clear()
        self.current_run = None
        self.results_table.setRowCount(0)
        self.update_summary({})
        self.set_export_enabled(False)
        self.set_status("Ready", "connectorStatusIdle")

    def run_reco(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Purchase Reco", "GST purchase Excel file select karein.")
            return

        try:
            amount_tolerance = self.decimal_input(self.amount_tolerance_input.text())
            tax_tolerance = self.decimal_input(self.tax_tolerance_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Purchase Reco", str(exc))
            return

        self.set_busy(True)
        self.set_status("Working...", "connectorStatusIdle")
        self.results_table.setRowCount(0)
        self.worker = PurchaseRecoWorker(
            self.selected_files,
            tally_url=self.tally_url_input.text().strip() or DEFAULT_TALLY_URL,
            amount_tolerance=amount_tolerance,
            tax_tolerance=tax_tolerance,
        )
        self.worker.progress.connect(self.handle_progress)
        self.worker.finished.connect(self.handle_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def handle_progress(self, current: int, total: int):
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)

    def handle_finished(self, ok: bool, message: str, payload: object):
        self.set_busy(False)
        self.set_status("Completed" if ok else "Failed", "connectorStatusOk" if ok else "connectorStatusError")
        if not ok or not isinstance(payload, PurchaseRecoRun):
            QMessageBox.warning(self, "Purchase Reco", message)
            return

        self.current_run = payload
        self.update_summary(payload.summary)
        self.populate_results(payload.results)
        self.set_export_enabled(True)

    def update_summary(self, summary: dict):
        self.update_card(self.gst_card, str(summary.get("gst_count", 0)))
        self.update_card(self.tally_card, str(summary.get("tally_count", 0)))
        self.update_card(self.matched_card, str(summary.get("matched_count", 0)))
        review_count = (
            summary.get("probable_count", 0)
            + summary.get("mismatch_count", 0)
            + summary.get("missing_count", 0)
        )
        self.update_card(self.review_card, str(review_count))

    def populate_results(self, results: list[dict]):
        self.results_table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            gst = result.get("gst")
            tally = result.get("tally")
            values = [
                result.get("status", ""),
                getattr(gst, "supplier_name", "") if gst is not None else "",
                getattr(gst, "invoice_number", "") if gst is not None else "",
                self.format_date(getattr(gst, "invoice_date", None) if gst is not None else None),
                self.format_amount(getattr(gst, "invoice_value", None) if gst is not None else None),
                getattr(tally, "voucher_number", "") if tally is not None else "",
                self.format_date(getattr(tally, "date", None) if tally is not None else None),
                self.format_amount(getattr(tally, "amount", None) if tally is not None else None),
                str(result.get("score", "")),
                ", ".join(result.get("reasons", []) or []),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    item.setForeground(self.status_color(value))
                self.results_table.setItem(row_index, column, item)

    def export_excel(self):
        if self.current_run is None:
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Purchase Reco Excel",
            "purchase-reco-result.xlsx",
            "Excel files (*.xlsx)",
        )
        if file_path:
            export_purchase_reco_excel(self.current_run, file_path)
            self.set_status("Excel exported", "connectorStatusOk")

    def export_pdf(self):
        if self.current_run is None:
            return
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Export Purchase Reco PDF",
            "purchase-reco-result.pdf",
            "PDF files (*.pdf)",
        )
        if file_path:
            export_purchase_reco_pdf(self.current_run, file_path)
            self.set_status("PDF exported", "connectorStatusOk")

    def set_busy(self, busy: bool):
        self.select_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.set_export_enabled(bool(self.current_run) and not busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1 if self.current_run else 0)

    def set_export_enabled(self, enabled: bool):
        self.export_excel_button.setEnabled(enabled)
        self.export_pdf_button.setEnabled(enabled)

    def set_status(self, text: str, object_name: str):
        self.status_label.setText(text)
        self.status_label.setObjectName(object_name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    @staticmethod
    def update_card(card: KpiCard, value: str):
        label = card.findChild(QLabel, "kpiValue")
        if label is not None:
            label.setText(value)

    @staticmethod
    def decimal_input(value: str) -> Decimal:
        try:
            return Decimal(value.strip() or "0.00")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Tolerance numeric value hona chahiye.") from exc

    @staticmethod
    def format_date(value) -> str:
        return value.isoformat() if value else ""

    @staticmethod
    def format_amount(value) -> str:
        return f"{Decimal(value or 0):.2f}"

    @staticmethod
    def status_color(status: str) -> QColor:
        return {
            "matched": QColor("#067647"),
            "probable": QColor("#b54708"),
            "mismatch": QColor("#b42318"),
            "missing": QColor("#b42318"),
        }.get(status, QColor("#101828"))
