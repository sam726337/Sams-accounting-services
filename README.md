# Sams Accounting Desktop UI

Local-only PySide6 desktop UI draft for Sam's Accounting.

Setup and run:

```powershell
python -m venv ".venv"
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".venv\Scripts\python.exe" app.py
```

Alternative module entrypoint:

```powershell
& ".venv\Scripts\python.exe" -m sams_accounting_desktop
```

Project layout:

```text
app.py
sams_accounting_desktop/
  config.py
  data.py
  main.py
  models.py
  services/
    tally_client.py
  ui/
    components.py
    dashboard_window.py
    icons.py
    styles.py
    tally_panel.py
  workers/
    tally_worker.py
```

Tally connector:

1. Tally Prime open rakhein.
2. Tally me HTTP server enable karein on port `9000`.
3. Company open rakhein.
4. App me `Tally Connector` panel se `Test Connection` dabayein.
5. `Fetch Ledgers` se Tally masters read karke verify karein.

Purchase reconciliation backend:

```python
from sams_accounting_desktop.services import export_purchase_reco_excel, run_purchase_reco

run = run_purchase_reco(
    ["gst-purchase-register.xlsx"],
    tally_url="http://127.0.0.1:9000",
)
print(run.summary)
export_purchase_reco_excel(run, "purchase-reco-result.xlsx")
```
