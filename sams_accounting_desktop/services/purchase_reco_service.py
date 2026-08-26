from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
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
    meaningful_tokens,
    normalize_gstin,
    parse_gst_purchase_excel,
    reconcile_gst_purchases_with_tally,
)
from sams_accounting_desktop.services.tally_client import (
    TallyImportResult,
    TallyLedgerGstRecord,
    TallyMasterRecord,
    fetch_tally_groups,
    fetch_tally_ledger_gst_records,
    update_tally_ledger_gstin,
)
from sams_accounting_desktop.services.tally_purchase_client import (
    TallyPurchaseVoucher,
    fetch_tally_purchase_vouchers,
    update_tally_purchase_supplier_invoice_number,
)


GENERIC_PARTY_NAME_TOKENS = {
    "agency",
    "agencies",
    "agri",
    "agro",
    "agriculture",
    "agricultural",
    "center",
    "centre",
    "ceramic",
    "company",
    "corp",
    "corporation",
    "decor",
    "dealer",
    "dealers",
    "distributor",
    "distributors",
    "enterprise",
    "enterprises",
    "fertiliser",
    "fertilisers",
    "fertilizer",
    "fertilizers",
    "flooring",
    "floorings",
    "hardware",
    "industries",
    "industry",
    "kendra",
    "kendras",
    "kisan",
    "krishi",
    "limited",
    "marble",
    "mart",
    "merchant",
    "merchants",
    "mills",
    "private",
    "proprietor",
    "retail",
    "retailer",
    "retailers",
    "sales",
    "service",
    "services",
    "seva",
    "sewa",
    "shop",
    "sons",
    "store",
    "stores",
    "stone",
    "supplier",
    "suppliers",
    "tile",
    "tiles",
    "trader",
    "traders",
    "trading",
}

PARTY_TOKEN_ALIASES = {
    "centre": "center",
    "centres": "center",
    "fertiliser": "fertilizer",
    "fertilisers": "fertilizer",
    "fertilizers": "fertilizer",
    "kendras": "kendra",
    "services": "service",
    "sewa": "seva",
    "stores": "store",
    "traders": "trader",
}


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


@dataclass(frozen=True)
class LedgerGstSuggestion:
    ledger_name: str
    parent: str = ""
    suggested_gstin: str = ""
    suggested_party_name: str = ""
    status: str = "unregistered"
    match_score: int = 0

    @property
    def has_suggestion(self) -> bool:
        return bool(self.suggested_gstin)


@dataclass(frozen=True)
class LedgerGstUpdateResult:
    ledger_name: str
    gstin: str
    success: bool
    message: str


@dataclass(frozen=True)
class PurchaseInvoiceNumberUpdateResult:
    voucher_number: str
    party_ledger_name: str
    old_invoice_number: str
    new_invoice_number: str
    success: bool
    message: str


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


def build_missing_ledger_gst_suggestions(
    excel_paths: Sequence[str | Path],
    *,
    tally_url: str = DEFAULT_TALLY_URL,
) -> list[LedgerGstSuggestion]:
    gst_rows = load_gst_purchase_rows(excel_paths) if excel_paths else []
    ledger_records = fetch_tally_ledger_gst_records(tally_url)
    group_records = fetch_tally_groups(tally_url)
    party_ledgers = filter_ledger_gst_records_by_groups(
        ledger_records,
        group_records,
        ("Sundry Debtors", "Sundry Creditors"),
    )
    missing_ledgers = [record for record in party_ledgers if not normalize_gstin(record.gstin)]
    return [suggest_gstin_for_ledger(record, gst_rows) for record in missing_ledgers]


def filter_ledger_gst_records_by_groups(
    ledger_records: Sequence[TallyLedgerGstRecord],
    group_records: Sequence[TallyMasterRecord],
    allowed_groups: tuple[str, ...],
) -> list[TallyLedgerGstRecord]:
    allowed = {group.casefold() for group in allowed_groups}
    group_parents = {group.name.casefold(): group.parent.casefold() for group in group_records}
    matches: list[TallyLedgerGstRecord] = []

    for ledger in ledger_records:
        current_group = ledger.parent.casefold()
        visited: set[str] = set()
        while current_group and current_group not in visited:
            if current_group in allowed:
                matches.append(ledger)
                break
            visited.add(current_group)
            current_group = group_parents.get(current_group, "")

    return sorted(matches, key=lambda record: record.name.casefold())


def suggest_gstin_for_ledger(
    ledger_record: TallyLedgerGstRecord,
    gst_rows: Sequence[GstPurchaseRow],
) -> LedgerGstSuggestion:
    candidates: list[tuple[int, str, str]] = []
    for row in gst_rows:
        supplier_gstin = normalize_gstin(row.supplier_gstin)
        supplier_name = (row.supplier_name or "").strip()
        if not supplier_gstin or not supplier_name:
            continue
        score = party_name_match_score(ledger_record.name, supplier_name)
        if score >= 60:
            candidates.append((score, supplier_gstin, supplier_name))

    if not candidates:
        return LedgerGstSuggestion(
            ledger_name=ledger_record.name,
            parent=ledger_record.parent,
            status="unregistered",
        )

    candidates.sort(key=lambda row: (row[0], row[1], row[2].casefold()), reverse=True)
    best_score, best_gstin, best_party = candidates[0]
    tied_gstins = {gstin for score, gstin, _party in candidates if score == best_score}
    if len(tied_gstins) > 1:
        return LedgerGstSuggestion(
            ledger_name=ledger_record.name,
            parent=ledger_record.parent,
            status="review",
            match_score=best_score,
        )

    return LedgerGstSuggestion(
        ledger_name=ledger_record.name,
        parent=ledger_record.parent,
        suggested_gstin=best_gstin,
        suggested_party_name=best_party,
        status="suggested",
        match_score=best_score,
    )


def party_name_match_score(ledger_name: str, supplier_name: str) -> int:
    ledger_tokens = normalized_party_tokens(ledger_name)
    supplier_tokens = normalized_party_tokens(supplier_name)
    if not ledger_tokens or not supplier_tokens:
        return 0

    ledger_distinctive = distinctive_party_tokens(ledger_tokens)
    supplier_distinctive = distinctive_party_tokens(supplier_tokens)
    if not ledger_distinctive or not supplier_distinctive:
        return 0

    common_distinctive = ledger_distinctive & supplier_distinctive
    if not common_distinctive:
        return 0

    ledger_key = compact_party_tokens(ledger_distinctive)
    supplier_key = compact_party_tokens(supplier_distinctive)
    if ledger_key == supplier_key:
        return 100

    if common_distinctive and (
        ledger_distinctive <= supplier_distinctive or supplier_distinctive <= ledger_distinctive
    ):
        return 90

    overlap_ratio = len(common_distinctive) / max(len(ledger_distinctive), len(supplier_distinctive))
    if len(common_distinctive) >= 2 and overlap_ratio >= 0.75:
        return 80 + min(len(common_distinctive), 10)
    return 0


def normalized_party_tokens(value: str) -> set[str]:
    return {PARTY_TOKEN_ALIASES.get(token, token) for token in meaningful_tokens(value)}


def distinctive_party_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if token not in GENERIC_PARTY_NAME_TOKENS}


def compact_party_tokens(tokens: set[str]) -> str:
    return "".join(sorted(tokens))


def update_suggested_ledger_gstins(
    suggestions: Sequence[LedgerGstSuggestion],
    *,
    tally_url: str = DEFAULT_TALLY_URL,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[LedgerGstUpdateResult]:
    updates = [suggestion for suggestion in suggestions if suggestion.suggested_gstin]
    results: list[LedgerGstUpdateResult] = []
    total = len(updates)

    for index, suggestion in enumerate(updates, start=1):
        try:
            result: TallyImportResult = update_tally_ledger_gstin(
                tally_url,
                ledger_name=suggestion.ledger_name,
                parent=suggestion.parent,
                gstin=suggestion.suggested_gstin,
            )
            results.append(
                LedgerGstUpdateResult(
                    ledger_name=suggestion.ledger_name,
                    gstin=suggestion.suggested_gstin,
                    success=result.success,
                    message=result.message,
                )
            )
        except Exception as exc:
            results.append(
                LedgerGstUpdateResult(
                    ledger_name=suggestion.ledger_name,
                    gstin=suggestion.suggested_gstin,
                    success=False,
                    message=str(exc),
                )
            )
        if progress_callback is not None:
            progress_callback(index, total)

    return results


def update_purchase_invoice_numbers_same_as_excel(
    reconciliation_results: Sequence[dict],
    *,
    tally_url: str = DEFAULT_TALLY_URL,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[PurchaseInvoiceNumberUpdateResult]:
    results: list[PurchaseInvoiceNumberUpdateResult] = []
    total = len(reconciliation_results)

    for index, reconciliation_result in enumerate(reconciliation_results, start=1):
        update_result = update_purchase_invoice_number_same_as_excel(
            reconciliation_result,
            tally_url=tally_url,
        )
        results.append(update_result)
        if progress_callback is not None:
            progress_callback(index, total)

    return results


def update_purchase_invoice_number_same_as_excel(
    reconciliation_result: dict,
    *,
    tally_url: str = DEFAULT_TALLY_URL,
) -> PurchaseInvoiceNumberUpdateResult:
    gst_row = reconciliation_result.get("gst")
    tally_row = reconciliation_result.get("tally")
    new_invoice = normalized_invoice_text(getattr(gst_row, "invoice_number", "") if gst_row is not None else "")
    old_invoice = normalized_invoice_text(
        getattr(tally_row, "supplier_invoice_number", "") if tally_row is not None else ""
    )
    voucher_number = getattr(tally_row, "voucher_number", "") if tally_row is not None else ""
    party_ledger_name = getattr(tally_row, "party_ledger_name", "") if tally_row is not None else ""

    if gst_row is None or tally_row is None:
        return PurchaseInvoiceNumberUpdateResult(
            voucher_number=voucher_number,
            party_ledger_name=party_ledger_name,
            old_invoice_number=old_invoice,
            new_invoice_number=new_invoice,
            success=False,
            message="Excel row ya Tally voucher missing hai.",
        )
    if not new_invoice:
        return PurchaseInvoiceNumberUpdateResult(
            voucher_number=voucher_number,
            party_ledger_name=party_ledger_name,
            old_invoice_number=old_invoice,
            new_invoice_number=new_invoice,
            success=False,
            message="Excel invoice number blank hai.",
        )

    if old_invoice and old_invoice.casefold() == new_invoice.casefold():
        mark_invoice_number_updated(reconciliation_result, new_invoice, old_invoice, "Already same as Excel.")
        return PurchaseInvoiceNumberUpdateResult(
            voucher_number=voucher_number,
            party_ledger_name=party_ledger_name,
            old_invoice_number=old_invoice,
            new_invoice_number=new_invoice,
            success=True,
            message="Already same as Excel.",
        )

    try:
        tally_result = update_tally_purchase_supplier_invoice_number(
            tally_url,
            tally_row,
            supplier_invoice_number=new_invoice,
        )
    except Exception as exc:
        return PurchaseInvoiceNumberUpdateResult(
            voucher_number=voucher_number,
            party_ledger_name=party_ledger_name,
            old_invoice_number=old_invoice,
            new_invoice_number=new_invoice,
            success=False,
            message=str(exc),
        )

    if tally_result.success:
        mark_invoice_number_updated(reconciliation_result, new_invoice, old_invoice, tally_result.message)

    return PurchaseInvoiceNumberUpdateResult(
        voucher_number=voucher_number,
        party_ledger_name=party_ledger_name,
        old_invoice_number=old_invoice,
        new_invoice_number=new_invoice,
        success=tally_result.success,
        message=tally_result.message,
    )


def mark_invoice_number_updated(
    reconciliation_result: dict,
    new_invoice: str,
    old_invoice: str,
    message: str,
) -> None:
    tally_row = reconciliation_result.get("tally")
    if tally_row is not None:
        tally_row.supplier_invoice_number = new_invoice
        bill_references = list(getattr(tally_row, "bill_references", []) or [])
        if old_invoice:
            bill_references = [
                new_invoice if normalized_invoice_text(reference).casefold() == old_invoice.casefold() else reference
                for reference in bill_references
            ]
        if new_invoice not in bill_references:
            bill_references.insert(0, new_invoice)
        tally_row.bill_references = bill_references

    reconciliation_result["invoice_updated"] = True
    reconciliation_result["invoice_update_message"] = message
    reasons = list(reconciliation_result.get("reasons", []) or [])
    update_reason = f"Tally supplier invoice updated same as Excel: {new_invoice}"
    if update_reason not in reasons:
        reasons.insert(0, update_reason)
    reconciliation_result["reasons"] = reasons


def normalized_invoice_text(value: str) -> str:
    return " ".join(str(value or "").split())


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
    if from_date is None or to_date is None:
        inferred_from_date, inferred_to_date = infer_tally_date_window(gst_rows)
        from_date = from_date or inferred_from_date
        to_date = to_date or inferred_to_date
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


def infer_tally_date_window(gst_rows: Sequence[GstPurchaseRow]) -> tuple[date | None, date | None]:
    invoice_dates = [row.invoice_date for row in gst_rows if row.invoice_date is not None]
    if not invoice_dates:
        return None, None
    return min(invoice_dates) - timedelta(days=7), max(invoice_dates) + timedelta(days=7)
