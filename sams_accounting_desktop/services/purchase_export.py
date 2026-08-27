from __future__ import annotations

from io import BytesIO
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
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
    prepared_results = list(results)
    supplier_by_gstin: dict[str, str] = {}
    for r in prepared_results:
        gst = r.get("gst")
        supplier_gstin = getattr(gst, "supplier_gstin", "") if gst is not None else ""
        supplier_name = getattr(gst, "supplier_name", "") if gst is not None else ""
        if supplier_gstin and supplier_name:
            supplier_by_gstin.setdefault(str(supplier_gstin).strip().upper(), str(supplier_name).strip())

    for r in prepared_results:
        gst = r.get("gst")
        tally = r.get("tally") or {}
        supplier_gstin = getattr(gst, "supplier_gstin", "") if gst is not None else ""
        supplier_name = getattr(gst, "supplier_name", "") if gst is not None else ""
        if not supplier_name and supplier_gstin:
            supplier_name = supplier_by_gstin.get(str(supplier_gstin).strip().upper(), "")
        if not supplier_name and supplier_gstin:
            supplier_name = "Name unavailable"
        yield {
            "status": r.get("status", ""),
            "supplier_name": supplier_name,
            "supplier_gstin": supplier_gstin,
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


def _pdf_wrap_text(value: object, width: float, font_size: float, max_lines: int) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return [""]

    def fits(candidate: str) -> bool:
        if fitz is None:
            return len(candidate) <= max(4, int(width / (font_size * 0.48)))
        return fitz.get_text_length(candidate, fontname="helv", fontsize=font_size) <= width

    max_chars = max(4, int(width / (font_size * 0.44)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        current = ""
        for word in words:
            if not fits(word):
                if current:
                    lines.append(current)
                    current = ""
                while word and not fits(word):
                    split_at = max_chars - 1
                    while split_at > 3 and not fits(word[:split_at] + "-"):
                        split_at -= 1
                    lines.append(word[:split_at] + "-")
                    word = word[split_at:]
                    if len(lines) >= max_lines:
                        break
                if len(lines) >= max_lines:
                    break
            candidate = word if not current else f"{current} {word}"
            if fits(candidate):
                current = candidate
            else:
                lines.append(current)
                current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) >= max_lines:
            break

    if not lines:
        return [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines and len(text) > sum(len(line) for line in lines):
        lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def _pdf_text_height(value: object, width: float, font_size: float, line_height: float, max_lines: int) -> float:
    return len(_pdf_wrap_text(value, width, font_size, max_lines)) * line_height


def _pdf_logo_path() -> Path | None:
    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parents[1] / "assets" / "logo.jpeg",
        current_file.parents[2] / "assets" / "logo.jpeg",
        current_file.parents[3] / "site" / "assets" / "logo.jpeg",
        current_file.parents[3] / "site" / "assets" / "sams-it-solution-logo.jpeg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def export_reconciliation_to_pdf(results: Iterable[dict], file_path: str | None = None) -> bytes | None:
    """Export reconciliation `results` to a polished table PDF using PyMuPDF.

    Returns bytes if `file_path` is None, otherwise writes to disk.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) not available. Install PyMuPDF to export PDF files.")

    rows = list(_iter_result_rows(results))
    page_width = 842
    page_height = 595
    margin = 28
    footer_height = 58
    table_top = 226
    row_font_size = 8.4
    header_font_size = 8.2
    line_height = 11.2
    cell_padding_x = 4.0
    cell_padding_y = 5.5
    header_height = 28
    usable_bottom = page_height - margin - footer_height
    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M")
    status_counts = {
        status: sum(1 for row in rows if str(row.get("status", "")).casefold() == status)
        for status in ("matched", "probable", "mismatch", "missing")
    }
    is_missing_report = bool(rows) and len(rows) == status_counts["missing"]
    title = "Purchase Reconciliation - Missing Entries" if is_missing_report else "Purchase Reconciliation Report"
    subtitle = "GST purchase rows with no reliable Tally match" if is_missing_report else "GST purchase Excel matched against Tally purchase vouchers"
    logo_path = _pdf_logo_path()

    if is_missing_report:
        columns = [
            ("Status", "status", 45, "left", 1),
            ("Supplier", "supplier_name", 142, "left", 4),
            ("GSTIN", "supplier_gstin", 90, "left", 2),
            ("Inv No", "invoice_number", 72, "left", 2),
            ("Inv Date", "invoice_date", 55, "left", 1),
            ("Inv Value", "invoice_value", 65, "right", 1),
            ("Taxable", "taxable_value", 65, "right", 1),
            ("Source File", "source_file", 95, "left", 2),
            ("Reason", "reasons", 157, "left", 4),
        ]
    else:
        columns = [
            ("Status", "status", 45, "left", 1),
            ("Supplier / Ledger", "supplier_name", 120, "left", 4),
            ("GSTIN", "supplier_gstin", 87, "left", 2),
            ("Inv No", "invoice_number", 62, "left", 2),
            ("Inv Date", "invoice_date", 54, "left", 1),
            ("Inv Value", "invoice_value", 56, "right", 1),
            ("Taxable", "taxable_value", 56, "right", 1),
            ("Tally No", "tally_voucher_number", 52, "left", 2),
            ("Tally Amt", "tally_amount", 52, "right", 1),
            ("Score", "score", 32, "right", 1),
            ("Reason", "reasons", 170, "left", 3),
        ]
    doc = fitz.Document()

    def status_palette(status: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        normalized = status.casefold()
        if normalized == "matched":
            return (0.02, 0.45, 0.28), (0.88, 0.97, 0.92)
        if normalized == "probable":
            return (0.71, 0.29, 0.03), (1.00, 0.94, 0.86)
        if normalized in {"mismatch", "missing"}:
            return (0.70, 0.14, 0.09), (1.00, 0.91, 0.90)
        return (0.20, 0.25, 0.32), (0.94, 0.96, 0.98)

    def add_footer(page, page_number: int, total_pages: int):
        y0 = page_height - 44
        page.draw_line((0, y0 - 12), (page_width, y0 - 12), color=(0.86, 0.89, 0.93), width=0.65)
        draw_simple_icon(page, margin + 18, y0 + 2, "shield", (0.06, 0.48, 0.86), 20)
        page.insert_text((margin + 38, y0 - 2), "Reconcile Smarter. Report Better.", fontname="helv", fontsize=8.4, color=(0.06, 0.35, 0.74))
        page.insert_text((margin + 38, y0 + 12), "Trusted by forward-thinking businesses.", fontname="helv", fontsize=7.4, color=(0.50, 0.56, 0.64))
        page.draw_line((page_width * 0.38, y0 - 7), (page_width * 0.38, y0 + 19), color=(0.82, 0.86, 0.90), width=0.55)
        draw_simple_icon(page, page_width * 0.42, y0 + 2, "lock", (0.26, 0.31, 0.39), 20)
        page.insert_text((page_width * 0.44, y0 - 2), "Confidential & Secure", fontname="helv", fontsize=8.4, color=(0.17, 0.30, 0.55))
        page.insert_text((page_width * 0.44, y0 + 12), "System generated and digitally secured.", fontname="helv", fontsize=7.4, color=(0.50, 0.56, 0.64))
        page.draw_line((page_width * 0.65, y0 - 7), (page_width * 0.65, y0 + 19), color=(0.82, 0.86, 0.90), width=0.55)
        draw_simple_icon(page, page_width * 0.69, y0 + 2, "spark", (0.30, 0.35, 0.44), 20)
        page.insert_text((page_width * 0.71, y0 - 2), "Thank you for using", fontname="helv", fontsize=7.6, color=(0.32, 0.37, 0.45))
        page.insert_text((page_width * 0.71, y0 + 12), "SAMS IT SOLUTION", fontname="helv", fontsize=8.4, color=(0.06, 0.35, 0.74))
        page.draw_line((page_width - 148, y0 - 7), (page_width - 148, y0 + 19), color=(0.82, 0.86, 0.90), width=0.55)
        page.insert_text((page_width - 105, y0 + 8), "Page", fontname="helv", fontsize=8.2, color=(0.21, 0.25, 0.32))
        page.draw_rect(fitz.Rect(page_width - 76, y0 - 4, page_width - 58, y0 + 14), color=(0.08, 0.43, 0.86), fill=(0.08, 0.43, 0.86), width=0)
        page.insert_text((page_width - 70, y0 + 8.5), str(page_number), fontname="helv", fontsize=8.2, color=(1, 1, 1))
        page.insert_text((page_width - 45, y0 + 8), f"of {total_pages}", fontname="helv", fontsize=8.2, color=(0.21, 0.25, 0.32))

    def draw_logo_mark(page):
        center = (margin + 30, 54)
        page.draw_circle(center, 30, color=(0.90, 0.96, 0.98), fill=(1, 1, 1), width=0.6)
        logo_rect = fitz.Rect(margin + 7, 31, margin + 53, 77)
        if logo_path is not None:
            try:
                page.insert_image(logo_rect, filename=str(logo_path), keep_proportion=True)
                return
            except Exception:
                pass
        page.draw_circle(center, 21, color=(0.00, 0.54, 0.55), fill=(0.00, 0.54, 0.55), width=0)
        page.insert_text((margin + 21, 59), "SA", fontname="helv", fontsize=13.5, color=(1, 1, 1))

    def draw_simple_icon(page, cx: float, cy: float, kind: str, color: tuple[float, float, float], size: float = 18):
        half = size / 2
        if kind in {"doc", "calendar", "file"}:
            page.draw_rect(fitz.Rect(cx - half * 0.55, cy - half, cx + half * 0.55, cy + half), color=color, width=1.4)
            page.draw_line((cx - half * 0.25, cy - half * 0.35), (cx + half * 0.30, cy - half * 0.35), color=color, width=1.0)
            page.draw_line((cx - half * 0.25, cy), (cx + half * 0.30, cy), color=color, width=1.0)
            if kind == "calendar":
                page.draw_line((cx - half * 0.55, cy - half * 0.45), (cx + half * 0.55, cy - half * 0.45), color=color, width=1.0)
        elif kind == "check":
            page.draw_circle((cx, cy), half, color=color, width=1.6)
            page.draw_line((cx - half * 0.45, cy), (cx - half * 0.10, cy + half * 0.32), color=color, width=1.6)
            page.draw_line((cx - half * 0.10, cy + half * 0.32), (cx + half * 0.48, cy - half * 0.42), color=color, width=1.6)
        elif kind == "question":
            page.draw_circle((cx, cy), half, color=color, width=1.6)
            page.insert_text((cx - 2.8, cy + 4.0), "?", fontname="helv", fontsize=size * 0.8, color=color)
        elif kind == "search":
            page.draw_circle((cx - 2, cy - 2), half * 0.65, color=color, width=1.7)
            page.draw_line((cx + half * 0.35, cy + half * 0.35), (cx + half * 0.78, cy + half * 0.78), color=color, width=1.7)
        elif kind == "x":
            page.draw_circle((cx, cy), half, color=color, width=1.6)
            page.draw_line((cx - half * 0.38, cy - half * 0.38), (cx + half * 0.38, cy + half * 0.38), color=color, width=1.5)
            page.draw_line((cx + half * 0.38, cy - half * 0.38), (cx - half * 0.38, cy + half * 0.38), color=color, width=1.5)
        elif kind == "shield":
            points = [(cx, cy - half), (cx + half * 0.70, cy - half * 0.55), (cx + half * 0.55, cy + half * 0.45), (cx, cy + half), (cx - half * 0.55, cy + half * 0.45), (cx - half * 0.70, cy - half * 0.55)]
            page.draw_polyline(points + [points[0]], color=color, width=1.2)
        elif kind == "lock":
            page.draw_rect(fitz.Rect(cx - half * 0.58, cy - half * 0.05, cx + half * 0.58, cy + half * 0.75), color=color, width=1.2)
            page.draw_line((cx - half * 0.38, cy - half * 0.05), (cx - half * 0.38, cy - half * 0.45), color=color, width=1.2)
            page.draw_line((cx + half * 0.38, cy - half * 0.05), (cx + half * 0.38, cy - half * 0.45), color=color, width=1.2)
            page.draw_line((cx - half * 0.38, cy - half * 0.45), (cx + half * 0.38, cy - half * 0.45), color=color, width=1.2)
        elif kind == "spark":
            page.draw_line((cx, cy - half), (cx, cy + half), color=color, width=1.2)
            page.draw_line((cx - half, cy), (cx + half, cy), color=color, width=1.2)
            page.draw_line((cx - half * 0.50, cy - half * 0.50), (cx + half * 0.50, cy + half * 0.50), color=color, width=0.9)

    def draw_kpi_card(page, x: float, label: str, value: object, accent: tuple[float, float, float], icon: str):
        card_width = 146
        card_height = 58
        y = 136
        page.draw_rect(fitz.Rect(x + 2, y + 2, x + card_width + 2, y + card_height + 2), color=(0.90, 0.92, 0.94), fill=(0.90, 0.92, 0.94), width=0)
        page.draw_rect(
            fitz.Rect(x, y, x + card_width, y + card_height),
            color=(0.88, 0.91, 0.94),
            fill=(1, 1, 1),
            width=0.5,
        )
        page.draw_circle((x + 28, y + 29), 14, color=accent, fill=accent, width=0)
        draw_simple_icon(page, x + 28, y + 29, icon, (1, 1, 1), 17)
        page.insert_text((x + 56, y + 24), label, fontname="helv", fontsize=8.8, color=(0.28, 0.33, 0.41))
        page.insert_text((x + 56, y + 45), str(value), fontname="helv", fontsize=18.0, color=(0.04, 0.07, 0.12))
        if label.startswith("Total"):
            page.draw_line((x, y + card_height), (x + card_width, y + card_height), color=accent, width=1.8)

    def draw_page_header(page):
        page.draw_rect(fitz.Rect(0, 0, page_width, 118), color=(0.02, 0.06, 0.12), fill=(0.02, 0.06, 0.12), width=0)
        page.draw_rect(fitz.Rect(0, 0, page_width, 6), color=(0.08, 0.52, 0.93), fill=(0.08, 0.52, 0.93), width=0)
        page.draw_circle((page_width - 62, -18), 38, color=(0.38, 0.28, 0.90), fill=(0.38, 0.28, 0.90), width=0)
        page.draw_circle((page_width - 38, 10), 34, color=(0.22, 0.55, 0.97), fill=(0.22, 0.55, 0.97), width=0)
        page.draw_circle((page_width - 16, 30), 30, color=(0.43, 0.22, 0.86), fill=(0.43, 0.22, 0.86), width=0)
        page.draw_rect(fitz.Rect(page_width - 242, 23, page_width - 32, 102), color=(0.06, 0.14, 0.25), fill=(0.06, 0.14, 0.25), width=0)
        page.draw_line((page_width - 258, 28), (page_width - 258, 98), color=(0.12, 0.52, 0.93), width=1.0)

        draw_logo_mark(page)
        page.insert_text((margin + 78, 39), "SAMS IT SOLUTION", fontname="helv", fontsize=10.0, color=(0.21, 0.58, 0.98))
        page.insert_text((margin + 78, 66), title, fontname="helv", fontsize=19.5, color=(1, 1, 1))
        page.insert_text((margin + 78, 90), "Ensure accuracy, eliminate mismatch, and reconcile with confidence.", fontname="helv", fontsize=10.0, color=(0.74, 0.81, 0.88))

        draw_simple_icon(page, page_width - 214, 47, "calendar", (1, 1, 1), 18)
        page.insert_text((page_width - 186, 41), "Purchase Reco", fontname="helv", fontsize=8.6, color=(0.42, 0.82, 0.92))
        page.insert_text((page_width - 186, 56), f"Generated On: {generated_at}", fontname="helv", fontsize=8.4, color=(0.86, 0.91, 0.96))
        draw_simple_icon(page, page_width - 214, 82, "file", (1, 1, 1), 18)
        page.insert_text((page_width - 186, 78), "Premium PDF Export", fontname="helv", fontsize=8.5, color=(1, 1, 1))
        page.insert_text((page_width - 186, 93), "High Quality  •  Secure  •  Verified", fontname="helv", fontsize=8.1, color=(0.84, 0.89, 0.95))

        kpis = [
            ("Total Entries", len(rows), (0.10, 0.45, 0.88), "doc"),
            ("Matched", status_counts["matched"], (0.27, 0.64, 0.20), "check"),
            ("Probable Match", status_counts["probable"], (0.98, 0.61, 0.04), "question"),
            ("Mismatch", status_counts["mismatch"], (0.43, 0.20, 0.82), "search"),
            ("Missing Entries", status_counts["missing"], (0.93, 0.22, 0.22), "x"),
        ]
        start_x = margin
        for index, (label, value, accent, icon) in enumerate(kpis):
            draw_kpi_card(page, start_x + index * 158, label, value, accent, icon)

    def draw_status_badge(page, rect, value: object):
        status = str(value or "").title()
        foreground, background = status_palette(str(value or ""))
        badge_width = min(rect.width, max(36, len(status) * 5.0 + 8))
        badge_height = 17
        y = rect.y0 + 0.8
        page.draw_rect(
            fitz.Rect(rect.x0, y, rect.x0 + badge_width, y + badge_height),
            color=background,
            fill=background,
            width=0,
        )
        page.insert_text(
            (rect.x0 + 4, y + 11.5),
            status,
            fontname="helv",
            fontsize=7.5,
            color=foreground,
        )

    def draw_cell_text(page, rect, value: object, width: float, align: str, max_lines: int):
        lines = _pdf_wrap_text(value, width, row_font_size, max_lines)
        baseline = rect.y0 + row_font_size
        for line in lines:
            x = rect.x0
            if align == "right" and fitz is not None:
                text_width = fitz.get_text_length(line, fontname="helv", fontsize=row_font_size)
                x = max(rect.x0, rect.x1 - text_width)
            page.insert_text(
                (x, baseline),
                line,
                fontname="helv",
                fontsize=row_font_size,
                color=(0.06, 0.09, 0.16),
            )
            baseline += line_height

    def draw_table_header(page, y: float) -> float:
        x = margin
        page.draw_rect(
            fitz.Rect(margin, y, page_width - margin, y + header_height),
            color=(0.07, 0.10, 0.16),
            fill=(0.07, 0.10, 0.16),
            width=0,
        )
        page.draw_line((margin, y), (page_width - margin, y), color=(0.30, 0.95, 0.84), width=0.6)
        for label, _key, width, align, _max_lines in columns:
            rect = fitz.Rect(x + cell_padding_x, y + 7, x + width - cell_padding_x, y + header_height - 3)
            page.insert_textbox(
                rect,
                label,
                fontname="helv",
                fontsize=header_font_size,
                color=(1, 1, 1),
                align=fitz.TEXT_ALIGN_RIGHT if align == "right" else fitz.TEXT_ALIGN_LEFT,
            )
            x += width
        return y + header_height

    def new_page():
        page = doc.new_page(width=page_width, height=page_height)
        draw_page_header(page)
        return page, draw_table_header(page, table_top)

    page, y = new_page()
    if not rows:
        page.insert_text((margin, y + 28), "No reconciliation rows available.", fontname="helv", fontsize=11.5, color=(0.29, 0.33, 0.39))

    for row_index, row in enumerate(rows):
        row_height = max(
            29,
            max(
                _pdf_text_height(row.get(key, ""), width - (cell_padding_x * 2), row_font_size, line_height, max_lines)
                for _label, key, width, _align, max_lines in columns
            )
            + (cell_padding_y * 2),
        )
        if y + row_height > usable_bottom:
            page, y = new_page()

        fill = (0.975, 0.99, 1.00) if row_index % 2 else (1, 1, 1)
        page.draw_rect(
            fitz.Rect(margin, y, page_width - margin, y + row_height),
            color=(0.86, 0.89, 0.93),
            fill=fill,
            width=0.35,
        )

        x = margin
        for _label, key, width, align, max_lines in columns:
            value = row.get(key, "")
            rect = fitz.Rect(
                x + cell_padding_x,
                y + cell_padding_y,
                x + width - cell_padding_x,
                y + row_height - cell_padding_y,
            )
            if key == "status":
                draw_status_badge(page, rect, value)
            else:
                draw_cell_text(page, rect, value, width - (cell_padding_x * 2), align, max_lines)
            if x > margin:
                page.draw_line((x, y), (x, y + row_height), color=(0.90, 0.92, 0.95), width=0.25)
            x += width
        y += row_height

    for page_index in range(doc.page_count):
        add_footer(doc[page_index], page_index + 1, doc.page_count)

    if file_path:
        doc.save(file_path)
        doc.close()
        return None

    bio = BytesIO()
    doc.save(bio)
    doc.close()
    return bio.getvalue()
