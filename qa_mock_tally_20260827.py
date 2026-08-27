from __future__ import annotations

from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

from sams_accounting_desktop.services.bank_pdf_service import create_tally_bank_voucher
from sams_accounting_desktop.services.tally_client import fetch_tally_ledgers, test_tally_connection


COMPANY_XML = "<ENVELOPE><BODY><DATA><COLLECTION><COMPANY NAME='QA Books'><NAME>QA Books</NAME></COMPANY></COLLECTION></DATA></BODY></ENVELOPE>"
LEDGER_XML = "<ENVELOPE><BODY><DATA><COLLECTION><LEDGER NAME='Bank Current A/c'/><LEDGER NAME='Office Rent'/><LEDGER NAME='Client Alpha'/></COLLECTION></DATA></BODY></ENVELOPE>"
IMPORT_XML = "<ENVELOPE><BODY><DATA><IMPORTRESULT><CREATED>1</CREATED><ALTERED>0</ALTERED><DELETED>0</DELETED><ERRORS>0</ERRORS><LASTVCHID>101</LASTVCHID></IMPORTRESULT></DATA></BODY></ENVELOPE>"


class Handler(BaseHTTPRequestHandler):
    requests: list[str] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        self.requests.append(body)
        upper = body.upper()
        if "<VOUCHER " in upper:
            response = IMPORT_XML
        elif "LEDGER" in upper:
            response = LEDGER_XML
        else:
            response = COMPANY_XML
        encoded = response.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format, *_args):
        return


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_port}"

try:
    ok, message, companies = test_tally_connection(url)
    print("PASS | mock Tally connection", ok, message, companies)

    ledgers = fetch_tally_ledgers(url)
    print("PASS | mock ledger fetch", ledgers == ["Bank Current A/c", "Client Alpha", "Office Rent"], ledgers)

    result = create_tally_bank_voucher(
        url,
        voucher_type="Payment",
        voucher_date=date(2026, 8, 27),
        bank_ledger="Bank Current A/c",
        opposite_ledger="Office Rent",
        amount=Decimal("25000.00"),
        narration="Launch QA voucher",
        voucher_number="QA-001",
    )
    print("PASS | mock voucher post", result.success, result.message)
    print("PASS | request count", len(Handler.requests) == 3, len(Handler.requests))
    raise SystemExit(0 if ok and result.success and len(ledgers) == 3 else 1)
finally:
    server.shutdown()
    server.server_close()
