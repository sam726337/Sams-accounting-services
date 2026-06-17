# Sams Accounting Desktop UI

Local-only PySide6 desktop UI draft for Sam's Accounting.

Setup and run:

```powershell
python -m venv ".venv"
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".venv\Scripts\python.exe" app.py
```

Tally connector:

1. Tally Prime open rakhein.
2. Tally me HTTP server enable karein on port `9000`.
3. Company open rakhein.
4. App me `Tally Connector` panel se `Test Connection` dabayein.
5. `Fetch Ledgers` se Tally masters read karke verify karein.
