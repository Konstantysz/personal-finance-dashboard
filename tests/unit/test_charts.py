"""Tests for chart generation functions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from personal_finance_dashboard.charts import plot_top_categories


def test_plot_top_categories_creates_file(tmp_path: Path) -> None:
    """plot_top_categories creates a PNG file."""
    data = pd.Series({"Jedzenie": 2000, "Transport": 500, "Rozrywka": 300}, name="amount")
    out_path = tmp_path / "top_categories.png"

    result = plot_top_categories(data, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path
