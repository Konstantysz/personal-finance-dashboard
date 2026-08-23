"""Charts. Deterministic, ready-made functions - no ad hoc plotting in the CLI."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_monthly_flow(
    flow: pd.DataFrame, out_path: str | Path, regime_change: pd.Timestamp | None = None
) -> Path:
    """Bars for income/expenses/savings + balance line, month by month."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    x = flow.index.astype(str)
    width = 0.25
    positions = range(len(x))

    ax.bar([p - width for p in positions], flow["przychod"], width, label="Income")
    ax.bar(list(positions), flow["wydatki"], width, label="Expenses")
    ax.bar([p + width for p in positions], flow["oszczednosci"], width, label="Savings")
    ax.plot(list(positions), flow["bilans"], color="black", marker="o", label="Balance")
    ax.axhline(0, color="grey", linewidth=0.8)

    ax.set_xticks(list(positions))
    ax.set_xticklabels(x, rotation=45, ha="right")
    ax.set_ylabel("PLN")
    ax.set_title("Monthly flow")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_top_categories(by_category: pd.Series, out_path: str | Path, top_n: int = 15) -> Path:
    """Horizontal bar of top N categories by total expenses."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    top = by_category.sort_values(ascending=True).tail(top_n)

    fig, ax = plt.subplots(figsize=(9, max(4, 0.35 * len(top))))
    ax.barh(top.index.astype(str), list(top.to_numpy()))
    ax.set_xlabel("PLN")
    ax.set_title(f"Top {top_n} expense categories")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_monthly_categories_stacked(
    df: pd.DataFrame, out_path: str | Path, top_n: int = 10
) -> Path:
    """
    Stacked bar chart: months on the X axis, expenses by category.
    Shows only the top N categories; the rest goes into "Inne".

    Args:
        df: DataFrame with columns: month, category, amount.
        out_path: Output PNG file path.
        top_n: Number of top categories to show (rest grouped as "Inne").

    Raises:
        ValueError: If required columns missing or DataFrame is empty.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if "month" not in df.columns or "category" not in df.columns or "amount" not in df.columns:
        raise ValueError("DataFrame must have columns: month, category, amount")

    if df.empty:
        raise ValueError("DataFrame is empty; nothing to plot")

    monthly_by_cat = df.groupby(["month", "category"])["amount"].sum().unstack(fill_value=0)

    top_cats = monthly_by_cat.sum().nlargest(top_n).index
    plot_data = monthly_by_cat[top_cats].copy()
    if len(monthly_by_cat.columns) > top_n:
        plot_data["Inne"] = monthly_by_cat.drop(columns=top_cats).sum(axis=1)

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_data.plot(kind="bar", stacked=True, ax=ax)
    ax.set_ylabel("PLN")
    ax.set_xlabel("Month")
    ax.set_title(f"Monthly expenses (top {top_n} categories)")
    ax.legend(title="Category", bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_category(monthly: pd.Series, out_path: str | Path, title: str) -> Path:
    """Plot a category's monthly expenses."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly.index.astype(str), monthly.to_numpy(), marker="o")
    ax.set_ylabel("PLN")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_goal(values: dict[str, list[float]], target: float, out_path: str | Path) -> Path:
    """Plot goal accumulation scenarios."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, series in values.items():
        ax.plot(range(len(series)), series, label=label)
    ax.axhline(target, color="black", linestyle="--", label="Goal")
    ax.set_ylabel("PLN")
    ax.set_xlabel("Month")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
