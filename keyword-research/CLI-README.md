# Google Ads Keyword Planner CLI

This read-only CLI calls `KeywordPlanIdeaService.GenerateKeywordIdeas`, ranks
ideas by average monthly searches, and writes a CSV report.

## Prerequisites

- The service account must have access to the target Google Ads account.
- Google Ads API must be enabled in the Cloud project.
- A valid Google Ads API developer token is required.
- Python package `google-auth` is required.

## PowerShell usage

Set secrets only for the current terminal session:

```powershell
$env:GOOGLE_ADS_DEVELOPER_TOKEN = Read-Host 'Google Ads developer token'
$env:GOOGLE_ADS_CUSTOMER_ID = Read-Host 'Target 10-digit Google Ads customer ID'
python .\keyword-research\google_ads_keyword_cli.py --market all --top 30
```

Validate files and seed lists without contacting Google Ads:

```powershell
python .\keyword-research\google_ads_keyword_cli.py --dry-run
```

Supported markets are `india`, `dubai`, `us`, and `uk`. Use `all` to query
all four. The default report is `keyword-research/keyword-planner-results.csv`.
Developer tokens and private keys are never written to the report.
