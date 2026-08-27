# Sams Accounting Desktop — Microsoft Store submission

## Product

- Product name: Sams Accounting Desktop
- Publisher display name: The Jishu IT Solution
- Version: 1.0.3.0
- Category: Business > Accounting & finance
- Pricing: Free download; signed licence or 14-day local trial inside the app
- Markets: India initially, then all supported English-language markets
- Website: https://thejishu.in/
- Support: sameermansurisam@gmail.com
- Privacy policy: https://thejishu.in/privacy.html
- Terms of use: https://thejishu.in/terms.html

## Short description

Prepare bank, purchase, GST and sales workflows for review and controlled posting to Tally Prime.

## Description

Sams Accounting Desktop helps accounting teams reduce repetitive preparation work before entries reach Tally Prime. Import supported bank statements and GST purchase files, review parsed transactions, reconcile purchase data, generate sales entries and send approved vouchers to a locally running Tally Prime instance.

The app keeps accounting processing on the Windows device. It connects to the Tally XML interface configured by the user, normally on localhost, and requires the user to review entries before posting. A 14-day local trial is available, with signed offline licences for continued use.

## Key features

- Parse supported bank statement PDFs
- Review debit and credit transactions before posting
- Reconcile GST purchase spreadsheets with Tally purchase data
- Generate reviewable sales voucher entries
- Connect to the local Tally Prime XML interface
- Signed offline licences and a 14-day local trial
- Local settings and consent record

## Certification notes

- This is a packaged Win32/PySide6 full-trust desktop application.
- The `runFullTrust` restricted capability is required to launch the desktop executable and access user-selected accounting files.
- Network access is used for the user-configured Tally XML endpoint and the public update manifest.
- The app does not silently post vouchers. Users review and explicitly initiate Tally operations.
- Test reviewers may use the 14-day local trial after accepting the Terms of Use and Privacy Policy.
- No external Tally installation is required to open and inspect the user interface; Tally-dependent actions display a connection error when no local endpoint is available.

## Before submission

1. Reserve the product name in Partner Center.
2. Copy Package Identity Name, Publisher ID and Publisher Display Name into a private `store-identity.json` based on `store-identity.example.json`.
3. Run `build-store-msix.ps1 -StoreIdentityPath .\store-identity.json`.
4. Confirm the public Terms and Privacy URLs return HTTP 200.
5. Upload the MSIX, listing images and screenshots.
6. Complete age rating and legal declarations in Partner Center.
7. Submit for Microsoft certification only after final review.
