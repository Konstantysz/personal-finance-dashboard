"""
CLI for the tool. The only place through which anyone — agent or human —
touches data/raw/*.csv. Each subcommand:

  1. writes a full report (.md) and charts (.png) to disk,
  2. prints a short JSON summary to stdout.

The agent reads stdout and does not load the entire report back into context.
Implemented: `validate`, `analyze`. The rest are stubs — see TODO.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from personal_finance_dashboard import data
from personal_finance_dashboard.charts import plot_monthly_flow, plot_top_categories

app = typer.Typer(help="Personal finance analysis — CSV -> report + JSON.")

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
    Does not calculate a budget. Equivalent of /waliduj.
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
        f"# Data validation — {date.today().isoformat()}",
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
    report_path = REPORTS_DIR / f"waliduj_{date.today().isoformat()}.md"
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
    Equivalent of /analiza.
    """
    if not csv_path.exists():
        _emit({"ok": False, "error": f"Missing file {csv_path}"})
        raise typer.Exit(code=1)
    if not profile_path.exists():
        _emit({"ok": False, "error": f"Missing {profile_path}. Run /profil."})
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
        f"# Analysis — ACTIVE window (from {profile['okresy']['regime_change_date']})",
        "",
        f"Months in window: {len(flow)}.",
        "",
        "## Monthly flow",
        flow.round(0).to_markdown(),
        "",
        "## Fixed costs (candidates, for approval)",
        fixed_costs.to_markdown(index=False) if not fixed_costs.empty else "None detected.",
        "",
        "## Top categories",
        by_category.sort_values(ascending=False).head(15).round(0).to_markdown(),
        "",
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"analiza_{date.today().isoformat()}.md"
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


@app.command()
def monthly() -> None:
    """Month close. NOT IMPLEMENTED — see TODO.md."""
    _not_implemented("monthly", "/miesiac")


@app.command()
def category(name: str = typer.Argument(...)) -> None:
    """Deep dive into a category. NOT IMPLEMENTED — see TODO.md."""
    _not_implemented("category", "/kategoria")


@app.command()
def invest() -> None:
    """Investment plan. NOT IMPLEMENTED — see TODO.md."""
    _not_implemented("invest", "/inwestycje")


@app.command()
def goal(name: str = typer.Argument(...)) -> None:
    """Goal simulation. NOT IMPLEMENTED — see TODO.md."""
    _not_implemented("goal", "/cel")


if __name__ == "__main__":
    app()
