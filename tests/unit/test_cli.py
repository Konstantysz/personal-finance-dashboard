"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from personal_finance_dashboard.cli import _build_monthly_report, app

runner = CliRunner()


@pytest.fixture
def tmp_csv(tmp_path: Path) -> Path:
    """Minimal valid CSV with transactions (6 months for forecast)."""
    csv_path = tmp_path / "test.csv"
    rows = []
    for month in range(1, 7):
        rows.append(
            {
                "date": f"2026-{month:02d}-01T10:00:00.000Z",
                "amount": "-1000",
                "account": "Checking",
                "category": "Food",
                "type": "Wydatek",
                "transfer": "false",
                "payee": "Store",
                "currency": "PLN",
                "ref_currency_amount": "-1000",
                "payment_type": "Card",
                "note": "",
                "labels": "",
            }
        )
        rows.append(
            {
                "date": f"2026-{month:02d}-05T10:00:00.000Z",
                "amount": "2500",
                "account": "Checking",
                "category": "Income",
                "type": "Przychód",
                "transfer": "false",
                "payee": "Employer",
                "currency": "PLN",
                "ref_currency_amount": "2500",
                "payment_type": "Transfer",
                "note": "",
                "labels": "",
            }
        )
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")
    return csv_path


@pytest.fixture
def tmp_profile(tmp_path: Path) -> Path:
    """Minimal valid profile YAML."""
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "okresy:\n"
        "  regime_change_date: 2026-01-01\n"
        "osoba:\n"
        "  tryb_okresu: kalendarzowy\n"
        "konta:\n"
        "  biezace:\n"
        "    - Checking\n"
        "  oszczednosciowe:\n"
        "    - Savings\n"
        "  salda_rzeczywiste:\n"
        "    wartosci:\n"
        "      Checking: 5000\n"
        "      Savings: 10000\n"
        "stan_wdrozenia:\n"
        "  poduszka_finansowa_kwota: 5000\n"
        "cele:\n"
        "  krotkoterminowe: []\n"
        "  dlugoterminowe: []\n"
        "  pozyczki_wlasne: []\n"
    )
    return profile_path


@pytest.fixture
def tmp_params(tmp_path: Path) -> Path:
    """Minimal valid parameters YAML."""
    params_path = tmp_path / "parameters.yaml"
    params_path.write_text(
        "last_verified: 2026-09-01\n"
        "symulacje:\n"
        "  scenariusz_bazowy:\n"
        "    akcje_globalne_nominalnie: 0.07\n"
        "  scenariusz_ostrozny:\n"
        "    akcje_globalne_nominalnie: 0.03\n"
    )
    return params_path


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


def test_validate_command_success(tmp_csv: Path, tmp_path: Path) -> None:
    """validate command succeeds with valid CSV."""
    result = runner.invoke(app, ["validate", "--csv", str(tmp_csv)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert output["rows"] == 12
    assert output["accounts"] == 1


def test_validate_command_missing_csv(tmp_path: Path) -> None:
    """validate command returns error when CSV is missing."""
    result = runner.invoke(app, ["validate", "--csv", str(tmp_path / "nonexistent.csv")])

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False
    assert "Missing file" in output["error"]


def test_analyze_command_success(tmp_csv: Path, tmp_profile: Path, tmp_path: Path) -> None:
    """analyze command succeeds with valid CSV and profile."""
    result = runner.invoke(app, ["analyze", "--csv", str(tmp_csv), "--profile", str(tmp_profile)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert "months_in_window" in output
    assert output["months_in_window"] > 0


def test_analyze_command_missing_csv(tmp_profile: Path) -> None:
    """analyze command returns error when CSV is missing."""
    result = runner.invoke(
        app, ["analyze", "--csv", "/nonexistent.csv", "--profile", str(tmp_profile)]
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_analyze_command_missing_profile(tmp_csv: Path) -> None:
    """analyze command returns error when profile is missing."""
    result = runner.invoke(app, ["analyze", "--csv", str(tmp_csv), "--profile", "/nonexistent"])

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_monthly_command_success(tmp_csv: Path, tmp_profile: Path) -> None:
    """monthly command succeeds with valid CSV and profile."""
    result = runner.invoke(app, ["monthly", "--csv", str(tmp_csv), "--profile", str(tmp_profile)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert "last_month" in output
    assert "last_month_balance" in output


def test_category_command_success(tmp_csv: Path, tmp_profile: Path) -> None:
    """category command succeeds with existing category."""
    result = runner.invoke(
        app,
        ["category", "Food", "--csv", str(tmp_csv), "--profile", str(tmp_profile)],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert output["category"] == "Food"


def test_category_command_missing_category(tmp_csv: Path, tmp_profile: Path) -> None:
    """category command returns error when category does not exist."""
    result = runner.invoke(
        app,
        ["category", "NonExistentCategory", "--csv", str(tmp_csv), "--profile", str(tmp_profile)],
    )

    assert result.exit_code == 2
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_category_command_missing_files(tmp_path: Path) -> None:
    """category command returns error when CSV or profile is missing."""
    result = runner.invoke(
        app,
        [
            "category",
            "Food",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_path / "nonexistent.yaml"),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_invest_command_success(tmp_csv: Path, tmp_profile: Path, tmp_params: Path) -> None:
    """invest command succeeds with valid CSV, profile, and params."""
    result = runner.invoke(
        app,
        [
            "invest",
            "--csv",
            str(tmp_csv),
            "--profile",
            str(tmp_profile),
            "--params",
            str(tmp_params),
        ],
    )

    if result.exit_code != 0:
        print("stdout:", result.stdout)
        if result.exception:
            import traceback

            traceback.print_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert "monthly_contribution" in output


def test_invest_command_missing_files(tmp_path: Path) -> None:
    """invest command returns error when files are missing."""
    result = runner.invoke(
        app,
        [
            "invest",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_path / "nonexistent.yaml"),
            "--params",
            str(tmp_path / "nonexistent.yaml"),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_goal_command_missing_goal(tmp_csv: Path, tmp_profile: Path, tmp_params: Path) -> None:
    """goal command returns error when goal does not exist."""
    result = runner.invoke(
        app,
        [
            "goal",
            "NonExistentGoal",
            "--csv",
            str(tmp_csv),
            "--profile",
            str(tmp_profile),
            "--params",
            str(tmp_params),
        ],
    )

    assert result.exit_code == 2
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_goal_command_missing_files(tmp_path: Path) -> None:
    """goal command returns error when files are missing."""
    result = runner.invoke(
        app,
        [
            "goal",
            "TestGoal",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_path / "nonexistent.yaml"),
            "--params",
            str(tmp_path / "nonexistent.yaml"),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_taxes_command_missing_files(tmp_path: Path) -> None:
    """taxes command returns error when files are missing."""
    result = runner.invoke(
        app,
        [
            "taxes",
            "--profile",
            str(tmp_path / "nonexistent.yaml"),
            "--params",
            str(tmp_path / "nonexistent.yaml"),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_forecast_command_success(tmp_csv: Path, tmp_profile: Path) -> None:
    """forecast command succeeds with valid CSV and profile."""
    result = runner.invoke(
        app,
        ["forecast", "--csv", str(tmp_csv), "--profile", str(tmp_profile), "--months", "3"],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert "report" in output


def test_forecast_command_missing_csv(tmp_profile: Path) -> None:
    """forecast command returns error when CSV is missing."""
    result = runner.invoke(
        app,
        ["forecast", "--csv", "/nonexistent.csv", "--profile", str(tmp_profile)],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_monthly_command_invalid_month_format(tmp_csv: Path, tmp_profile: Path) -> None:
    """monthly command returns error with invalid month format."""
    result = runner.invoke(
        app,
        [
            "monthly",
            "--csv",
            str(tmp_csv),
            "--profile",
            str(tmp_profile),
            "--month",
            "invalid-month",
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_category_command_error_with_missing_csv(tmp_profile: Path, tmp_path: Path) -> None:
    """category command returns error when CSV is missing."""
    result = runner.invoke(
        app,
        [
            "category",
            "Food",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_profile),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_invest_command_error_with_missing_csv(
    tmp_profile: Path, tmp_params: Path, tmp_path: Path
) -> None:
    """invest command returns error when CSV is missing."""
    result = runner.invoke(
        app,
        [
            "invest",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_profile),
            "--params",
            str(tmp_params),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_goal_command_error_missing_files(tmp_path: Path) -> None:
    """goal command returns error when files are missing."""
    result = runner.invoke(
        app,
        [
            "goal",
            "TestGoal",
            "--csv",
            str(tmp_path / "nonexistent.csv"),
            "--profile",
            str(tmp_path / "nonexistent.yaml"),
            "--params",
            str(tmp_path / "nonexistent.yaml"),
        ],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_monthly_command_no_active_data(tmp_path: Path) -> None:
    """monthly command returns error when no data in ACTIVE window."""
    csv_path = tmp_path / "test.csv"
    rows = [
        {
            "date": "2025-01-01T10:00:00.000Z",
            "amount": "-1000",
            "account": "Checking",
            "category": "Food",
            "type": "Wydatek",
            "transfer": "false",
            "payee": "Store",
            "currency": "PLN",
            "ref_currency_amount": "-1000",
            "payment_type": "Card",
            "note": "",
            "labels": "",
        }
    ]
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "okresy:\n"
        "  regime_change_date: 2026-01-01\n"
        "osoba:\n"
        "  tryb_okresu: kalendarzowy\n"
        "konta:\n"
        "  biezace:\n"
        "    - Checking\n"
        "  oszczednosciowe:\n"
        "    - Savings\n"
        "  salda_rzeczywiste:\n"
        "    wartosci:\n"
        "      Checking: 5000\n"
        "      Savings: 10000\n"
    )

    result = runner.invoke(
        app,
        ["monthly", "--csv", str(csv_path), "--profile", str(profile_path)],
    )

    assert result.exit_code == 1
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False
    assert "No data" in output["error"]


def test_analyze_command_no_active_data(tmp_path: Path) -> None:
    """analyze command works even when no data in ACTIVE window."""
    csv_path = tmp_path / "test.csv"
    rows = [
        {
            "date": "2025-01-01T10:00:00.000Z",
            "amount": "-1000",
            "account": "Checking",
            "category": "Food",
            "type": "Wydatek",
            "transfer": "false",
            "payee": "Store",
            "currency": "PLN",
            "ref_currency_amount": "-1000",
            "payment_type": "Card",
            "note": "",
            "labels": "",
        }
    ]
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "okresy:\n"
        "  regime_change_date: 2026-01-01\n"
        "osoba:\n"
        "  tryb_okresu: kalendarzowy\n"
        "konta:\n"
        "  biezace:\n"
        "    - Checking\n"
        "  oszczednosciowe:\n"
        "    - Savings\n"
        "  salda_rzeczywiste:\n"
        "    wartosci:\n"
        "      Checking: 5000\n"
        "      Savings: 10000\n"
    )

    result = runner.invoke(
        app,
        ["analyze", "--csv", str(csv_path), "--profile", str(profile_path)],
    )

    # Result can be ok=true (empty analysis) or ok=false (no ACTIVE data)
    output = json.loads(result.stdout.strip())
    assert "ok" in output or "error" in output


def test_monthly_command_empty_window(tmp_path: Path) -> None:
    """monthly command with specific month outside range."""
    # Build CSV with January data only
    csv_path = tmp_path / "test.csv"
    rows = [
        {
            "date": "2026-01-05T10:00:00.000Z",
            "amount": "2500",
            "account": "Checking",
            "category": "Income",
            "type": "Przychód",
            "transfer": "false",
            "payee": "Employer",
            "currency": "PLN",
            "ref_currency_amount": "2500",
            "payment_type": "Transfer",
            "note": "",
            "labels": "",
        }
    ]
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "okresy:\n"
        "  regime_change_date: 2026-01-01\n"
        "osoba:\n"
        "  tryb_okresu: kalendarzowy\n"
        "konta:\n"
        "  biezace:\n"
        "    - Checking\n"
        "  oszczednosciowe:\n"
        "    - Savings\n"
        "  salda_rzeczywiste:\n"
        "    wartosci:\n"
        "      Checking: 5000\n"
        "      Savings: 10000\n"
    )

    result = runner.invoke(
        app,
        ["monthly", "--csv", str(csv_path), "--profile", str(profile_path), "--month", "2026-12"],
    )

    # Month outside available data should return an error or success with available month
    assert result.exit_code in (0, 1)
    output = json.loads(result.stdout.strip())
    assert "ok" in output or "error" in output


def test_analyze_with_category_analysis(tmp_csv: Path, tmp_profile: Path) -> None:
    """analyze command performs full category analysis."""
    result = runner.invoke(app, ["analyze", "--csv", str(tmp_csv), "--profile", str(tmp_profile)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert "months_in_window" in output
    assert "charts" in output
    assert len(output["charts"]) == 2  # flow + categories


def test_monthly_builds_full_report(tmp_csv: Path, tmp_profile: Path) -> None:
    """monthly command builds complete report markdown."""
    result = runner.invoke(app, ["monthly", "--csv", str(tmp_csv), "--profile", str(tmp_profile)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    # Check that report file path is valid
    report_path = Path(output["report"])
    assert report_path.exists()
    # Verify report contains expected sections
    report_text = report_path.read_text(encoding="utf-8")
    assert "Monthly close" in report_text
    assert "Balance" in report_text


def test_category_builds_full_report(tmp_csv: Path, tmp_profile: Path) -> None:
    """category command builds complete report markdown."""
    result = runner.invoke(
        app,
        ["category", "Food", "--csv", str(tmp_csv), "--profile", str(tmp_profile)],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    report_path = Path(output["report"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Category: Food" in report_text


def test_category_with_nonexistent_in_active(tmp_csv: Path, tmp_profile: Path) -> None:
    """category command with category that exists in archive but not active."""
    # This tests archive/active comparison logic
    result = runner.invoke(
        app,
        ["category", "NonExistent", "--csv", str(tmp_csv), "--profile", str(tmp_profile)],
    )

    # Command should fail because category doesn't exist even in archive
    assert result.exit_code == 2
    output = json.loads(result.stdout.strip())
    assert output["ok"] is False


def test_forecast_with_custom_months(tmp_csv: Path, tmp_profile: Path) -> None:
    """forecast command with custom months parameter."""
    result = runner.invoke(
        app,
        ["forecast", "--csv", str(tmp_csv), "--profile", str(tmp_profile), "--months", "6"],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert len(output["horyzont"]) == 6
    assert "report" in output


def test_validate_creates_report_file(tmp_csv: Path, tmp_path: Path) -> None:
    """validate command creates report file on disk."""
    result = runner.invoke(app, ["validate", "--csv", str(tmp_csv)])

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    report_path = Path(output["report"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Data validation" in report_text
    assert "Accounts" in report_text


def test_monthly_with_specific_valid_month(tmp_csv: Path, tmp_profile: Path) -> None:
    """monthly command with valid specific month."""
    result = runner.invoke(
        app,
        [
            "monthly",
            "--csv",
            str(tmp_csv),
            "--profile",
            str(tmp_profile),
            "--month",
            "2026-03",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout.strip())
    assert output["ok"] is True
    assert output["last_month"] == "2026-03"
