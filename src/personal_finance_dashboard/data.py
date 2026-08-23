"""
Single source of truth for loading and cleaning transaction data.

`cli.py` imports from here and is the only allowed place that calls these
functions on raw CSV. The agent (Claude Code) does not read data/raw/*.csv
directly — see CLAUDE.md and .claude/settings.json (blocking hook).
Do not duplicate transfer logic or period division anywhere else — three
errors in the previous (manual) analysis came exactly from the fact that
rules were being rewritten ad hoc for each question.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

TYPE_INCOME = "Przychód"
TYPE_EXPENSE = "Wydatek"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load(csv_path: str | Path) -> pd.DataFrame:
    """Loads the Wallet export and normalizes types. Does not filter anything."""
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8", dtype=str)

    required = {"account", "category", "amount", "type", "date", "transfer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ".", regex=False), errors="coerce")
    if "ref_currency_amount" in df.columns:
        df["ref_amount"] = pd.to_numeric(
            df["ref_currency_amount"].str.replace(",", ".", regex=False),
            errors="coerce",
        )
    else:
        df["ref_amount"] = df["amount"]

    df["date"] = pd.to_datetime(df["date"], format="ISO8601", utc=True)
    # Wallet saves in UTC; convert to local time, because pay cycles
    # and month boundaries are calculated in Warsaw time.
    df["date"] = df["date"].dt.tz_convert("Europe/Warsaw").dt.tz_localize(None)

    df["transfer"] = df["transfer"].astype(str).str.strip().str.lower() == "true"
    df["type"] = df["type"].astype(str).str.strip()

    for col in ("account", "category", "payee", "note", "labels", "payment_type"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["month"] = df["date"].dt.to_period("M")
    return df.sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------
# Transfers
# --------------------------------------------------------------------------


@dataclass
class TransferAudit:
    """Result of matching transfer pairs. Always show orphans to the user."""

    pairs: pd.DataFrame = field(default_factory=pd.DataFrame)
    orphans: pd.DataFrame = field(default_factory=pd.DataFrame)
    malformed: pd.DataFrame = field(default_factory=pd.DataFrame)

    def summary(self) -> str:
        return (
            f"Transfer pairs: {len(self.pairs)}. "
            f"Orphans: {len(self.orphans)}. "
            f"Malformed pairs (both sides of the same type): {len(self.malformed)}."
        )


def audit_transfers(df: pd.DataFrame) -> TransferAudit:
    """
    Matches transfers into pairs by key (date, amount).

    A correct pair: exactly 2 records, one Expense + one Income.
    Anything else requires a user decision.
    """
    t = df[df["transfer"]].copy()
    if t.empty:
        return TransferAudit()

    grouped = t.groupby(["date", "amount"], sort=False)

    pair_rows, orphan_rows, malformed_rows = [], [], []
    for (dt, amt), g in grouped:
        if len(g) == 1:
            orphan_rows.append(g)
        elif len(g) == 2 and set(g["type"]) == {TYPE_INCOME, TYPE_EXPENSE}:
            src = g[g["type"] == TYPE_EXPENSE].iloc[0]
            dst = g[g["type"] == TYPE_INCOME].iloc[0]
            pair_rows.append(
                {
                    "date": dt,
                    "amount": amt,
                    "from_account": src["account"],
                    "to_account": dst["account"],
                    "note": dst.get("note", ""),
                }
            )
        else:
            malformed_rows.append(g)

    return TransferAudit(
        pairs=pd.DataFrame(pair_rows),
        orphans=pd.concat(orphan_rows) if orphan_rows else pd.DataFrame(),
        malformed=pd.concat(malformed_rows) if malformed_rows else pd.DataFrame(),
    )


# --------------------------------------------------------------------------
# Basic filters — use THESE, not your own conditions
# --------------------------------------------------------------------------


def income(df: pd.DataFrame) -> pd.DataFrame:
    """Actual income: transfers are NOT income."""
    return df[(df["type"] == TYPE_INCOME) & (~df["transfer"])]


def expenses(df: pd.DataFrame) -> pd.DataFrame:
    """Actual expenses: transfers are NOT expenses."""
    return df[(df["type"] == TYPE_EXPENSE) & (~df["transfer"])]


def savings(df: pd.DataFrame, savings_accounts: list[str]) -> pd.DataFrame:
    """
    Savings = only the incoming side of a transfer to an account
    marked in the profile as savings.

    Counting both sides of the pair doubles the amount. Counting all transfers
    drags in PKO -> Revolut moves, which are not savings.
    """
    if not savings_accounts:
        raise ValueError(
            "The list of savings accounts is empty. Fill in config/profile.yaml "
            "— don't guess by account names."
        )
    return df[df["transfer"] & (df["type"] == TYPE_INCOME) & (df["account"].isin(savings_accounts))]


# --------------------------------------------------------------------------
# Period division
# --------------------------------------------------------------------------


def load_profile(path: str | Path = "config/profile.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}. Run /profil before starting analysis.")
    with p.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def split_periods(df: pd.DataFrame, profile: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Returns windows: archive / active / recent / all.

    ACTIVE is the default window for EVERY budget analysis. ARCHIVE serves only
    for seasonality, basket inflation, and history — not for average expenses.
    """
    change = pd.Timestamp(profile["okresy"]["regime_change_date"])

    active = df[df["date"] >= change]
    archive = df[df["date"] < change]

    if active.empty:
        recent = active
    else:
        last_full = active["month"].max() - 1
        recent = active[active["month"] > (last_full - 3)]

    return {"all": df, "archive": archive, "active": active, "recent": recent}


def detect_regime_change(
    df: pd.DataFrame, keywords: list[str] | None = None
) -> tuple[pd.Period | None, pd.Series]:
    """
    Looks for a step change in the level of housing-related categories.
    The result is a PROPOSAL for user confirmation, not a determination.
    """
    keywords = keywords or [
        "czynsz",
        "mieszkan",
        "media",
        "prąd",
        "prad",
        "internet",
        "gaz",
        "woda",
        "wynajem",
    ]
    exp = expenses(df).copy()
    mask = exp["category"].str.lower().str.contains("|".join(keywords), na=False)
    housing = exp[mask]
    if housing.empty:
        return None, pd.Series(dtype=float)

    # Fill missing months with zeros — otherwise "category appeared from zero"
    # is indistinguishable from "category existed all along".
    monthly = housing.groupby("month")["amount"].sum()
    full_idx = pd.period_range(df["month"].min(), df["month"].max(), freq="M")
    monthly = monthly.reindex(full_idx, fill_value=0.0)

    # Case 1: the category simply appears and doesn't disappear.
    # Then the first non-zero month IS the regime change date.
    nonzero = monthly[monthly > 0]
    if not nonzero.empty:
        first = nonzero.index[0]
        before = monthly[monthly.index < first]
        after = monthly[monthly.index >= first]
        if len(before) >= 3 and (before == 0).all() and (after > 0).mean() >= 0.8:
            return first, monthly

    # Case 2: level jump. Look for a split that maximizes the difference in
    # medians, requiring >=3 months on both sides.
    best: pd.Period | None = None
    best_ratio = 0.0
    for i in range(3, len(monthly) - 2):
        b, a = monthly.iloc[:i], monthly.iloc[i:]
        if b.median() <= 0:
            continue
        ratio = a.median() / b.median()
        if ratio > best_ratio and ratio > 1.8:
            best, best_ratio = monthly.index[i], ratio

    fallback: pd.Period = monthly.idxmax()  # type: ignore[assignment]
    return (best or fallback), monthly


# --------------------------------------------------------------------------
# Fixed costs
# --------------------------------------------------------------------------


def detect_fixed_costs(
    df: pd.DataFrame, min_months: int = 3, tolerance: float = 0.20
) -> pd.DataFrame:
    """
    Fixed cost candidates: same (category, payee) in >= min_months
    consecutive months, amount within +/- tolerance around the median.

    This is a HEURISTIC. Show the result to the user for approval — do not
    treat it as an established fact.
    """
    exp = expenses(df).copy()
    exp["key"] = exp["category"] + " | " + exp.get("payee", "")

    out = []
    for key, g in exp.groupby("key"):
        per_month = g.groupby("month")["amount"].sum()
        if len(per_month) < min_months:
            continue
        med = per_month.median()
        if med <= 0:
            continue
        within = ((per_month - med).abs() <= tolerance * med).sum()
        if within >= min_months and within / len(per_month) >= 0.6:
            out.append(
                {
                    "pozycja": key,
                    "mediana_miesieczna": round(med, 2),
                    "miesiecy": len(per_month),
                    "stabilnych": int(within),
                    "ostatni_miesiac": str(per_month.index.max()),
                }
            )

    columns = ["pozycja", "mediana_miesieczna", "miesiecy", "stabilnych", "ostatni_miesiac"]
    if not out:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(out, columns=columns)
        .sort_values("mediana_miesieczna", ascending=False)
        .reset_index(drop=True)
    )


# --------------------------------------------------------------------------
# Market parameters — freshness
# --------------------------------------------------------------------------


def check_parameters_freshness(
    path: str | Path = "config/parameters.yaml", max_age_days: int = 60
) -> dict[str, Any]:
    """Returns whether config/parameters.yaml is older than max_age_days."""
    import datetime as _dt

    p = Path(path)
    if not p.exists():
        return {"exists": False, "stale": True, "age_days": None}

    with p.open(encoding="utf-8") as f:
        params: dict[str, Any] = yaml.safe_load(f)

    last_verified = params.get("last_verified")
    if last_verified is None:
        return {"exists": True, "stale": True, "age_days": None}

    verified_date = pd.Timestamp(last_verified).date()
    age_days = (_dt.date.today() - verified_date).days
    return {"exists": True, "stale": age_days > max_age_days, "age_days": age_days}


# --------------------------------------------------------------------------
# Monthly summary
# --------------------------------------------------------------------------


def monthly_flow(df: pd.DataFrame, savings_accounts: list[str]) -> pd.DataFrame:
    """Income / expenses / savings / balance, month by month."""
    inc = income(df).groupby("month")["amount"].sum()
    exp = expenses(df).groupby("month")["amount"].sum()
    sav = savings(df, savings_accounts).groupby("month")["amount"].sum()

    out = pd.DataFrame({"przychod": inc, "wydatki": exp, "oszczednosci": sav})
    out = out.fillna(0.0)
    out["bilans"] = out["przychod"] - out["wydatki"] - out["oszczednosci"]
    out["stopa_oszczedzania"] = out["oszczednosci"] / out["przychod"].replace(0, pd.NA)
    return out


def rolling_view(flow: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Rolling + last month separately.

    Reason: the average over the whole period can show a deficit at a moment
    when the last month is already positive. Always report both numbers.
    """
    r = flow[["przychod", "wydatki", "oszczednosci", "bilans"]].rolling(window).mean()
    r.columns = [f"{c}_r{window}m" for c in r.columns]
    return flow.join(r)
