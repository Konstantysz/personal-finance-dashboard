"""Wykresy. Deterministyczne, gotowe funkcje — bez ad hoc plotowania w CLI."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_monthly_flow(
    flow: pd.DataFrame, out_path: str | Path, regime_change: pd.Timestamp | None = None
) -> Path:
    """Słupki przychód/wydatki/oszczędności + linia bilansu, miesiąc po miesiącu."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    x = flow.index.astype(str)
    width = 0.25
    positions = range(len(x))

    ax.bar([p - width for p in positions], flow["przychod"], width, label="Przychód")
    ax.bar(list(positions), flow["wydatki"], width, label="Wydatki")
    ax.bar([p + width for p in positions], flow["oszczednosci"], width, label="Oszczędności")
    ax.plot(list(positions), flow["bilans"], color="black", marker="o", label="Bilans")
    ax.axhline(0, color="grey", linewidth=0.8)

    ax.set_xticks(list(positions))
    ax.set_xticklabels(x, rotation=45, ha="right")
    ax.set_ylabel("PLN")
    ax.set_title("Przepływ miesięczny")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_top_categories(by_category: pd.Series, out_path: str | Path, top_n: int = 15) -> Path:
    """Poziomy bar top N kategorii wg sumy wydatków."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    top = by_category.sort_values(ascending=True).tail(top_n)

    fig, ax = plt.subplots(figsize=(9, max(4, 0.35 * len(top))))
    ax.barh(top.index.astype(str), list(top.to_numpy()))
    ax.set_xlabel("PLN")
    ax.set_title(f"Top {top_n} kategorii wydatków")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
