"""Tests for chart generation functions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from personal_finance_dashboard.charts import (
    plot_category,
    plot_category_stack,
    plot_goal,
    plot_monthly_flow,
    plot_top_categories,
)


def test_plot_top_categories_creates_file(tmp_path: Path) -> None:
    """plot_top_categories creates a PNG file."""
    data = pd.Series({"Jedzenie": 2000, "Transport": 500, "Rozrywka": 300}, name="amount")
    out_path = tmp_path / "top_categories.png"

    result = plot_top_categories(data, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path


def test_plot_top_categories_with_custom_top_n(tmp_path: Path) -> None:
    """plot_top_categories respects top_n parameter."""
    data = pd.Series({f"Category{i}": 1000 - i * 100 for i in range(20)})
    out_path = tmp_path / "top_categories.png"

    result = plot_top_categories(data, out_path, top_n=5)

    assert out_path.exists()
    assert result == out_path


def test_plot_category_stack_creates_file(tmp_path: Path) -> None:
    """plot_category_stack creates a PNG file."""
    pivot = pd.DataFrame(
        {"2026-01": [200, 100], "2026-02": [250, 80]},
        index=["Jedzenie i napoje", "Transport"],
    )
    out_path = tmp_path / "stack.png"

    result = plot_category_stack(pivot, out_path, group_order=["Jedzenie i napoje", "Transport"])

    assert out_path.exists()
    assert result == out_path


def test_plot_category_stack_rolls_leaves_up_to_group(tmp_path: Path) -> None:
    """Two leaves of the same group collapse into one stacked series, not two."""
    pivot = pd.DataFrame(
        {"2026-01": [200, 100, 50]}, index=["Zakupy spożywcze", "Restauracja", "Paliwo"]
    )
    group_of = {
        "Zakupy spożywcze": "Jedzenie i napoje",
        "Restauracja": "Jedzenie i napoje",
        "Paliwo": "Transport",
    }
    out_path = tmp_path / "stack_grouped.png"

    plot_category_stack(
        pivot, out_path, group_of=group_of, group_order=["Jedzenie i napoje", "Transport"]
    )

    assert out_path.exists()


def test_plot_category_stack_raises_for_group_without_color(tmp_path: Path) -> None:
    """A group missing from `_GROUP_COLORS` is a config gap, not a silent fallback."""
    pivot = pd.DataFrame({"2026-01": [100.0]}, index=["Nieznana grupa"])
    out_path = tmp_path / "stack_unknown.png"

    with pytest.raises(KeyError):
        plot_category_stack(pivot, out_path, group_order=["Nieznana grupa"])


def test_plot_monthly_flow_creates_file(tmp_path: Path) -> None:
    """plot_monthly_flow creates a PNG file."""
    flow = pd.DataFrame(
        {
            "przychod": [2500.0, 2500.0, 2500.0],
            "wydatki": [1500.0, 1600.0, 1550.0],
            "oszczednosci": [1000.0, 900.0, 950.0],
            "bilans": [1000.0, 1900.0, 2850.0],
        },
        index=pd.PeriodIndex(["2026-06", "2026-07", "2026-08"], freq="M"),
    )
    out_path = tmp_path / "monthly_flow.png"

    result = plot_monthly_flow(flow, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path


def test_plot_monthly_flow_with_regime_change(tmp_path: Path) -> None:
    """plot_monthly_flow works with regime_change parameter."""
    flow = pd.DataFrame(
        {
            "przychod": [2500.0, 2500.0],
            "wydatki": [1500.0, 1600.0],
            "oszczednosci": [1000.0, 900.0],
            "bilans": [1000.0, 1900.0],
        },
        index=pd.PeriodIndex(["2026-07", "2026-08"], freq="M"),
    )
    out_path = tmp_path / "monthly_flow_with_regime.png"

    result = plot_monthly_flow(flow, out_path, regime_change=pd.Timestamp("2026-06-01"))

    assert out_path.exists()
    assert result == out_path


def test_plot_category_creates_file(tmp_path: Path) -> None:
    """plot_category creates a PNG file."""
    monthly = pd.Series(
        [1000.0, 1100.0, 1050.0],
        index=pd.PeriodIndex(["2026-06", "2026-07", "2026-08"], freq="M"),
    )
    out_path = tmp_path / "category.png"

    result = plot_category(monthly, out_path, "Food")

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path


def test_plot_goal_creates_file(tmp_path: Path) -> None:
    """plot_goal creates a PNG file."""
    scenarios = {
        "conservative": [1000.0, 1150.0, 1320.0, 1518.0],
        "base": [1000.0, 1200.0, 1450.0, 1750.0],
    }
    target = 2000.0
    out_path = tmp_path / "goal.png"

    result = plot_goal(scenarios, target, out_path)

    assert out_path.exists()
    assert out_path.suffix == ".png"
    assert result == out_path


def test_plot_top_categories_creates_parent_directories(tmp_path: Path) -> None:
    """plot_top_categories creates missing parent directories."""
    data = pd.Series({"A": 100, "B": 200}, name="amount")
    out_path = tmp_path / "nested" / "deep" / "dir" / "top_categories.png"

    _ = plot_top_categories(data, out_path)

    assert out_path.exists()
    assert out_path.parent == tmp_path / "nested" / "deep" / "dir"


def test_plot_monthly_flow_creates_parent_directories(tmp_path: Path) -> None:
    """plot_monthly_flow creates missing parent directories."""
    flow = pd.DataFrame(
        {
            "przychod": [2500.0],
            "wydatki": [1500.0],
            "oszczednosci": [1000.0],
            "bilans": [1000.0],
        },
        index=pd.PeriodIndex(["2026-06"], freq="M"),
    )
    out_path = tmp_path / "nested" / "dir" / "monthly_flow.png"

    _ = plot_monthly_flow(flow, out_path)

    assert out_path.exists()
    assert out_path.parent == tmp_path / "nested" / "dir"


def test_plot_category_creates_parent_directories(tmp_path: Path) -> None:
    """plot_category creates missing parent directories."""
    monthly = pd.Series(
        [1000.0],
        index=pd.PeriodIndex(["2026-06"], freq="M"),
    )
    out_path = tmp_path / "nested" / "dir" / "category.png"

    _ = plot_category(monthly, out_path, "Food")

    assert out_path.exists()
    assert out_path.parent == tmp_path / "nested" / "dir"


def test_plot_goal_creates_parent_directories(tmp_path: Path) -> None:
    """plot_goal creates missing parent directories."""
    scenarios = {"base": [1000.0, 1200.0]}
    target = 2000.0
    out_path = tmp_path / "nested" / "dir" / "goal.png"

    _ = plot_goal(scenarios, target, out_path)

    assert out_path.exists()
    assert out_path.parent == tmp_path / "nested" / "dir"
