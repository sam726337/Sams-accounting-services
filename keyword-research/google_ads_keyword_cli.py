#!/usr/bin/env python3
"""Read-only Google Ads Keyword Planner CLI.

Generates keyword ideas and historical metrics for The Jishu IT Solution's
supported markets. Secrets are read from environment variables/local Google
Cloud credentials and are never written to reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


API_VERSION = "v25"
ADWORDS_SCOPE = "https://www.googleapis.com/auth/adwords"
DEFAULT_LOGIN_CUSTOMER_ID = "4868781539"
DEFAULT_KEY_PATH = (
    Path(os.environ.get("APPDATA", ""))
    / "gcloud"
    / "google-ads-cli-20260828.json"
)


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    geo_target_id: str
    seed_file: str


MARKETS = {
    "india": Market("india", "India", "2356", "keyword-planner-india.csv"),
    "dubai": Market("dubai", "United Arab Emirates", "2784", "keyword-planner-dubai.csv"),
    "us": Market("us", "United States", "2840", "keyword-planner-us.csv"),
    "uk": Market("uk", "United Kingdom", "2826", "keyword-planner-uk.csv"),
}


OUTPUT_FIELDS = [
    "market",
    "keyword",
    "avg_monthly_searches",
    "competition",
    "competition_index",
    "low_top_of_page_bid",
    "high_top_of_page_bid",
]


def digits_only(value: str, label: str) -> str:
    cleaned = "".join(ch for ch in value if ch.isdigit())
    if len(cleaned) != 10:
        raise ValueError(f"{label} must be a 10-digit Google Ads customer ID.")
    return cleaned


def load_seed_keywords(base_dir: Path, market: Market) -> list[str]:
    # The API accepts at most 20 keyword seeds. Put location-specific commercial
    # terms first so a shared core list cannot crowd them out.
    paths = [base_dir / market.seed_file, base_dir / "keyword-planner-core.csv"]
    keywords: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Seed file not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                keyword = (row.get("Keyword") or "").strip()
                normalized = keyword.casefold()
                if keyword and normalized not in seen:
                    seen.add(normalized)
                    keywords.append(keyword)
    if not keywords:
        raise ValueError(f"No keywords found for {market.name}.")
    return keywords


def micros_to_currency(value: Any) -> str:
    if value in (None, ""):
        return ""
    return f"{int(value) / 1_000_000:.2f}"


def request_keyword_ideas(
    session: AuthorizedSession,
    *,
    developer_token: str,
    customer_id: str,
    login_customer_id: str,
    market: Market,
    keywords: list[str],
) -> Iterable[dict[str, Any]]:
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}/customers/"
        f"{customer_id}:generateKeywordIdeas"
    )
    headers = {
        "developer-token": developer_token,
        "login-customer-id": login_customer_id,
        "Content-Type": "application/json",
    }
    base_payload: dict[str, Any] = {
        "customerId": customer_id,
        "language": "languageConstants/1000",
        "geoTargetConstants": [f"geoTargetConstants/{market.geo_target_id}"],
        "includeAdultKeywords": False,
        "keywordPlanNetwork": "GOOGLE_SEARCH",
        "keywordSeed": {"keywords": keywords[:20]},
        "pageSize": 10000,
    }
    page_token = ""
    while True:
        payload = dict(base_payload)
        if page_token:
            payload["pageToken"] = page_token
        response = session.post(url, headers=headers, json=payload, timeout=120)
        if not response.ok:
            request_id = response.headers.get("request-id", "unknown")
            try:
                detail = response.json()
            except ValueError:
                detail = {"error": {"message": response.text[:500]}}
            message = detail.get("error", {}).get("message", "Google Ads API request failed")
            raise RuntimeError(
                f"Google Ads API HTTP {response.status_code}: {message} "
                f"(request-id: {request_id})"
            )
        data = response.json()
        yield from data.get("results", [])
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break


def normalize_result(market: Market, result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("keywordIdeaMetrics") or {}
    return {
        "market": market.name,
        "keyword": result.get("text", ""),
        "avg_monthly_searches": int(metrics.get("avgMonthlySearches") or 0),
        "competition": metrics.get("competition", "UNSPECIFIED"),
        "competition_index": metrics.get("competitionIndex", ""),
        "low_top_of_page_bid": micros_to_currency(metrics.get("lowTopOfPageBidMicros")),
        "high_top_of_page_bid": micros_to_currency(metrics.get("highTopOfPageBidMicros")),
    }


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and rank Google Keyword Planner ideas using Google Ads API."
    )
    parser.add_argument(
        "--market",
        choices=["all", *MARKETS],
        default="all",
        help="Target market (default: all).",
    )
    parser.add_argument(
        "--customer-id",
        default=os.environ.get("GOOGLE_ADS_CUSTOMER_ID", DEFAULT_LOGIN_CUSTOMER_ID),
        help="Target Google Ads customer ID; defaults to GOOGLE_ADS_CUSTOMER_ID.",
    )
    parser.add_argument(
        "--login-customer-id",
        default=os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", DEFAULT_LOGIN_CUSTOMER_ID),
        help="Manager account ID used for access.",
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        default=Path(os.environ.get("GOOGLE_ADS_KEY_FILE", DEFAULT_KEY_PATH)),
        help="Service-account JSON key path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "keyword-planner-results.csv",
        help="Destination CSV path.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of highest-volume rows to print (default: 25).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and seeds without calling Google Ads.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        customer_id = digits_only(args.customer_id, "customer-id")
        login_customer_id = digits_only(args.login_customer_id, "login-customer-id")
        selected = list(MARKETS.values()) if args.market == "all" else [MARKETS[args.market]]
        base_dir = Path(__file__).resolve().parent
        seeds = {market.code: load_seed_keywords(base_dir, market) for market in selected}
        if not args.key_file.is_file():
            raise FileNotFoundError(f"Service-account key not found: {args.key_file}")

        if args.dry_run:
            print("Configuration OK (dry run; Google Ads API was not called).")
            print(f"Customer: {customer_id}; manager: {login_customer_id}")
            for market in selected:
                print(f"{market.name}: {len(seeds[market.code])} unique seed keywords")
            return 0

        developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()
        if not developer_token:
            raise ValueError(
                "GOOGLE_ADS_DEVELOPER_TOKEN is not set. Set it for this terminal "
                "session; do not save the token in the repository."
            )

        credentials = service_account.Credentials.from_service_account_file(
            str(args.key_file), scopes=[ADWORDS_SCOPE]
        )
        session = AuthorizedSession(credentials)
        rows: list[dict[str, Any]] = []
        for market in selected:
            print(f"Fetching {market.name} keyword ideas...", file=sys.stderr)
            results = request_keyword_ideas(
                session,
                developer_token=developer_token,
                customer_id=customer_id,
                login_customer_id=login_customer_id,
                market=market,
                keywords=seeds[market.code],
            )
            rows.extend(normalize_result(market, item) for item in results)

        rows.sort(key=lambda row: (-row["avg_monthly_searches"], row["keyword"].casefold()))
        write_report(args.output, rows)
        print(f"Saved {len(rows)} rows to {args.output}")
        print("\nTop keywords by average monthly searches:")
        for row in rows[: max(args.top, 0)]:
            print(
                f"{row['avg_monthly_searches']:>10,}  "
                f"{row['market']:<20}  {row['keyword']}"
            )
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Keep unexpected errors concise and secret-safe.
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
