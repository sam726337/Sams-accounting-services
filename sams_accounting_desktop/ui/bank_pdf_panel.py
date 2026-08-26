from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sams_accounting_desktop.config import DEFAULT_TALLY_URL
from sams_accounting_desktop.services.bank_pdf_service import (
    BankPdfTransaction,
    create_tally_bank_voucher,
    parse_bank_pdf_transactions,
)
from sams_accounting_desktop.services.tally_client import (
    fetch_tally_groups,
    fetch_tally_ledger_masters,
    fetch_tally_voucher_types,
    filter_tally_ledger_names_by_groups,
)
from sams_accounting_desktop.ui.components import AppButton, StatusChip


def money_text(value: Decimal | str | None) -> str:
    try:
        return f"{Decimal(value or '0').quantize(Decimal('0.01')):.2f}"
    except (InvalidOperation, ValueError):
        return "0.00"


class BankPdfPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")
        self.pdf_file_path = ""
        self.transactions: list[BankPdfTransaction] = []
        self.ledger_names: list[str] = []
        self.bank_ledgers: list[str] = []
        self.voucher_types: list[str] = ["Payment", "Receipt"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(16)
        layout.addWidget(self.header())
        layout.addWidget(self.form_panel())
        layout.addWidget(self.preview_panel(), 1)

    def header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topbar")
        header.setMinimumHeight(76)
        row = QHBoxLayout(header)
        row.setContentsMargins(22, 12, 22, 12)

        copy = QVBoxLayout()
        title = QLabel("Bank PDF Parser")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Selectable bank statement PDF ko Payment/Receipt voucher preview me convert karein.")
        subtitle.setObjectName("pageSubtitle")
        copy.addWidget(title)
        copy.addWidget(subtitle)
        row.addLayout(copy)
        row.addStretch()

        self.status_chip = StatusChip("Ready", "info")
        row.addWidget(self.status_chip)
        return header

    def form_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("formPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        self.tally_url_input = QLineEdit(DEFAULT_TALLY_URL)
        self.tally_url_input.setObjectName("searchBox")
        self.bank_ledger_input = self.combo("Select bank ledger")
        self.file_label = QLabel("No PDF selected")
        self.file_label.setObjectName("smallText")
        self.file_label.setWordWrap(True)

        self.add_labeled(layout, 0, 0, "Tally URL", self.tally_url_input)
        self.add_labeled(layout, 0, 1, "Bank Ledger", self.bank_ledger_input)
        layout.addWidget(self.file_label, 1, 0, 1, 2)

        button_row = QHBoxLayout()
        choose_button = AppButton("Choose PDF", "secondary", "PF", "#7c3aed")
        choose_button.clicked.connect(self.choose_pdf)
        parse_button = AppButton("Parse PDF", "primary", "BP", "#0f766e")
        parse_button.clicked.connect(self.parse_pdf)
        load_button = AppButton("Load Tally Masters", "secondary", "TA", "#115e59")
        load_button.clicked.connect(self.load_tally_masters)
        self.import_button = AppButton("Import to Tally", "primary", "IM", "#15803d")
        self.import_button.clicked.connect(self.import_to_tally)
        self.import_button.setEnabled(False)

        for button in (choose_button, parse_button, load_button, self.import_button):
            button_row.addWidget(button)
        button_row.addStretch()
        layout.addLayout(button_row, 2, 0, 1, 2)
        return panel

    def preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Transaction Preview")
        title.setObjectName("sectionTitle")
        self.total_label = QLabel("0 entries | debit 0.00 | credit 0.00")
        self.total_label.setObjectName("smallText")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(self.total_label)
        layout.addLayout(head)

        self.table = QTableWidget(0, 8)
        self.table.setObjectName("activityTable")
        self.table.setHorizontalHeaderLabels(
            ["Date", "Voucher", "Bank Ledger", "Opposite Ledger", "Debit", "Credit", "Narration", "Balance"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        return panel

    def add_labeled(self, layout: QGridLayout, row: int, column: int, label: str, widget: QWidget):
        box = QVBoxLayout()
        title = QLabel(label)
        title.setObjectName("formLabel")
        box.addWidget(title)
        box.addWidget(widget)
        layout.addLayout(box, row, column)

    def combo(self, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("masterCombo")
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(18)
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(placeholder)
            line_edit.setClearButtonEnabled(True)
        return combo

    def choose_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Bank Statement PDF", "", "PDF files (*.pdf)")
        if not file_path:
            return
        self.pdf_file_path = file_path
        self.file_label.setText(Path(file_path).name)
        self.set_status("info", "PDF selected. Parse PDF click karein.")

    def parse_pdf(self):
        if not self.pdf_file_path:
            self.set_status("warning", "Pehle bank PDF select karein.")
            return
        try:
            self.transactions = parse_bank_pdf_transactions(self.pdf_file_path)
        except Exception as exc:
            self.set_status("error", str(exc))
            QMessageBox.warning(self, "Bank PDF Parse", str(exc))
            return
        self.populate_preview()
        self.import_button.setEnabled(bool(self.transactions))
        self.set_status("ok", f"{len(self.transactions)} transactions parsed. Review karke import karein.")

    def populate_preview(self):
        self.table.setRowCount(len(self.transactions))
        debit_total = Decimal("0.00")
        credit_total = Decimal("0.00")
        for row, transaction in enumerate(self.transactions):
            debit_total += transaction.debit
            credit_total += transaction.credit
            values = [
                transaction.voucher_date.isoformat(),
                transaction.voucher_type,
                self.bank_ledger_input.currentText().strip(),
                "",
                money_text(transaction.debit),
                money_text(transaction.credit),
                transaction.description,
                money_text(transaction.balance),
            ]
            for column, value in enumerate(values):
                if column in {1, 2, 3}:
                    combo = self.combo("Select ledger" if column != 1 else "Voucher type")
                    source = self.voucher_types if column == 1 else (self.bank_ledgers if column == 2 else self.ledger_names)
                    combo.addItems(source)
                    if value and combo.findText(value, Qt.MatchFlag.MatchFixedString) < 0:
                        combo.insertItem(0, value)
                    combo.setCurrentText(value)
                    self.table.setCellWidget(row, column, combo)
                    continue
                item = QTableWidgetItem(value)
                if column in {4, 5, 7}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if column == 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
        self.total_label.setText(f"{len(self.transactions)} entries | debit {money_text(debit_total)} | credit {money_text(credit_total)}")

    def load_tally_masters(self):
        tally_url = self.tally_url_input.text().strip() or DEFAULT_TALLY_URL
        self.set_status("info", "Tally masters loading...")
        try:
            ledger_masters = fetch_tally_ledger_masters(tally_url)
            group_masters = fetch_tally_groups(tally_url)
            voucher_types = fetch_tally_voucher_types(tally_url)
        except Exception as exc:
            self.set_status("warning", f"Tally masters load nahi hue: {exc}")
            return

        self.ledger_names = [record.name for record in ledger_masters]
        self.bank_ledgers = filter_tally_ledger_names_by_groups(
            ledger_masters,
            group_masters,
            ("Cash-in-Hand", "Bank Accounts", "Bank OD A/c", "Bank OCC A/c"),
        )
        self.voucher_types = sorted(
            {item for item in voucher_types if item.casefold() in {"payment", "receipt"}},
            key=str.casefold,
        ) or ["Payment", "Receipt"]
        self.populate_combo(self.bank_ledger_input, self.bank_ledgers)
        if self.transactions:
            self.populate_preview()
        self.set_status("ok", f"Loaded {len(self.ledger_names)} ledgers, bank ledgers {len(self.bank_ledgers)}.")

    def populate_combo(self, combo: QComboBox, values: list[str]):
        current = combo.currentText().strip()
        combo.clear()
        combo.addItems(sorted({value for value in values if value}, key=str.casefold))
        if current:
            combo.setCurrentText(current)

    def import_to_tally(self):
        entries = self.collect_entries()
        if not entries:
            self.set_status("warning", "Import ke liye valid rows nahi hain.")
            return

        tally_url = self.tally_url_input.text().strip() or DEFAULT_TALLY_URL
        created = 0
        failed = 0
        first_error = ""
        self.set_status("info", "Importing bank vouchers to Tally...")
        for entry in entries:
            try:
                result = create_tally_bank_voucher(tally_url, **entry)
                if result.success:
                    created += 1
                else:
                    failed += 1
                    first_error = first_error or result.message
            except Exception as exc:
                failed += 1
                first_error = first_error or str(exc)

        if failed:
            self.set_status("warning", f"Imported {created}, failed {failed}. {first_error}")
            QMessageBox.warning(self, "Bank PDF Import", f"Imported {created}, failed {failed}.\n{first_error}")
        else:
            self.set_status("ok", f"{created} bank vouchers imported to Tally.")

    def collect_entries(self) -> list[dict]:
        entries: list[dict] = []
        for row in range(self.table.rowCount()):
            voucher_type = self.combo_text(row, 1) or "Payment"
            bank_ledger = self.combo_text(row, 2)
            opposite_ledger = self.combo_text(row, 3)
            voucher_date = date.fromisoformat(self.item_text(row, 0))
            debit = Decimal(self.item_text(row, 4).replace(",", "") or "0").quantize(Decimal("0.01"))
            credit = Decimal(self.item_text(row, 5).replace(",", "") or "0").quantize(Decimal("0.01"))
            amount = debit if debit > Decimal("0.00") else credit
            if amount <= Decimal("0.00") or not bank_ledger or not opposite_ledger:
                continue
            entries.append(
                {
                    "voucher_type": voucher_type,
                    "voucher_date": voucher_date,
                    "bank_ledger": bank_ledger,
                    "opposite_ledger": opposite_ledger,
                    "amount": amount,
                    "narration": self.item_text(row, 6),
                    "voucher_number": f"BP-{row + 1}",
                }
            )
        return entries

    def combo_text(self, row: int, column: int) -> str:
        widget = self.table.cellWidget(row, column)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""

    def item_text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def set_status(self, status: str, message: str):
        self.status_chip.set_status(status, message[:80])
        self.status_chip.setToolTip(message)
