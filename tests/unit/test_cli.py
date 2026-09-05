"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from personal_finance_dashboard.cli import _build_monthly_report, app

runner = CliRunner()


def test_build_monthly_report_includes_monthly_balance() -> None:
    """_build_monthly_report includes monthly balance information."""
    trends = {
        "last_month": "2026-08",
        "last_month_stats": {
            "wydatki": 9525.43,
            "przychod": 11530.08,
            "oszczednosci": 0.0,
            "bilans": 2004.65,
        },
        "trends": {
            "wydatki_3m": 12690.35,
            "wydatki_6m": None,
            "wydatki_12m": None,
        },
        "pct_change": {"vs_3m": -24.9},
        "category_changes": {"up": [], "down": []},
        "all_categories_breakdown": [],
        "new_categories": [],
        "new_fixed_costs": [],
        "fixed_costs_total": 10000.0,
    }

    report = _build_monthly_report(trends)

    assert "2026-08" in report
    assert "9525.43" in report


def test_build_monthly_report_includes_category_table() -> None:
    """_build_monthly_report includes category breakdown table."""
    trends = {
        "last_month": "2026-08",
        "last_month_stats": {
            "wydatki": 1000.0,
            "przychod": 1000.0,
            "oszczednosci": 0.0,
            "bilans": 0.0,
        },
        "trends": {"wydatki_3m": 1000.0, "wydatki_6m": None, "wydatki_12m": None},
        "pct_change": {"vs_3m": 0.0},
        "category_changes": {"up": [], "down": []},
        "all_categories_breakdown": [
            {
                "kategoria": "Food",
                "kwota": 500.0,
                "procent_wydatkow": 50.0,
                "vs_poprzedni": None,
                "vs_3m_srednia": 0.0,
                "vs_6m_srednia": None,
                "vs_12m_srednia": None,
            }
        ],
        "new_categories": [],
        "new_fixed_costs": [],
        "fixed_costs_total": 500.0,
    }

    report = _build_monthly_report(trends)

    assert "Category breakdown" in report
    assert "Food" in report


def test_build_monthly_report_includes_fixed_costs() -> None:
    """_build_monthly_report includes fixed costs estimate."""
    trends = {
        "last_month": "2026-08",
        "last_month_stats": {
            "wydatki": 10000.0,
            "przychod": 10000.0,
            "oszczednosci": 0.0,
            "bilans": 0.0,
        },
        "trends": {"wydatki_3m": 10000.0, "wydatki_6m": None, "wydatki_12m": None},
        "pct_change": {"vs_3m": 0.0},
        "category_changes": {"up": [], "down": []},
        "all_categories_breakdown": [],
        "new_categories": [],
        "new_fixed_costs": [
            {"pozycja": "Rent", "mediana_miesieczna": 5000.0, "miesiecy": 3, "stabilnych": 3}
        ],
        "fixed_costs_total": 5000.0,
    }

    report = _build_monthly_report(trends)

    assert "Fixed costs estimate" in report
    assert "5000.0" in report


def test_build_monthly_report_minimal_data() -> None:
    """_build_monthly_report works with minimal required data."""
    trends = {
        "last_month": "2026-08",
        "last_month_stats": {"wydatki": 0.0, "przychod": 0.0, "oszczednosci": 0.0, "bilans": 0.0},
        "trends": {"wydatki_3m": None, "wydatki_6m": None, "wydatki_12m": None},
        "pct_change": {},
        "category_changes": {"up": [], "down": []},
        "all_categories_breakdown": [],
        "new_categories": [],
        "new_fixed_costs": [],
        "fixed_costs_total": 0.0,
    }

    report = _build_monthly_report(trends)

    assert "2026-08" in report
    assert "Monthly close" in report


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
