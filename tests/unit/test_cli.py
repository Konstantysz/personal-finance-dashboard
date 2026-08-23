"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from personal_finance_dashboard.cli import _build_monthly_report, app

runner = CliRunner()


@pytest.fixture
def sample_category_stats() -> tuple[pd.DataFrame, dict]:
    """Create sample category analysis results."""
    cat_summary = pd.DataFrame(
        {
            "kategoria": ["Jedzenie", "Transport"],
            "srednia": [2000.0, 500.0],
            "min": [1800.0, 400.0],
            "max": [2200.0, 600.0],
            "stdev": [150.0, 80.0],
            "miesiece": [3, 3],
            "udzial_%": [80.0, 20.0],
        }
    )

    overall = {
        "srednia_wydatki": 2500.0,
        "min_miesiace": 2400.0,
        "max_miesiace": 2600.0,
        "stdev_miesiace": 80.0,
        "liczba_miesiecy": 3,
    }

    return cat_summary, overall


def test_build_monthly_report_includes_overall_stats(
    sample_category_stats: tuple[pd.DataFrame, dict]
) -> None:
    """_build_monthly_report includes overall statistics."""
    cat_summary, overall = sample_category_stats
    fixed_costs = pd.DataFrame(columns=["pozycja", "mediana_miesieczna"])

    profile = {"okresy": {"regime_change_date": "2025-08"}}

    report = _build_monthly_report(cat_summary, overall, fixed_costs, profile)

    assert "Expense analysis by category" in report
    assert "Overall statistics" in report
    assert "2500.0" in report or "2500" in report


def test_build_monthly_report_includes_distribution_table(
    sample_category_stats: tuple[pd.DataFrame, dict]
) -> None:
    """_build_monthly_report includes category distribution table."""
    cat_summary, overall = sample_category_stats
    fixed_costs = pd.DataFrame(columns=["pozycja", "mediana_miesieczna"])

    profile = {"okresy": {"regime_change_date": "2025-08"}}

    report = _build_monthly_report(cat_summary, overall, fixed_costs, profile)

    assert "Distribution by category" in report
    assert "Jedzenie" in report


def test_build_monthly_report_includes_fixed_costs_caveat_when_present(
    sample_category_stats: tuple[pd.DataFrame, dict]
) -> None:
    """_build_monthly_report adds disclaimer to fixed costs candidates."""
    cat_summary, overall = sample_category_stats
    fixed_costs = pd.DataFrame(
        {"pozycja": ["Jedzenie | Lidl"], "mediana_miesieczna": [500.0]}
    )

    profile = {"okresy": {"regime_change_date": "2025-08"}}

    report = _build_monthly_report(cat_summary, overall, fixed_costs, profile)

    assert "Fixed expenses (candidates)" in report
    assert "heuristic" in report.lower()
    assert "review and approve" in report


def test_build_monthly_report_empty_fixed_costs_omits_section(
    sample_category_stats: tuple[pd.DataFrame, dict]
) -> None:
    """_build_monthly_report omits fixed costs section when empty."""
    cat_summary, overall = sample_category_stats
    fixed_costs = pd.DataFrame(columns=["pozycja", "mediana_miesieczna"])

    profile = {"okresy": {"regime_change_date": "2025-08"}}

    report = _build_monthly_report(cat_summary, overall, fixed_costs, profile)

    assert "Fixed expenses" not in report


def test_monthly_command_missing_csv_returns_error(tmp_path: Path) -> None:
    """monthly command returns error when CSV is missing."""
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("okresy:\n  regime_change_date: 2025-08\n")

    result = runner.invoke(
        app, ["monthly", "--csv", str(tmp_path / "nonexistent.csv"), "--profile", str(profile_path)]
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False
    assert "Missing file" in output["error"]


def test_monthly_command_missing_profile_returns_error(tmp_path: Path) -> None:
    """monthly command returns error when profile is missing."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a;b;c\n1;2;3")

    result = runner.invoke(
        app, ["monthly", "--csv", str(csv_path), "--profile", str(tmp_path / "nonexistent.yaml")]
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False
    assert "Missing" in output["error"]
