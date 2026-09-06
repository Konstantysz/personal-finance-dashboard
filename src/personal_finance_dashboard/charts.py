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


# Fixed group -> color, matched to the app's own palette. Color follows the
# group's identity, never its rank. Every top-level group in
# config/category_tree.json must have an entry here.
_GROUP_COLORS = {
    "Jedzenie i napoje": "#fa2f00",
    "Zakupy": "#00e5fa",
    "Mieszkanie": "#faa700",
    "Transport": "#b0b0b0",
    "Pojazd": "#de31f5",
    "Życie i rozrywka": "#4cff00",
    "Komunikacja, komputer": "#0064ff",
    "Wydatki finansowe": "#00ffcb",
    "Inwestycje": "#ff0069",
    "Przychód": "#ffef00",
    "Inne": "#898781",
}


def plot_category_stack(
    pivot: pd.DataFrame,
    out_path: str | Path,
    group_order: list[str],
    group_of: dict[str, str] | None = None,
) -> Path:
    """Stacked bar of expenses per top-level group (rows) across months (columns).

    Every leaf category belongs to exactly one top-level group in
    `config/category_tree.json` (a transaction can be booked directly on any
    tree node, not just a leaf). Stacking by leaf produces 50+ colors that no
    categorical palette can keep distinct, so this always rolls up to groups
    first - the same rollup `data.category_breakdown` reports as `grupy`.

    Args:
        pivot: Category x period PLN, as returned by `data.category_breakdown`
            (`result["pivot"]`), indexed by leaf/node category name.
        out_path: PNG destination.
        group_order: Display order for groups (e.g. `category_tree.json` key
            order). Groups in `pivot` but absent here are dropped.
        group_of: Category -> top-level group, from `data.load_category_tree`.
            Required to roll up; without it every row is its own group (only
            sane for already-grouped input).

    Raises:
        KeyError: If a group has no entry in `_GROUP_COLORS` - add it there
            rather than falling back to a generated color.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if group_of:
        rolled = pivot.groupby(pivot.index.map(lambda c: group_of.get(c, c))).sum()
    else:
        rolled = pivot

    order = [g for g in group_order if g in rolled.index]
    top = rolled.loc[order]
    colors = [_GROUP_COLORS[g] for g in order]

    fig, ax = plt.subplots(figsize=(11, 6))
    x = top.columns.astype(str)
    bottom = pd.Series(0.0, index=top.columns)
    for group, color in zip(top.index, colors, strict=True):
        ax.bar(
            x,
            top.loc[group],
            bottom=bottom,
            label=str(group),
            color=color,
            edgecolor="#fcfcfb",
            linewidth=1,
        )
        bottom = bottom + top.loc[group]

    ax.set_ylabel("PLN")
    ax.set_title("Expenses by group, per month")
    ax.tick_params(axis="x", rotation=45)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9, frameon=False)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
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
