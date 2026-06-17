from __future__ import annotations

from io import BytesIO
from datetime import date
from decimal import Decimal
from typing import Iterable

try:
    from openpyxl import Workbook
except Exception:  # pragma: no cover - runtime dependency
    Workbook = None

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - runtime dependency
    fitz = None


def _format_date(value: date | None) -> str:
    return value.isoformat() if isinstance(value, date) else (str(value) if value is not None else "")


def _format_decimal(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    try:
        return f"{Decimal(value):.2f}"
    except Exception:
        return str(value)


def _iter_result_rows(results: Iterable[dict]) -> Iterable[dict]:
    for r in results:
        gst = r.get("gst")
        tally = r.get("tally") or {}
        yield {
            "status": r.get("status", ""),
            "supplier_name": getattr(gst, "supplier_name", "") if gst is not None else "",
            "supplier_gstin": getattr(gst, "supplier_gstin", "") if gst is not None else "",
            "invoice_number": getattr(gst, "invoice_number", "") if gst is not None else "",
            "invoice_date": _format_date(getattr(gst, "invoice_date", None) if gst is not None else None),
            "invoice_value": _format_decimal(getattr(gst, "invoice_value", None) if gst is not None else None),
            "taxable_value": _format_decimal(getattr(gst, "taxable_value", None) if gst is not None else None),
            "tally_voucher_number": getattr(tally, "voucher_number", "") if hasattr(tally, "voucher_number") else (tally.get("voucher_number") if isinstance(tally, dict) else ""),
            "tally_date": _format_date(getattr(tally, "date", None) if hasattr(tally, "date") else (tally.get("date") if isinstance(tally, dict) else None)),
            "tally_amount": _format_decimal(getattr(tally, "amount", None) if hasattr(tally, "amount") else (tally.get("amount") if isinstance(tally, dict) else None)),
            "score": r.get("score", ""),
            "reasons": ", ".join(r.get("reasons", []) or []),
            "source_file": getattr(gst, "source_file", "") if gst is not None else "",
        }


def export_reconciliation_to_excel(results: Iterable[dict], file_path: str | None = None) -> bytes | None:
    """Export reconciliation `results` to an Excel workbook.

    If `file_path` is provided the workbook is saved to disk and the function
    returns None. If `file_path` is None the function returns the generated
    workbook as bytes suitable for sending to a downloader UI.
    """
    if Workbook is None:
        raise RuntimeError("openpyxl not available. Install openpyxl to export Excel files.")

    wb = Workbook()
    ws = wb.active
    headers = [
        "Status",
        "Supplier name",
        "Supplier GSTIN",
        "Invoice number",
        "Invoice date",
        "Invoice value",
        "Taxable value",
        "Tally voucher number",
        "Tally date",
        "Tally amount",
        "Score",
        "Reasons",
        "Source file",
    ]
    ws.append(headers)
    for row in _iter_result_rows(results):
        ws.append([
            row["status"],
            row["supplier_name"],
            row["supplier_gstin"],
            row["invoice_number"],
            row["invoice_date"],
            row["invoice_value"],
            row["taxable_value"],
            row["tally_voucher_number"],
            row["tally_date"],
            row["tally_amount"],
            row["score"],
            row["reasons"],
            row["source_file"],
        ])

    if file_path:
        wb.save(file_path)
        return None

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def export_reconciliation_to_pdf(results: Iterable[dict], file_path: str | None = None) -> bytes | None:
    """Export reconciliation `results` to a simple PDF using PyMuPDF.

    Returns bytes if `file_path` is None, otherwise writes to disk.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) not available. Install PyMuPDF to export PDF files.")

    # Page size A4 points
    page_width = 595
    page_height = 842
    margin = 36
    line_height = 14

    doc = fitz.Document()
    x = margin
    y = margin

    headers = [
        "Status",
        "Supplier",
        "GSTIN",
        "Inv No",
        "Inv Date",
        "Inv Value",
        "Taxable",
        "Tally No",
        "Tally Date",
        "Tally Amt",
        "Score",
    ]

    def new_page():
        nonlocal x, y
        page = doc.new_page(width=page_width, height=page_height)
        x = margin
        y = margin
        return page

    page = new_page()
    font = "helv"
    fontsize = 9

    header_text = "  ".join(headers)
    page.insert_text((x, y), header_text, fontname=font, fontsize=11)
    y += line_height * 1.5

    for row in _iter_result_rows(results):
        line = "  ".join(
            [
                str(row["status"]),
                row["supplier_name"][:20],
                row["supplier_gstin"],
                str(row["invoice_number"])[:12],
                row["invoice_date"],
                str(row["invoice_value"]),
                str(row["taxable_value"]),
                str(row["tally_voucher_number"])[:12],
                row["tally_date"],
                str(row["tally_amount"]),
                str(row["score"]),
            ]
        )
        if y + line_height > page_height - margin:
            page = new_page()
        page.insert_text((x, y), line, fontname=font, fontsize=fontsize)
        y += line_height

        # write reasons on next line if present
        reasons = row.get("reasons")
        if reasons:
            if y + line_height > page_height - margin:
                page = new_page()
            page.insert_text((x + 12, y), f"Reasons: {reasons}", fontname=font, fontsize=8)
            y += line_height

    if file_path:
        doc.save(file_path)
        doc.close()
        return None

    bio = BytesIO()
    doc.save(bio)
    doc.close()
    return bio.getvalue()
