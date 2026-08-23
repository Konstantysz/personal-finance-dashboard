"""
CLI for the tool. The only place through which anyone - agent or human -
touches data/raw/*.csv. Each subcommand:

  1. writes a full report (.md) and charts (.png) to disk,
  2. prints a short JSON summary to stdout.

The agent reads stdout and does not load the entire report back into context.
Implemented: `validate`, `analyze`, `monthly`, `category`, `invest`, `taxes`, `goal`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from personal_finance_dashboard import data
from personal_finance_dashboard.charts import (
    plot_category,
    plot_goal,
    plot_monthly_flow,
    plot_top_categories,
)

app = typer.Typer(help="Personal finance analysis - CSV -> report + JSON.")

DEFAULT_CSV = Path("data/raw/wallet_export.csv")
DEFAULT_PROFILE = Path("config/profile.yaml")
DEFAULT_PARAMS = Path("config/parameters.yaml")
REPORTS_DIR = Path("output/reports")
CHARTS_DIR = Path("output/charts")


def _emit(summary: dict[str, Any]) -> None:
    """The only way to return a result to stdout: compact JSON, one line."""
    typer.echo(json.dumps(summary, ensure_ascii=False, default=str))


@app.command()
def validate(
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv", help="Path to the CSV export."),
) -> None:
    """
    Data quality check: coverage, accounts, transfers, anomalies.
    Does not calculate a budget. Equivalent of /validate.
    """
    if not csv_path.exists():
        _emit({"ok": False, "error": f"Missing file {csv_path}"})
        raise typer.Exit(code=1)

    df = data.load(csv_path)
    audit = data.audit_transfers(df)

    duplicates: pd.DataFrame = df[
        df.duplicated(subset=["date", "amount", "account", "category"], keep=False)
    ]
    large: pd.DataFrame = df[df["amount"].abs() > 20_000]
    missing_amount = int(df["amount"].isna().sum())

    per_month: pd.Series = df.groupby("month").size()
    median_count = float(per_month.median()) if not per_month.empty else 0.0
    sparse_months: pd.Series = per_month[per_month < 0.5 * median_count]

    accounts = (
        df.groupby("account")
        .agg(transakcje=("amount", "size"), pierwsza=("date", "min"), ostatnia=("date", "max"))
        .reset_index()
    )

    report_lines = [
        f"# Data validation - {date.today().isoformat()}",
        "",
        f"Range: {df['date'].min().date()} → {df['date'].max().date()}, {len(df)} transactions.",
        "",
        "## Accounts",
        accounts.to_markdown(index=False),
        "",
        "## Transfers",
        audit.summary(),
        "",
    ]
    if not audit.orphans.empty:
        report_lines += [
            "### Orphans (require user decision)",
            audit.orphans.to_markdown(index=False),
            "",
        ]
    if not audit.malformed.empty:
        report_lines += ["### Malformed pairs", audit.malformed.to_markdown(index=False), ""]
    if not duplicates.empty:
        report_lines += ["## Possible duplicates", duplicates.to_markdown(index=False), ""]
    if not large.empty:
        report_lines += ["## Transactions > 20,000 PLN", large.to_markdown(index=False), ""]
    if not sparse_months.empty:
        report_lines += [
            "## Months with suspiciously low transaction counts",
            sparse_months.to_markdown(),
            "",
        ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"validate_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    _emit(
        {
            "ok": True,
            "rows": len(df),
            "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
            "accounts": int(df["account"].nunique()),
            "transfer_pairs": len(audit.pairs),
            "transfer_orphans": len(audit.orphans),
            "transfer_malformed": len(audit.malformed),
            "duplicates": len(duplicates),
            "large_transactions": len(large),
            "missing_amount": missing_amount,
            "sparse_months": [str(m) for m in sparse_months.index],
            "report": str(report_path),
        }
    )


@app.command()
def analyze(
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv"),
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
    params_path: Path = typer.Option(DEFAULT_PARAMS, "--params"),
) -> None:
    """
    Full ACTIVE window analysis: flow, categories, fixed costs.
    Equivalent of /analysis.
    """
    if not csv_path.exists():
        _emit({"ok": False, "error": f"Missing file {csv_path}"})
        raise typer.Exit(code=1)
    if not profile_path.exists():
        _emit({"ok": False, "error": f"Missing {profile_path}. Run /profile."})
        raise typer.Exit(code=1)

    df = data.load(csv_path)
    profile = data.load_profile(profile_path)
    savings_accounts = profile.get("konta", {}).get("oszczednosciowe", [])

    windows = data.split_periods(df, profile)
    active = windows["active"]

    flow = data.monthly_flow(active, savings_accounts)
    flow_r = data.rolling_view(flow, window=3)
    fixed_costs = data.detect_fixed_costs(active)

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    flow_chart = plot_monthly_flow(flow, CHARTS_DIR / "przeplyw_miesieczny.png")

    exp = data.expenses(active)
    by_category = exp.groupby("category")["amount"].sum()
    cat_chart = plot_top_categories(by_category, CHARTS_DIR / "kategorie_top15.png")

    last_month = flow.index.max() if not flow.empty else None
    last_row = flow.loc[last_month] if last_month is not None else None

    params_check = data.check_parameters_freshness(params_path)

    report_lines = [
        f"# Analysis - ACTIVE window (from {profile['okresy']['regime_change_date']})",
        "",
        f"Months in window: {len(flow)}.",
        "",
        "## Monthly flow",
        flow.drop(columns=["stopa_oszczedzania"]).round(0).to_markdown(),
        "",
        "## Savings rate",
        flow[["stopa_oszczedzania"]]
        .mul(100)
        .round(1)
        .rename(columns={"stopa_oszczedzania": "stopa_oszczedzania_%"})
        .to_markdown(),
        "",
        "## Fixed costs (candidates, for approval)",
        fixed_costs.to_markdown(index=False) if not fixed_costs.empty else "None detected.",
        "",
        "## Top categories",
        by_category.sort_values(ascending=False).head(15).round(0).to_markdown(),
        "",
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"analysis_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    _emit(
        {
            "ok": True,
            "months_in_window": len(flow),
            "last_month": str(last_month) if last_month is not None else None,
            "last_month_balance": None if last_row is None else round(float(last_row["bilans"]), 0),
            "avg_balance": None if flow.empty else round(float(flow["bilans"].mean()), 0),
            "avg_balance_3m": None
            if flow_r["bilans_r3m"].dropna().empty
            else round(float(flow_r["bilans_r3m"].dropna().iloc[-1]), 0),
            "fixed_costs_candidates": len(fixed_costs),
            "params_stale": params_check["stale"],
            "params_age_days": params_check["age_days"],
            "report": str(report_path),
            "charts": [str(flow_chart), str(cat_chart)],
        }
    )


def _not_implemented(name: str, doc_command: str) -> None:
    _emit(
        {
            "ok": False,
            "error": f"`{name}` is not yet implemented in the CLI.",
            "see": "TODO.md",
            "workaround": f"The slash command {doc_command} still describes the target "
            "behavior and can be used as a specification during implementation.",
        }
    )
    raise typer.Exit(code=2)


def _build_monthly_report(
    trends: dict[str, Any],
) -> str:
    """Build one-page markdown report for monthly close analysis.

    Args:
        trends: Dict from data.monthly_trends().
        profile: User profile dict.

    Returns:
        Markdown report as string.
    """
    last_month = trends["last_month"]
    stats = trends["last_month_stats"]
    trends_data = trends["trends"]
    pct = trends["pct_change"]
    categories = trends["category_changes"]
    new_cats = trends["new_categories"]
    new_fixed = trends["new_fixed_costs"]

    report_lines = [
        f"# Monthly close — {last_month}",
        "",
        "## Last month balance",
        f"- Expenses: **{stats['wydatki']:.2f} PLN**",
        f"- Income: {stats['przychod']:.2f} PLN",
        f"- Savings: {stats['oszczednosci']:.2f} PLN",
        f"- Balance: **{stats['bilans']:.2f} PLN** "
        f"({'positive' if stats['bilans'] > 0 else 'negative'})",
        "",
        "## Trends (3M / 6M / 12M average)",
        f"- 3M average: {trends_data['wydatki_3m']} PLN "
        f"({pct.get('vs_3m', 0):+.1f}% vs last month)",
        f"- 6M average: {trends_data['wydatki_6m']} PLN ({pct.get('vs_6m', 0):+.1f}% vs last month)"
        if trends_data["wydatki_6m"]
        else "",
        f"- 12M average: {trends_data['wydatki_12m']} PLN "
        f"({pct.get('vs_12m', 0):+.1f}% vs last month)"
        if trends_data["wydatki_12m"]
        else "",
        "",
        "## Category changes (vs 3M average)",
    ]

    if categories["up"]:
        report_lines += ["**Largest increases:**"]
        for item in categories["up"]:
            report_lines.append(f"- {item['kategoria']}: +{item['zmiana']:.2f} PLN")
        report_lines.append("")

    if categories["down"]:
        report_lines += ["**Largest decreases:**"]
        for item in categories["down"]:
            report_lines.append(f"- {item['kategoria']}: {item['zmiana']:.2f} PLN")
        report_lines.append("")

    if new_cats:
        report_lines += [
            "## New categories",
            ", ".join(new_cats),
            "",
        ]

    if new_fixed:
        report_lines += [
            "## New fixed cost candidates",
            "⚠️ **Review and approve before using in budget planning.**",
        ]
        for fc in new_fixed:
            report_lines.append(
                f"- {fc['pozycja']}: {fc['mediana_miesieczna']} PLN "
                f"({fc['stabilnych']}/{fc['miesiecy']} months stable)"
            )
        report_lines.append("")

    # IKZE reminder for Nov/Dec
    today = date.today()
    if today.month in (11, 12):
        report_lines += [
            "## ⏰ IKZE deadline reminder",
            "**31 December deadline.** Contribute by end of year for tax deduction.",
            "",
        ]

    return "\n".join(line for line in report_lines if line is not None)


@app.command()
def monthly(
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv"),
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
) -> None:
    """
    Month close: last full month vs 3M/6M/12M trends.
    One-page report with category changes and goal progress.
    """
    if not csv_path.exists():
        _emit({"ok": False, "error": f"Missing file {csv_path}"})
        raise typer.Exit(code=1)
    if not profile_path.exists():
        _emit({"ok": False, "error": f"Missing {profile_path}. Run /profile."})
        raise typer.Exit(code=1)

    df = data.load(csv_path)
    profile = data.load_profile(profile_path)
    windows = data.split_periods(df, profile)
    active = windows["active"]

    if active.empty:
        _emit({"ok": False, "error": "No data in the ACTIVE window"})
        raise typer.Exit(code=1)

    trends = data.monthly_trends(active, profile.get("konta", {}).get("oszczednosciowe", []))
    report_text = _build_monthly_report(trends)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"miesiac_{trends['last_month']}.md"
    report_path.write_text(report_text, encoding="utf-8")

    _emit(
        {
            "ok": True,
            "last_month": trends["last_month"],
            "last_month_balance": trends["last_month_stats"]["bilans"],
            "pct_vs_3m": trends["pct_change"].get("vs_3m"),
            "pct_vs_12m": trends["pct_change"].get("vs_12m"),
            "top_3_up": trends["category_changes"]["up"],
            "top_3_down": trends["category_changes"]["down"],
            "new_categories": len(trends["new_categories"]),
            "new_fixed_costs": len(trends["new_fixed_costs"]),
            "report": str(report_path),
        }
    )


@app.command()
def category(
    name: str = typer.Argument(...),
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv"),
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
) -> None:
    """Deep dive into one ACTIVE expense category."""
    if not csv_path.exists() or not profile_path.exists():
        _emit({"ok": False, "error": "CSV and profile are required."})
        raise typer.Exit(code=1)
    df = data.load(csv_path)
    profile = data.load_profile(profile_path)
    windows = data.split_periods(df, profile)
    result = data.category_analysis(windows["active"], name)
    if result["category"] is None:
        _emit(
            {
                "ok": False,
                "error": "Category is missing or ambiguous.",
                "matches": result["matches"],
            }
        )
        raise typer.Exit(code=2)
    archive = data.category_analysis(windows["archive"], result["category"])
    chart = plot_category(
        result["monthly"], CHARTS_DIR / f"kategoria_{result['category']}.png", result["category"]
    )
    report_lines = [
        f"# Category: {result['category']}",
        "",
        "## ACTIVE",
        str(result["active"]),
        "",
        "## Top counterparties",
        pd.DataFrame(result["counterparties"]).to_markdown(index=False),
        "",
        "## Outliers",
        pd.DataFrame(result["outliers"]).to_markdown(index=False),
        "",
        "## ARCHIVE context",
        str(archive.get("active", {})),
        "",
    ]
    if any(
        word in result["category"].casefold()
        for word in ("miesz", "czynsz", "media", "spoż", "zakup")
    ):
        report_lines += ["This comparison may reflect a lifestyle change, not extravagance.", ""]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"kategoria_{result['category']}_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    _emit(
        {
            "ok": True,
            "category": result["category"],
            "active": result["active"],
            "report": str(report_path),
            "chart": str(chart),
        }
    )


@app.command()
def invest(
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv"),
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
    params_path: Path = typer.Option(DEFAULT_PARAMS, "--params"),
) -> None:
    """Create an investment plan from actual ACTIVE cash flow and balances."""
    if not csv_path.exists() or not profile_path.exists() or not params_path.exists():
        _emit({"ok": False, "error": "CSV, profile, and parameters are required."})
        raise typer.Exit(code=1)
    profile = data.load_profile(profile_path)
    freshness = data.check_parameters_freshness(params_path)
    if freshness["stale"]:
        _emit(
            {
                "ok": False,
                "error": "Parameters are stale; refresh parameters first.",
                "params": freshness,
            }
        )
        raise typer.Exit(code=1)
    params = data.load_profile(params_path)
    df = data.load(csv_path)
    active = data.split_periods(df, profile)["active"]
    flow = data.monthly_flow(active, profile.get("konta", {}).get("oszczednosciowe", []))
    surplus = float(flow["bilans"].mean()) if not flow.empty else 0.0
    balances = profile.get("konta", {}).get("salda_rzeczywiste", {}).get("wartosci", {})
    starting = sum(
        float(balances.get(account, 0))
        for account in profile.get("konta", {}).get("oszczednosciowe", [])
    )
    try:
        result = data.investment_plan(profile, params, surplus, starting)
    except ValueError as exc:
        _emit({"ok": False, "error": str(exc)})
        raise typer.Exit(code=1) from exc
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"inwestycje_{date.today().isoformat()}.md"
    report_path.write_text(
        "# Investment plan\n\n"
        + pd.Series(result).to_string()
        + "\n\nSimulation on assumptions, not investment advice.\n",
        encoding="utf-8",
    )
    _emit(
        {
            "ok": True,
            "monthly_contribution": result["monthly_contribution"],
            "investable_capital": result["investable_capital"],
            "params": freshness,
            "report": str(report_path),
        }
    )


@app.command()
def goal(
    name: str = typer.Argument(...),
    csv_path: Path = typer.Option(DEFAULT_CSV, "--csv"),
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
    params_path: Path = typer.Option(DEFAULT_PARAMS, "--params"),
) -> None:
    """Simulate a configured financial goal."""
    if not csv_path.exists() or not profile_path.exists() or not params_path.exists():
        _emit({"ok": False, "error": "CSV, profile, and parameters are required."})
        raise typer.Exit(code=1)
    profile = data.load_profile(profile_path)
    goals = profile.get("cele", {}).get("krotkoterminowe", []) + profile.get("cele", {}).get(
        "dlugoterminowe", []
    )
    found = next(
        (item for item in goals if item.get("nazwa", "").casefold() == name.casefold()), None
    )
    if not found or found.get("kwota") is None or found.get("termin") is None:
        _emit(
            {
                "ok": False,
                "error": "Unknown goal or missing amount/deadline.",
                "matches": [item.get("nazwa") for item in goals],
            }
        )
        raise typer.Exit(code=2)
    df = data.load(csv_path)
    windows = data.split_periods(df, profile)
    flow = data.monthly_flow(windows["active"], profile.get("konta", {}).get("oszczednosciowe", []))
    surplus = float(flow["bilans"].mean()) if not flow.empty else 0.0
    balances = profile.get("konta", {}).get("salda_rzeczywiste", {}).get("wartosci", {})
    current_capital = sum(
        float(balances.get(account, 0))
        for account in profile.get("konta", {}).get("oszczednosciowe", [])
    )
    params = data.load_profile(params_path)
    simulation = params.get("symulacje", {})
    archive_flow = data.monthly_flow(
        windows["archive"], profile.get("konta", {}).get("oszczednosciowe", [])
    )
    factors = (
        (archive_flow["bilans"] / archive_flow["bilans"].mean()).dropna().tolist()
        if not archive_flow.empty and archive_flow["bilans"].mean()
        else [1.0]
    )
    result = data.goal_simulation(
        float(found["kwota"]),
        pd.Period(found["termin"], freq="M"),
        current_capital,
        surplus,
        {
            "conservative": simulation.get("scenariusz_ostrozny", {}).get(
                "akcje_globalne_nominalnie", 0
            ),
            "base": simulation.get("scenariusz_bazowy", {}).get("akcje_globalne_nominalnie", 0),
        },
        factors,
    )
    chart = plot_goal(result["scenarios"], result["target"], CHARTS_DIR / f"goal_{name}.png")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"goal_{name}_{date.today().isoformat()}.md"
    report_path.write_text(
        "# Goal simulation\n\n"
        + pd.Series({k: v for k, v in result.items() if k != "scenarios"}).to_string(),
        encoding="utf-8",
    )
    _emit(
        {
            "ok": True,
            "goal": name,
            "required_monthly_contribution": result["required_monthly_contribution"],
            "reachable": result["reachable"],
            "report": str(report_path),
            "chart": str(chart),
        }
    )


@app.command()
def taxes(
    profile_path: Path = typer.Option(DEFAULT_PROFILE, "--profile"),
    params_path: Path = typer.Option(DEFAULT_PARAMS, "--params"),
) -> None:
    """Calculate current-year IKE and IKZE room."""
    if not profile_path.exists() or not params_path.exists():
        _emit({"ok": False, "error": "Profile and parameters are required."})
        raise typer.Exit(code=1)
    try:
        result = data.tax_calculation(
            data.load_profile(profile_path), data.load_profile(params_path)
        )
    except ValueError as exc:
        _emit({"ok": False, "error": str(exc)})
        raise typer.Exit(code=1) from exc
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"taxes_{result['year']}.md"
    report_path.write_text(
        "# Taxes\n\n" + pd.Series(result).to_string() + "\n\nThis is not tax advice.\n",
        encoding="utf-8",
    )
    _emit({"ok": True, **result, "report": str(report_path)})


if __name__ == "__main__":
    app()
