"""
Budget Bakers Wallet REST API client. Pulls the full record history and maps it
to the same columns as the Wallet CSV export, so `data.load()` stays the single
parser. Spec: https://rest.budgetbakers.com/wallet/openapi
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

from personal_finance_dashboard.data import TYPE_EXPENSE, TYPE_INCOME

BASE_URL = "https://rest.budgetbakers.com/wallet/v1/api"
TOKEN_ENV = "BUDGETBAKERS_WALLET_API"
PAGE_SIZE = 200  # API maximum
# Without a recordDate filter the API returns only the last 3 months.
HISTORY_START = "2000-01-01"


class WalletApiError(RuntimeError):
    """API call failed (auth, rate limit, initial sync in progress, network)."""


def read_token(env_path: Path = Path(".env")) -> str:
    """Returns the API token from the environment or from `.env`.

    Args:
        env_path: Fallback dotenv file with `BUDGETBAKERS_WALLET_API=...`.

    Raises:
        WalletApiError: Token not found.
    """
    token = os.environ.get(TOKEN_ENV)
    if not token and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == TOKEN_ENV:
                token = value.strip().strip("\"'")
    if not token:
        raise WalletApiError(f"Missing {TOKEN_ENV} in environment or {env_path}")
    return token


def _get(path: str, token: str) -> tuple[dict[str, Any], dict[str, str]]:
    """GET one endpoint; returns (JSON body, headers)."""
    req = urllib.request.Request(
        BASE_URL + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()), dict(resp.headers)
    except urllib.error.HTTPError as e:
        hints = {
            401: "invalid token",
            409: "initial data sync in progress, retry in a few minutes",
            429: f"rate limit, retry after {e.headers.get('Retry-After', '?')} s",
        }
        raise WalletApiError(f"HTTP {e.code} on {path}: {hints.get(e.code, e.reason)}") from e
    except urllib.error.URLError as e:
        raise WalletApiError(f"Network error on {path}: {e.reason}") from e


def fetch_records(token: str, since: str = HISTORY_START) -> tuple[list[dict[str, Any]], str]:
    """Fetches every record from `since`, oldest first, following `nextOffset`.

    Args:
        token: API bearer token.
        since: Lower bound for recordDate (YYYY-MM-DD).

    Returns:
        (records, value of the X-Last-Data-Change-At header).
    """
    records: list[dict[str, Any]] = []
    offset: int | None = 0
    last_change = ""
    while offset is not None:
        body, headers = _get(
            f"/records?recordDate=gte.{since}&sortBy=%2BrecordDate&convertTo=base"
            f"&limit={PAGE_SIZE}&offset={offset}",
            token,
        )
        records.extend(body.get("records", []))
        last_change = headers.get("X-Last-Data-Change-At", last_change)
        offset = body.get("nextOffset")
    return records, last_change


def records_to_frame(
    records: list[dict[str, Any]],
    category_names: dict[str, str] | None = None,
    excluded_accounts: frozenset[str] = frozenset(),
) -> pd.DataFrame:
    """Maps API records to the CSV export columns that `data.load()` reads.

    Args:
        records: Raw records from `fetch_records`.
        category_names: API (English) system category name -> export name
            (`api_en` in config/category_mapping.yaml). Unmapped names pass through.
        excluded_accounts: Names of accounts flagged `excludeFromStats` in Wallet.

    Returns:
        DataFrame with account, category, currency, amount, ref_currency_amount,
        type, payee, note, labels, date, transfer, exclude_from_stats.
    """
    names = category_names or {}
    rows = []
    for r in records:
        # The CSV export holds unsigned amounts (direction lives in `type`);
        # audit_transfers pairs legs on equal amounts, so keep it that way.
        amount = abs(float(r["amount"]["value"]))
        converted = r.get("convertedAmount") or {}
        category = (r.get("category") or {}).get("name", "")
        rows.append(
            {
                "account": r.get("accountName", ""),
                "category": names.get(category, category),
                "currency": r["amount"].get("currencyCode", ""),
                "amount": amount,
                "ref_currency_amount": abs(float(converted.get("value", amount))),
                "type": TYPE_INCOME if r.get("recordType") == "income" else TYPE_EXPENSE,
                "payee": r.get("counterParty", ""),
                "note": r.get("note", ""),
                "labels": "|".join(lbl.get("name", "") for lbl in r.get("labels") or []),
                "date": r["recordDate"],
                "transfer": "true" if r.get("transfer") else "false",
                "exclude_from_stats": "true"
                if r.get("accountName") in excluded_accounts
                else "false",
            }
        )
    return pd.DataFrame(rows)


def fetch_excluded_accounts(token: str) -> frozenset[str]:
    """Names of accounts with `excludeFromStats` set in Wallet."""
    body, _ = _get("/accounts?limit=200", token)
    return frozenset(a["name"] for a in body["accounts"] if a.get("excludeFromStats"))


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Writes the frame in the export format (`;`-separated), atomically.

    Args:
        df: Output of `records_to_frame`.
        path: Target CSV; replaced only after the full write succeeds.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, sep=";", index=False, encoding="utf-8")
    tmp.replace(path)


PPK_ACCOUNT = "PPK"
# System category IDs are deterministic across accounts ("Dues, grants" / "Interest, dividends").
PPK_CAT_CONTRIBUTION = "5c5c2714-0064-8000-8000-000000000000"
PPK_CAT_GAIN = "5c5c2711-0064-8000-8000-000000000000"
PPK_BATCH = 50  # API maximum records per POST


def _post(path: str, body: object, token: str) -> dict[str, Any]:
    """POST JSON to one endpoint; returns the JSON response."""
    req = urllib.request.Request(
        BASE_URL + path,
        json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result: dict[str, Any] = json.loads(resp.read())
            return result
    except urllib.error.HTTPError as e:
        raise WalletApiError(f"HTTP {e.code} on POST {path}: {e.read()[:300]!r}") from e
    except urllib.error.URLError as e:
        raise WalletApiError(f"Network error on POST {path}: {e.reason}") from e


def plan_ppk_update(
    ppk_file: Path, existing: list[dict[str, Any]], current_balance: float
) -> list[dict[str, Any]]:
    """Builds the PPK records that are missing in Wallet.

    New contributions are rows of the provider's history file whose
    (day, amount, note) is not yet on the account. A correction record then
    brings the balance to the file's latest "Wartość rachunku" (unit-price gains).

    Args:
        ppk_file: Provider export (.ods), newest row first.
        existing: Records already on the Wallet PPK account.
        current_balance: Current Wallet balance of the PPK account.

    Returns:
        Records without `accountId`, oldest first; empty when up to date.
    """
    df = pd.read_excel(ppk_file, engine="odf")
    ordered, valued, kind, _, amount, balance = (df.columns[i] for i in range(6))
    have = {
        (str(r["recordDate"])[:10], round(float(r["amount"]["value"]), 2), r.get("note", ""))
        for r in existing
    }
    new: list[dict[str, Any]] = []
    for _, row in df.iloc[::-1].iterrows():
        day = pd.to_datetime(row[ordered]).strftime("%Y-%m-%d")
        value = round(float(row[amount]), 2)
        if (day, value, str(row[kind])[:255]) not in have:
            new.append(
                {
                    "amount": {"value": value},
                    "categoryId": PPK_CAT_CONTRIBUTION,
                    "note": str(row[kind])[:255],
                    "recordDate": f"{day}T12:00:00Z",
                }
            )
    gain = round(
        float(df[balance].iloc[0]) - current_balance - sum(r["amount"]["value"] for r in new), 2
    )
    if abs(gain) >= 0.01:
        day = pd.to_datetime(df[valued]).max().strftime("%Y-%m-%d")
        new.append(
            {
                "amount": {"value": gain},
                "categoryId": PPK_CAT_GAIN,
                "note": "Korekta: zmiana wartości jednostek",
                "recordDate": f"{day}T12:00:00Z",
            }
        )
    return new


def push_ppk(token: str, records: list[dict[str, Any]], account_id: str) -> int:
    """Creates records on the PPK account in batches; returns how many succeeded."""
    done = 0
    for i in range(0, len(records), PPK_BATCH):
        batch = [{**r, "accountId": account_id} for r in records[i : i + PPK_BATCH]]
        done += _post("/records", batch, token)["summary"]["succeeded"]
    return done
