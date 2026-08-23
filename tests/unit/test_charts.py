"""Tests for chart generation functions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from personal_finance_dashboard.charts import plot_monthly_categories_stacked, plot_top_categories


@pytest.fixture
def sample_expenses_df() -> pd.DataFrame:
    """Create a sample expenses DataFrame for chart testing."""
    months = list(pd.period_range("2025-08", periods=3, freq="M")) * 2
    return pd.DataFrame(
        {
            "month": months,
            "category": ["Jedzenie", "Transport", "Jedzenie", "Transport", "Jedzenie", "Transport"],
            "amount": [500, 200, 550, 180, 480, 220],
        }
    )


def test_plot_monthly_categories_stacked_creates_file(
    sample_expenses_df: pd.DataFrame, tmp_path: Path
) -> None:
    """plot_monthly_categories_stacked creates a PNG file."""
    out_path = tmp_path / "test_chart.png"

    result = plot_monthly_categories_stacked(sample_expenses_df, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path


def test_plot_monthly_categories_stacked_missing_columns() -> None:
    """plot_monthly_categories_stacked raises ValueError for missing columns."""
    df_bad = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

    with pytest.raises(ValueError, match="must have columns"):
        plot_monthly_categories_stacked(df_bad, "dummy.png")


def test_plot_monthly_categories_stacked_empty_df() -> None:
    """plot_monthly_categories_stacked raises ValueError for empty DataFrame."""
    df_empty = pd.DataFrame({"month": [], "category": [], "amount": []})

    with pytest.raises(ValueError, match="is empty"):
        plot_monthly_categories_stacked(df_empty, "dummy.png")


def test_plot_monthly_categories_stacked_creates_parent_dirs(
    sample_expenses_df: pd.DataFrame, tmp_path: Path
) -> None:
    """plot_monthly_categories_stacked creates parent directories if needed."""
    out_path = tmp_path / "subdir" / "nested" / "chart.png"

    result = plot_monthly_categories_stacked(sample_expenses_df, out_path)

    assert out_path.parent.exists()
    assert out_path.exists()
    assert result == out_path


def test_plot_top_categories_creates_file(tmp_path: Path) -> None:
    """plot_top_categories creates a PNG file."""
    data = pd.Series({"Jedzenie": 2000, "Transport": 500, "Rozrywka": 300}, name="amount")
    out_path = tmp_path / "top_categories.png"

    result = plot_top_categories(data, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path
