"""
Single source of truth for loading and cleaning transaction data.

`cli.py` imports from here and is the only allowed place that calls these
functions on raw CSV. The agent (Claude Code) does not read data/raw/*.csv
directly - see CLAUDE.md and .claude/settings.json (blocking hook).
Do not duplicate transfer logic or period division anywhere else - three
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
# Basic filters - use THESE, not your own conditions
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
            "- don't guess by account names."
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
    for seasonality, basket inflation, and history - not for average expenses.
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

    # Fill missing months with zeros - otherwise "category appeared from zero"
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


_FIXED_COST_STABILITY_RATIO = 0.6


def detect_fixed_costs(
    df: pd.DataFrame,
    min_months: int = 3,
    tolerance: float = 0.20,
    stability_ratio: float = _FIXED_COST_STABILITY_RATIO,
) -> pd.DataFrame:
    """
    Fixed cost candidates: same (category, payee) in >= min_months
    consecutive months, amount within +/- tolerance around the median.

    This is a HEURISTIC. Show the result to the user for approval - do not
    treat it as an established fact.

    Args:
        df: Transactions DataFrame.
        min_months: Minimum consecutive months to consider.
        tolerance: Allowed variance around median as fraction (0.20 = ±20%).
        stability_ratio: Minimum ratio of stable months to total months (0.6 = 60%).
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
        if within >= min_months and within / len(per_month) >= stability_ratio:
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
# Market parameters - freshness
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


def monthly_flow(
    df: pd.DataFrame,
    savings_accounts: list[str],
    today: pd.Timestamp | None = None,
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    """Income / expenses / savings / balance, month by month.

    By default the current, unfinished month is excluded. Income is concentrated
    on payday (`osoba.dzien_wyplaty` in the profile) while expenses accrue daily,
    so a month analyzed before payday shows spending without the matching income
    and drags every average and trend downwards.

    Args:
        df: Parsed transactions, as returned by `load`.
        savings_accounts: Account names treated as savings.
        today: Reference date deciding which month is still running. Defaults to
            the current date.
        drop_incomplete: When False, keep the running month. Use only when the
            partial month is explicitly what is being asked about.

    Returns:
        DataFrame indexed by month with income, expenses, savings, balance and
        savings rate.
    """
    inc = income(df).groupby("month")["amount"].sum()
    exp = expenses(df).groupby("month")["amount"].sum()
    sav = savings(df, savings_accounts).groupby("month")["amount"].sum()

    out = pd.DataFrame({"przychod": inc, "wydatki": exp, "oszczednosci": sav})
    out = out.fillna(0.0)
    out["bilans"] = out["przychod"] - out["wydatki"] - out["oszczednosci"]
    out["stopa_oszczedzania"] = out["oszczednosci"] / out["przychod"].replace(0, pd.NA)

    if drop_incomplete and not out.empty:
        ref = today or pd.Timestamp.now()
        out = out.drop(index=ref.to_period("M"), errors="ignore")

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


def monthly_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Expense statistics by category: mean, min, max, stdev, share %.

    Returns: (DataFrame with categories, dict with overall statistics).
    """
    exp = expenses(df).copy()
    if exp.empty:
        return pd.DataFrame(
            columns=["kategoria", "srednia", "min", "max", "stdev", "miesiece", "udzial_%"]
        ), {
            "srednia_wydatki": 0.0,
            "min_miesiace": 0.0,
            "max_miesiace": 0.0,
            "stdev_miesiace": 0.0,
            "liczba_miesiecy": 0,
        }

    monthly_total = exp.groupby("month")["amount"].sum()
    if monthly_total.empty:
        return pd.DataFrame(
            columns=["kategoria", "srednia", "min", "max", "stdev", "miesiece", "udzial_%"]
        ), {
            "srednia_wydatki": 0.0,
            "min_miesiace": 0.0,
            "max_miesiace": 0.0,
            "stdev_miesiace": 0.0,
            "liczba_miesiecy": 0,
        }

    total_expenses = exp["amount"].sum()
    num_months = len(monthly_total)

    categories = []
    for cat, g in exp.groupby("category"):
        monthly_cat = g.groupby("month")["amount"].sum()
        avg = monthly_cat.mean()
        categories.append(
            {
                "kategoria": cat,
                "srednia": round(avg, 2),
                "min": round(monthly_cat.min(), 2),
                "max": round(monthly_cat.max(), 2),
                "stdev": round(monthly_cat.std(), 2),
                "miesiece": len(monthly_cat),
                "udzial_%": round(100.0 * g["amount"].sum() / total_expenses, 2),
            }
        )

    df_summary = pd.DataFrame(categories).sort_values("srednia", ascending=False)

    overall = {
        "srednia_wydatki": round(monthly_total.mean(), 2),
        "min_miesiace": round(monthly_total.min(), 2),
        "max_miesiace": round(monthly_total.max(), 2),
        "stdev_miesiace": round(monthly_total.std(), 2),
        "liczba_miesiecy": num_months,
    }

    return df_summary, overall


def category_analysis(df: pd.DataFrame, name: str) -> dict[str, Any]:
    """Analyze one expense category, or return matching category names."""
    categories = sorted(expenses(df)["category"].dropna().unique().tolist())
    matches = [category for category in categories if name.casefold() in category.casefold()]
    exact = [category for category in matches if category.casefold() == name.casefold()]
    if len(exact) == 1:
        matches = exact
    if len(matches) != 1:
        return {"category": None, "matches": matches, "ambiguous": bool(matches)}

    category = matches[0]
    selected = expenses(df)[expenses(df)["category"] == category].copy()
    monthly = selected.groupby("month")["amount"].sum().sort_index()
    mean = float(selected["amount"].mean()) if not selected.empty else 0.0
    stdev = float(selected["amount"].std()) if len(selected) > 1 else 0.0
    threshold = mean + 2 * stdev
    outliers = selected[selected["amount"] > threshold]
    payee = (
        selected.groupby("payee", dropna=False)
        .agg(suma=("amount", "sum"), transakcje=("amount", "size"))
        .reset_index()
    )
    payee = payee.sort_values("suma", ascending=False).head(10)
    return {
        "category": category,
        "matches": matches,
        "ambiguous": False,
        "active": {
            "sum": float(selected["amount"].sum()),
            "monthly_average": float(monthly.mean()) if not monthly.empty else 0.0,
            "median": float(selected["amount"].median()) if not selected.empty else 0.0,
            "stdev": stdev,
            "months": len(monthly),
        },
        "monthly": monthly,
        "rolling_3m": monthly.rolling(3).mean(),
        "counterparties": payee.to_dict("records"),
        "by_weekday": selected.groupby(selected["date"].dt.day_name()).size().to_dict(),
        "outliers": outliers[["date", "amount", "note"]].to_dict("records"),
    }


def investment_plan(
    profile: dict[str, Any],
    params: dict[str, Any],
    monthly_surplus: float,
    starting_capital: float,
) -> dict[str, Any]:
    """Build an assumption-driven investment allocation and projections."""
    if monthly_surplus < 0:
        raise ValueError("Monthly surplus is negative; resolve cash flow before investing.")
    emergency = profile.get("stan_wdrozenia", {}).get("poduszka_finansowa_kwota")
    if emergency is None:
        raise ValueError("Fill in stan_wdrozenia.poduszka_finansowa_kwota first.")
    tax = float(params.get("podatki", {}).get("belka", 0.19))
    retirement = params.get("konta_emerytalne", {})
    form = profile.get("osoba", {}).get("forma_zatrudnienia")
    ikze_key = "limit_jdg" if form == "jdg" else "limit_etat"
    scenarios = params.get("symulacje", {})
    conservative = scenarios.get("scenariusz_ostrozny", {})
    base = scenarios.get("scenariusz_bazowy", {})
    investable_capital = max(0.0, starting_capital - float(emergency))
    return {
        "emergency_fund": float(emergency),
        "starting_capital": float(starting_capital),
        "investable_capital": investable_capital,
        "monthly_contribution": float(monthly_surplus),
        "ike_limit": float(retirement.get("ike", {}).get("limit", 0)),
        "ikze_limit": float(retirement.get("ikze", {}).get(ikze_key, 0)),
        "bond_return_net": float(base.get("obligacje_edo", 0.0)) * (1 - tax),
        "allocation": {"emergency_fund": float(emergency), "goals": investable_capital},
        "scenarios": {
            "conservative": {
                "equity_return": float(conservative.get("akcje_globalne_nominalnie", 0))
            },
            "base": {"equity_return": float(base.get("akcje_globalne_nominalnie", 0))},
        },
        "contribution_drop_30_percent": float(monthly_surplus * 0.7),
    }


def goal_simulation(
    target: float,
    deadline: pd.Period,
    current_capital: float,
    monthly_surplus: float,
    returns: dict[str, float],
    seasonal_factors: list[float] | None = None,
    current_month: pd.Period | None = None,
) -> dict[str, Any]:
    """Simulate required contributions and three goal accumulation scenarios."""
    current = current_month or pd.Timestamp.now().to_period("M")
    months = max(0, (deadline.year - current.year) * 12 + deadline.month - current.month)
    seasonality = sum(seasonal_factors or [1.0]) / len(seasonal_factors or [1.0])
    effective_contribution = monthly_surplus * seasonality
    scenarios: dict[str, list[float]] = {}
    for label, annual_return in returns.items():
        monthly_return = (1 + annual_return) ** (1 / 12) - 1
        values = [float(current_capital)]
        for _ in range(months):
            values.append(values[-1] * (1 + monthly_return) + effective_contribution)
        scenarios[label] = values
    event = scenarios.get("base", [float(current_capital)]).copy()
    for index in range(min(3, max(0, len(event) - 1))):
        event[index + 1] = event[index]
    scenarios["random_event"] = event
    rate = (1 + returns.get("base", 0.0)) ** (1 / 12) - 1
    required = (
        target / months
        if months and rate == 0
        else (
            (target - current_capital * (1 + rate) ** months) * rate / ((1 + rate) ** months - 1)
            if months
            else max(0.0, target - current_capital)
        )
    )
    return {
        "target": float(target),
        "months": months,
        "required_monthly_contribution": max(0.0, float(required)) / max(seasonality, 1e-9),
        "monthly_surplus": float(monthly_surplus),
        "seasonality_factor": seasonality,
        "annual_savings_difference": float(monthly_surplus * 12 * (1 - seasonality)),
        "scenarios": scenarios,
        "reachable": (not scenarios["base"] or scenarios["base"][-1] >= target),
    }


def monthly_trends(
    df: pd.DataFrame, savings_accounts: list[str], target_month: pd.Period | str | None = None
) -> dict[str, Any]:
    """
    Analyze a full month: compare with 3M/6M/12M averages.

    Args:
        df: Transactions DataFrame.
        savings_accounts: List of savings account names.
        target_month: Month to analyze (default: last full month). Period or YYYY-MM string.

    Returns dict with:
    - last_month: Period of analyzed month
    - last_month_stats: expenses, income, savings, balance for analyzed month
    - trends: 3M, 6M, 12M average expenses
    - pct_change: % change vs 3M/6M/12M averages
    - category_changes: top 3 up/down by change vs 3M avg
    - all_categories_breakdown: all categories with amount, %share, vs prev month, vs 3M/6M/12M
    - new_categories: categories that appeared in analyzed month but not before
    - new_fixed_costs: fixed costs candidates from analyzed month
    - fixed_costs_total: sum of estimated fixed costs (from all_fixed)
    """
    if df.empty:
        raise ValueError("No data to analyze")

    flow = monthly_flow(df, savings_accounts)
    if flow.empty:
        raise ValueError("No monthly flow data")

    # Determine target month
    if target_month is None:
        last_month = flow.index.max()
    else:
        if isinstance(target_month, str):
            target_month = pd.Period(target_month, freq="M")
        if target_month not in flow.index:
            raise ValueError(
                f"Month {target_month} not in data range {flow.index.min()} - {flow.index.max()}"
            )
        last_month = target_month

    last_month_data = flow.loc[last_month]

    # Trends: 3M, 6M, 12M averages
    trend_3m = flow.iloc[-3:]["wydatki"].mean() if len(flow) >= 3 else None
    trend_6m = flow.iloc[-6:]["wydatki"].mean() if len(flow) >= 6 else None
    trend_12m = flow.iloc[-12:]["wydatki"].mean() if len(flow) >= 12 else None

    last_expenses = float(last_month_data["wydatki"])
    pct_change = {}
    if trend_3m:
        pct_change["vs_3m"] = ((last_expenses - trend_3m) / trend_3m * 100) if trend_3m > 0 else 0.0
    if trend_6m:
        pct_change["vs_6m"] = ((last_expenses - trend_6m) / trend_6m * 100) if trend_6m > 0 else 0.0
    if trend_12m:
        pct_change["vs_12m"] = (
            ((last_expenses - trend_12m) / trend_12m * 100) if trend_12m > 0 else 0.0
        )

    # Category analysis
    exp = expenses(df)
    all_categories_breakdown = []

    if not exp.empty:
        last_month_categories = (
            exp[exp["month"] == last_month]
            .groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
        )

        # Previous month for comparison
        prev_month = None
        for idx, m in enumerate(flow.index):
            if m == last_month and idx > 0:
                prev_month = flow.index[idx - 1]
                break

        prev_month_categories = (
            exp[exp["month"] == prev_month].groupby("category")["amount"].sum()
            if prev_month
            else pd.Series()
        )

        # 3M average by category
        months_3m = flow.index[-3:] if len(flow) >= 3 else flow.index
        avg_3m_categories = exp[exp["month"].isin(months_3m)].groupby("category")[
            "amount"
        ].sum() / len(months_3m)

        # 6M average by category
        months_6m = flow.index[-6:] if len(flow) >= 6 else flow.index
        avg_6m_categories = (
            exp[exp["month"].isin(months_6m)].groupby("category")["amount"].sum() / len(months_6m)
            if len(months_6m) > 0
            else pd.Series()
        )

        # 12M average by category
        months_12m = flow.index[-12:] if len(flow) >= 12 else flow.index
        avg_12m_categories = (
            exp[exp["month"].isin(months_12m)].groupby("category")["amount"].sum() / len(months_12m)
            if len(months_12m) > 0
            else pd.Series()
        )

        # Build full breakdown for all categories
        all_categories = set(last_month_categories.index) | set(avg_3m_categories.index)
        category_changes = {}

        for cat in all_categories:
            last = float(last_month_categories.get(cat, 0.0))
            avg_3m = float(avg_3m_categories.get(cat, 0.0))
            avg_6m = float(avg_6m_categories.get(cat, 0.0)) if not avg_6m_categories.empty else None
            avg_12m = (
                float(avg_12m_categories.get(cat, 0.0)) if not avg_12m_categories.empty else None
            )
            prev = (
                float(prev_month_categories.get(cat, 0.0))
                if not prev_month_categories.empty
                else None
            )

            change_3m = last - avg_3m
            pct_prev = ((last - prev) / prev * 100) if prev and prev > 0 else None
            pct_3m = ((last - avg_3m) / avg_3m * 100) if avg_3m > 0 else None
            pct_6m = ((last - avg_6m) / avg_6m * 100) if avg_6m and avg_6m > 0 else None
            pct_12m = ((last - avg_12m) / avg_12m * 100) if avg_12m and avg_12m > 0 else None

            pct_wydatkow = round(last / last_expenses * 100, 1) if last_expenses > 0 else 0.0

            all_categories_breakdown.append(
                {
                    "kategoria": cat,
                    "kwota": round(last, 2),
                    "procent_wydatkow": pct_wydatkow,
                    "vs_poprzedni": round(pct_prev, 1) if pct_prev is not None else None,
                    "vs_3m_srednia": round(pct_3m, 1) if pct_3m is not None else None,
                    "vs_6m_srednia": round(pct_6m, 1) if pct_6m is not None else None,
                    "vs_12m_srednia": round(pct_12m, 1) if pct_12m is not None else None,
                }
            )
            category_changes[cat] = change_3m

        # Sort by amount
        all_categories_breakdown.sort(key=lambda x: x["kwota"], reverse=True)

        # Top 3 changes
        changes_sorted = sorted(category_changes.items(), key=lambda x: x[1], reverse=True)
        top_3_up = changes_sorted[:3]
        top_3_down = changes_sorted[-3:]
        top_3_down.reverse()
    else:
        top_3_up = []
        top_3_down = []

    # New categories in last month
    if not exp.empty:
        last_month_cats = set(exp[exp["month"] == last_month]["category"].unique())
        prev_months_cats = set(exp[exp["month"] < last_month]["category"].unique())
        new_categories = sorted(last_month_cats - prev_months_cats)
    else:
        new_categories = []

    # Fixed costs: check if any new ones appeared
    all_fixed = detect_fixed_costs(df)
    new_fixed = (
        all_fixed[all_fixed["ostatni_miesiac"] == str(last_month)]
        if not all_fixed.empty
        else pd.DataFrame()
    )

    # Sum of all fixed costs (estimated)
    fixed_costs_total = float(all_fixed["mediana_miesieczna"].sum()) if not all_fixed.empty else 0.0

    return {
        "last_month": str(last_month),
        "last_month_stats": {
            "wydatki": round(float(last_month_data["wydatki"]), 2),
            "przychod": round(float(last_month_data["przychod"]), 2),
            "oszczednosci": round(float(last_month_data["oszczednosci"]), 2),
            "bilans": round(float(last_month_data["bilans"]), 2),
        },
        "trends": {
            "wydatki_3m": round(trend_3m, 2) if trend_3m else None,
            "wydatki_6m": round(trend_6m, 2) if trend_6m else None,
            "wydatki_12m": round(trend_12m, 2) if trend_12m else None,
        },
        "pct_change": {k: round(v, 1) for k, v in pct_change.items()},
        "category_changes": {
            "up": [{"kategoria": cat, "zmiana": round(change, 2)} for cat, change in top_3_up],
            "down": [{"kategoria": cat, "zmiana": round(change, 2)} for cat, change in top_3_down],
        },
        "all_categories_breakdown": all_categories_breakdown,
        "new_categories": new_categories,
        "new_fixed_costs": (
            [dict(row) for _, row in new_fixed.iterrows()] if not new_fixed.empty else []
        ),
        "fixed_costs_total": round(fixed_costs_total, 2),
    }


def tax_calculation(
    profile: dict[str, Any], params: dict[str, Any], today: pd.Timestamp | None = None
) -> dict[str, Any]:
    """Calculate current-year IKE/IKZE room and the IKZE deduction."""
    person = profile.get("osoba", {})
    form = person.get("forma_zatrudnienia")
    bracket = person.get("prog_podatkowy")
    if form not in {"etat", "jdg"}:
        raise ValueError("Fill in osoba.forma_zatrudnienia first.")
    if bracket not in {12, 32}:
        raise ValueError("Fill in osoba.prog_podatkowy first.")
    state = profile.get("stan_wdrozenia", {})
    ike_paid = state.get("ike_wplacone_w_tym_roku")
    ikze_paid = state.get("ikze_wplacone_w_tym_roku")
    if ike_paid is None or ikze_paid is None:
        raise ValueError("Fill in this year's IKE and IKZE contributions first.")
    retirement = params.get("konta_emerytalne", {})
    ikze = retirement.get("ikze", {})
    limits = {
        "ike": float(retirement.get("ike", {}).get("limit", 0)),
        "ikze": float(ikze.get("limit_jdg" if form == "jdg" else "limit_etat", 0)),
    }
    current = (today or pd.Timestamp.now()).date()
    year_end = pd.Timestamp(year=current.year, month=12, day=31).date()
    return {
        "year": current.year,
        "days_to_year_end": (year_end - current).days,
        "ike_remaining": max(0.0, limits["ike"] - float(ike_paid)),
        "ikze_remaining": max(0.0, limits["ikze"] - float(ikze_paid)),
        "ikze_deduction_at_limit": max(0.0, limits["ikze"] - float(ikze_paid)) * bracket / 100,
        "limits": limits,
        "bonds_tax_free_outside_wrappers": False,
    }
