"""
Testy skupione na trzech konkretnych błędach popełnionych w ręcznej analizie
(patrz historia projektu), żeby żaden refaktor ich nie odtworzył:

  1. saldo konta o mylącej nazwie pomylone z oszczędnościami,
  2. wszystkie transfery policzone jako oszczędności zamiast tylko wpłat
     na konto oszczędnościowe,
  3. średnia z całego okresu maskująca trend w ostatnim miesiącu.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from personal_finance_dashboard import data


def _mk_row(
    account: str,
    category: str,
    amount: float,
    type_: str,
    date: str,
    transfer: bool = False,
    payee: str = "",
) -> dict[str, object]:
    return {
        "account": account,
        "category": category,
        "currency": "PLN",
        "amount": amount,
        "ref_currency_amount": amount,
        "type": type_,
        "payment_type": "Przelew bankowy",
        "note": "",
        "date": date,
        "transfer": str(transfer).lower(),
        "payee": payee,
        "labels": "",
    }


@pytest.fixture
def sample_df(tmp_path) -> pd.DataFrame:
    rows = []
    for month in range(1, 4):
        d = f"2026-{month:02d}-10T00:00:00.000Z"
        rows.append(_mk_row("PKO", "Wynagrodzenie", 10000, "Przychód", d))
        # transfer oszczędnościowy: para PKO(Wydatek) <-> Konto oszcz.(Przychód)
        t = f"2026-{month:02d}-11T00:00:00.000Z"
        rows.append(_mk_row("PKO", "Przelew, wypłata", 1500, "Wydatek", t, True, "sav"))
        rows.append(
            _mk_row("Konto oszczędnościowe", "Przelew, wypłata", 1500, "Przychód", t, True, "sav")
        )
        # przesunięcie wewnętrzne PKO -> Revolut: NIE jest oszczędnością
        t2 = f"2026-{month:02d}-08T00:00:00.000Z"
        rows.append(_mk_row("PKO", "Przelew, wypłata", 100, "Wydatek", t2, True, "rev"))
        rows.append(_mk_row("Revolut", "Przelew, wypłata", 100, "Przychód", t2, True, "rev"))
        rows.append(
            _mk_row(
                "PKO", "Zakupy spożywcze", 2000, "Wydatek", f"2026-{month:02d}-15T00:00:00.000Z"
            )
        )

    csv_path = tmp_path / "wallet_export.csv"
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    return data.load(csv_path)


def test_transfers_are_paired_not_counted_as_income_or_expense(sample_df: pd.DataFrame) -> None:
    audit = data.audit_transfers(sample_df)
    assert len(audit.pairs) == 6  # 3 miesiące x 2 pary
    assert len(audit.orphans) == 0

    # Suma przychodów NIE zawiera strony transferu (błąd nr 2 w innej postaci:
    # gdyby transfer liczył się jako przychód/wydatek, poniższe by nie zgadzały).
    inc = data.income(sample_df)["amount"].sum()
    assert inc == pytest.approx(30000)  # tylko wynagrodzenie, 3 x 10000


def test_savings_only_from_designated_account_not_all_transfers(sample_df: pd.DataFrame) -> None:
    """Błąd #2: liczenie wszystkich transferów jako oszczędności."""
    only_savings = data.savings(sample_df, ["Konto oszczędnościowe"])
    assert only_savings["amount"].sum() == pytest.approx(4500)  # 3 x 1500

    all_incoming_transfers = sample_df[sample_df["transfer"] & (sample_df["type"] == "Przychód")]
    # Gdyby ktoś (błędnie) policzył wszystkie transfery jako oszczędności,
    # wyszłoby więcej niż rzeczywiste wpłaty na konto oszczędnościowe.
    assert all_incoming_transfers["amount"].sum() > only_savings["amount"].sum()


def test_savings_requires_explicit_account_list(sample_df: pd.DataFrame) -> None:
    """Nie zgaduj kont oszczędnościowych po nazwie - wymagaj jawnej listy."""
    with pytest.raises(ValueError):
        data.savings(sample_df, [])


def test_regime_change_detection_finds_step_increase() -> None:
    """Kategoria pojawiająca się od zera po N miesiącach = przełom."""
    rows = []
    for month in range(1, 8):
        d = f"2025-{month:02d}-05T00:00:00.000Z"
        rows.append(_mk_row("PKO", "Zakupy spożywcze", 500, "Wydatek", d))
        if month >= 5:
            rows.append(_mk_row("PKO", "Czynsz i media", 2500, "Wydatek", d))

    import io

    header = list(rows[0].keys())
    buf = io.StringIO()
    buf.write(";".join(header) + "\n")
    for r in rows:
        buf.write(";".join(str(r[k]) for k in header) + "\n")
    buf.seek(0)

    df = data.load(buf)
    detected, _ = data.detect_regime_change(df)
    assert detected == pd.Period("2025-05", freq="M")


def test_detect_fixed_costs_empty_result_does_not_crash() -> None:
    """
    Regresja: przy zbyt krótkiej historii (brak >=3 miesięcy dla żadnej
    pozycji) `out` jest puste, a pd.DataFrame([]) nie ma kolumn - sort_values
    na nieistniejącej kolumnie wywala KeyError. Wykryte przy pierwszym
    uruchomieniu `personal-finance-dashboard analyze` na świeżo sklonowanym repo z małym CSV.
    """
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 11000, "Przychód", "2025-08-10T00:00:00.000Z"),
        _mk_row("PKO", "Czynsz i media", 2600, "Wydatek", "2025-08-12T00:00:00.000Z"),
    ]
    import io

    header = list(rows[0].keys())
    buf = io.StringIO()
    buf.write(";".join(header) + "\n")
    for r in rows:
        buf.write(";".join(str(r[k]) for k in header) + "\n")
    buf.seek(0)

    df = data.load(buf)
    result = data.detect_fixed_costs(df)  # nie może rzucić

    assert result.empty
    assert list(result.columns) == [
        "pozycja",
        "mediana_miesieczna",
        "miesiecy",
        "stabilnych",
        "ostatni_miesiac",
    ]


def test_average_can_mask_last_month_trend() -> None:
    """
    Błąd #3: średnia z całego okresu vs ostatni miesiąc. Nie testujemy tu
    konkretnej liczby - dokumentujemy, że rolling_view zawsze zwraca OBA
    widoki, żeby nie dało się łatwo zgubić trendu.
    """
    flow = pd.DataFrame(
        {
            "przychod": [10000] * 5,
            "wydatki": [11000, 10800, 10500, 10200, 9000],
            "oszczednosci": [0] * 5,
        },
        index=pd.period_range("2025-08", periods=5, freq="M"),
    )
    flow["bilans"] = flow["przychod"] - flow["wydatki"] - flow["oszczednosci"]
    view = data.rolling_view(flow, window=3)

    assert flow["bilans"].mean() < 0  # średnia: deficyt
    assert flow["bilans"].iloc[-1] > 0  # ostatni miesiąc: nadwyżka
    assert "bilans_r3m" in view.columns  # oba widoki dostępne jednocześnie


def test_monthly_summary_calculates_category_stats(sample_df: pd.DataFrame) -> None:
    """monthly_summary returns category statistics and overall stats."""
    cat_summary, overall = data.monthly_summary(sample_df)

    assert not cat_summary.empty
    assert "kategoria" in cat_summary.columns
    assert "srednia" in cat_summary.columns
    assert "udzial_%" in cat_summary.columns

    assert overall["liczba_miesiecy"] == 3
    assert overall["srednia_wydatki"] == pytest.approx(2000)  # 6000 total / 3 months
    assert overall["min_miesiace"] == pytest.approx(2000)
    assert overall["max_miesiace"] == pytest.approx(2000)


def test_monthly_summary_empty_expenses_returns_empty(tmp_path) -> None:
    """monthly_summary handles an empty dataset without errors."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-08-10T00:00:00.000Z"),
    ]
    csv_path = tmp_path / "income_only.csv"
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    df = data.load(csv_path)
    cat_summary, overall = data.monthly_summary(df)

    assert cat_summary.empty
    assert overall["liczba_miesiecy"] == 0
    assert overall["srednia_wydatki"] == 0.0


def test_category_analysis_uses_active_data_and_finds_outliers(sample_df: pd.DataFrame) -> None:
    result = data.category_analysis(sample_df, "Zakupy")

    assert result["category"] == "Zakupy spożywcze"
    assert result["active"]["sum"] == pytest.approx(6000)
    assert result["active"]["monthly_average"] == pytest.approx(2000)
    assert result["counterparties"][0]["payee"] == ""
    assert result["outliers"] == []


def test_category_analysis_reports_ambiguous_matches(sample_df: pd.DataFrame) -> None:
    extra = sample_df.iloc[-1].copy()
    extra["category"] = "Zakupy chemiczne"
    result = data.category_analysis(pd.concat([sample_df, extra.to_frame().T]), "Zakupy")

    assert result["ambiguous"] is True
    assert len(result["matches"]) > 1


def test_investment_plan_has_two_scenarios_and_net_bond_return() -> None:
    profile = {
        "osoba": {"forma_zatrudnienia": "etat", "prog_podatkowy": 12},
        "stan_wdrozenia": {"poduszka_finansowa_kwota": 10000},
    }
    params = {
        "podatki": {"belka": 0.19},
        "konta_emerytalne": {"ike": {"limit": 28260}, "ikze": {"limit_etat": 11304}},
        "symulacje": {
            "scenariusz_ostrozny": {"obligacje_edo": 0.045, "akcje_globalne_nominalnie": 0.05},
            "scenariusz_bazowy": {"obligacje_edo": 0.05, "akcje_globalne_nominalnie": 0.07},
        },
    }

    result = data.investment_plan(profile, params, monthly_surplus=3000, starting_capital=20000)

    assert set(result["scenarios"]) == {"conservative", "base"}
    assert result["bond_return_net"] == pytest.approx(0.05 * 0.81)
    assert result["monthly_contribution"] == pytest.approx(3000)


def test_goal_simulation_returns_three_scenarios() -> None:
    result = data.goal_simulation(
        target=12000,
        deadline=pd.Period("2027-12", freq="M"),
        current_capital=0,
        monthly_surplus=1000,
        returns={"conservative": 0.02, "base": 0.05},
        seasonal_factors=[0.8, 1.2],
    )

    assert set(result["scenarios"]) == {"conservative", "base", "random_event"}
    assert result["required_monthly_contribution"] > 0
    assert result["seasonality_factor"] == pytest.approx(1.0)


def test_detect_fixed_costs_identifies_stable_categories(sample_df: pd.DataFrame) -> None:
    """detect_fixed_costs finds expenses with stable monthly amounts."""
    result = data.detect_fixed_costs(sample_df, min_months=2, tolerance=0.20)

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "pozycja" in result.columns
    assert "mediana_miesieczna" in result.columns
    assert "stabilnych" in result.columns


def test_detect_fixed_costs_empty_df_returns_empty(tmp_path: Path) -> None:
    """detect_fixed_costs returns empty DataFrame for income-only data."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-08-10T00:00:00.000Z"),
    ]
    csv_path = tmp_path / "income_only.csv"
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    df = data.load(csv_path)
    result = data.detect_fixed_costs(df)

    assert result.empty


def test_detect_fixed_costs_respects_stability_ratio(sample_df: pd.DataFrame) -> None:
    """detect_fixed_costs uses stability_ratio parameter correctly."""
    result_strict = data.detect_fixed_costs(
        sample_df, min_months=2, tolerance=0.20, stability_ratio=0.95
    )
    result_loose = data.detect_fixed_costs(
        sample_df, min_months=2, tolerance=0.20, stability_ratio=0.50
    )

    assert isinstance(result_strict, pd.DataFrame)
    assert isinstance(result_loose, pd.DataFrame)


def test_monthly_trends_returns_last_month_and_averages(sample_df: pd.DataFrame) -> None:
    """monthly_trends extracts last month data and compares with 3M/6M/12M."""
    result = data.monthly_trends(sample_df, ["Konto oszczędnościowe"])

    assert "last_month" in result
    assert "last_month_stats" in result
    assert "trends" in result
    assert "pct_change" in result
    assert "category_changes" in result

    # Last month should be the latest period
    assert result["last_month"] == "2026-03"

    # Stats should have key fields
    stats = result["last_month_stats"]
    assert "wydatki" in stats
    assert "bilans" in stats


def test_monthly_trends_categories_up_down(sample_df: pd.DataFrame) -> None:
    """monthly_trends identifies top 3 up/down categories vs 3M avg."""
    result = data.monthly_trends(sample_df, ["Konto oszczędnościowe"])

    changes = result["category_changes"]
    assert "up" in changes
    assert "down" in changes
    assert isinstance(changes["up"], list)
    assert isinstance(changes["down"], list)


def test_monthly_trends_single_month_works(tmp_path: Path) -> None:
    """monthly_trends works with single month (no rolling averages)."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-08-10T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2025-08-15T00:00:00.000Z"),
    ]
    csv_path = tmp_path / "single_month.csv"
    header = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")

    df = data.load(csv_path)
    result = data.monthly_trends(df, ["Konto oszczędnościowe"])
    assert result["last_month"] == "2025-08"
    # 3M/6M/12M should be None (no historical data)
    assert result["trends"]["wydatki_3m"] is None


def _write_csv(rows: list[dict[str, object]], path: Path) -> Path:
    header = list(rows[0].keys())
    with path.open("w", encoding="utf-8") as f:
        f.write(";".join(header) + "\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in header) + "\n")
    return path


def test_monthly_flow_excludes_incomplete_current_month(tmp_path: Path) -> None:
    """
    Błąd 4: bieżący, niedokończony miesiąc liczony jak pełny.

    Wypłata wpływa 21. dnia miesiąca, więc analiza uruchomiona 5. dnia widzi
    wydatki bez odpowiadającego im przychodu. Wciągnięcie takiego miesiąca do
    średnich zaniża je tym mocniej, im wcześniej w miesiącu ją uruchomiono.
    """
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-07-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-07-25T00:00:00.000Z"),
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-08-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-08-25T00:00:00.000Z"),
        # Bieżący miesiąc: same wydatki, wypłata (21.09) jeszcze nie wpłynęła.
        _mk_row("PKO", "Zakupy", 900, "Wydatek", "2026-09-03T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "incomplete.csv"))

    flow = data.monthly_flow(df, ["Konto oszczędnościowe"], today=pd.Timestamp("2026-09-05"))

    assert pd.Period("2026-09", freq="M") not in flow.index
    assert flow.index.max() == pd.Period("2026-08", freq="M")
    # Średnia bilansu liczona wyłącznie z pełnych miesięcy: (5000-1000) = 4000.
    assert flow["bilans"].mean() == pytest.approx(4000.0)


def test_monthly_flow_keeps_finished_month(tmp_path: Path) -> None:
    """Miesiąc, który już się skończył, zostaje — nawet jeśli jest ostatni."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-08-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-08-25T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "finished.csv"))

    flow = data.monthly_flow(df, ["Konto oszczędnościowe"], today=pd.Timestamp("2026-09-05"))

    assert pd.Period("2026-08", freq="M") in flow.index


def test_monthly_flow_incomplete_month_available_on_demand(tmp_path: Path) -> None:
    """Niepełny miesiąc da się odzyskać jawnie — nie znika z danych na stałe."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-08-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 900, "Wydatek", "2026-09-03T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "ondemand.csv"))

    flow = data.monthly_flow(
        df, ["Konto oszczędnościowe"], today=pd.Timestamp("2026-09-05"), drop_incomplete=False
    )

    assert pd.Period("2026-09", freq="M") in flow.index


def test_tax_calculation_requires_explicit_profile_fields() -> None:
    with pytest.raises(ValueError, match="forma_zatrudnienia"):
        data.tax_calculation({}, {"konta_emerytalne": {}}, today=pd.Timestamp("2026-08-23"))


# --------------------------------------------------------------------------
# assign_periods - okres rozliczeniowy wypłata-do-wypłaty (opcja B)
# --------------------------------------------------------------------------


def test_assign_periods_kalendarzowy_matches_dt_to_period(sample_df: pd.DataFrame) -> None:
    """Tryb domyślny/kalendarzowy = identyczny wynik jak dzisiejsze .dt.to_period('M')."""
    out = data.assign_periods(sample_df, mode="kalendarzowy")
    expected = sample_df["date"].dt.to_period("M")
    pd.testing.assert_series_equal(out["month"], expected, check_names=False)


def test_assign_periods_weekday_payday_matches_calendar(tmp_path: Path) -> None:
    """21. dzień miesiąca wypadający w zwykły dzień roboczy = brak przesunięcia."""
    # 2026-01-21 to środa (zwykły dzień roboczy, brak święta).
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-01-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-01-25T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "weekday_payday.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    assert (out["month"] == pd.Period("2026-01", freq="M")).all()


def _month_on(out: pd.DataFrame, date_str: str) -> pd.Period:
    return out.loc[out["date"].dt.date == pd.Timestamp(date_str).date(), "month"].iloc[0]


def test_assign_periods_saturday_payday_shifts_to_friday(tmp_path: Path) -> None:
    """21. wypada w sobotę (2026-11-21) -> granica przesunięta na piątek 2026-11-20."""
    rows = [
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-11-19T00:00:00.000Z"),  # przed granicą
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-11-20T00:00:00.000Z"),  # granica
    ]
    df = data.load(_write_csv(rows, tmp_path / "saturday_payday.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    assert _month_on(out, "2026-11-19") == pd.Period("2026-10", freq="M")
    assert _month_on(out, "2026-11-20") == pd.Period("2026-11", freq="M")


def test_assign_periods_sunday_payday_shifts_to_friday_not_saturday(tmp_path: Path) -> None:
    """21. wypada w niedzielę (2026-06-21) -> granica na piątek 2026-06-19, nie sobotę."""
    rows = [
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-06-18T00:00:00.000Z"),  # przed granicą
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-06-19T00:00:00.000Z"),  # granica
    ]
    df = data.load(_write_csv(rows, tmp_path / "sunday_payday.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    assert _month_on(out, "2026-06-18") == pd.Period("2026-05", freq="M")
    assert _month_on(out, "2026-06-19") == pd.Period("2026-06", freq="M")


def test_assign_periods_holiday_and_weekend_walks_back_to_workday(tmp_path: Path) -> None:
    """
    21.04.2025 to Poniedziałek Wielkanocny (święto), 20.04 niedziela (też
    Wielkanoc), 19.04 sobota - granica musi cofnąć się aż do piątku 18.04,
    jedynego dnia roboczego w tym ciągu.
    """
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-04-18T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2025-04-19T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 500, "Wydatek", "2025-04-20T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 300, "Wydatek", "2025-04-21T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "holiday_payday.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    assert (out["month"] == pd.Period("2025-04", freq="M")).all()


def test_assign_periods_year_rollover(tmp_path: Path) -> None:
    """Grudzień -> styczeń: granica i etykieta okresu przechodzą przez rok bez błędu."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-12-19T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2025-12-30T00:00:00.000Z"),
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-01-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-01-25T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "year_rollover.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    # 2025-12-21 to niedziela -> granica na piątek 2025-12-19.
    assert _month_on(out, "2025-12-19") == pd.Period("2025-12", freq="M")
    assert _month_on(out, "2025-12-30") == pd.Period("2025-12", freq="M")
    assert _month_on(out, "2026-01-21") == pd.Period("2026-01", freq="M")


def test_assign_periods_boundary_date_starts_new_window(tmp_path: Path) -> None:
    """Transakcja dokładnie w dniu przesuniętej granicy należy do NOWEGO okresu."""
    rows = [
        _mk_row("PKO", "Zakupy", 100, "Wydatek", "2026-11-19T00:00:00.000Z"),  # dzień przed granicą
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-11-20T00:00:00.000Z"),  # granica
    ]
    df = data.load(_write_csv(rows, tmp_path / "boundary_inclusive.csv"))
    out = data.assign_periods(df, mode="wyplata", payday=21)
    assert _month_on(out, "2026-11-19") == pd.Period("2026-10", freq="M")
    assert _month_on(out, "2026-11-20") == pd.Period("2026-11", freq="M")


def test_split_periods_wyplata_mode_rebuckets_around_payday(tmp_path: Path) -> None:
    """
    split_periods w trybie 'wyplata' łączy wypłatę z wydatkami z tego samego
    cyklu, nawet gdy kalendarzowo znalazłyby się w różnych miesiącach - to
    strukturalna naprawa błędu, dla którego powstaje cała ta zmiana.

    Wypłata za grudzień wpływa 19.12.2025 (piątek, bo 21.12 to niedziela) i
    otwiera cykl "2025-12". Wydatek z 20.12 jest kalendarzowo też grudniowy,
    ale wydatek z 30.11 (kalendarzowo listopad) w trybie kalendarzowym
    trafiłby do innego miesiąca niż ta sama wypłata - w trybie 'wyplata'
    30.11 nadal należy do POPRZEDNIEGO cyklu ("2025-11"), bo cykl grudniowy
    zaczyna się dopiero 19.12. Test dokumentuje więc, że granica realnie się
    przesuwa, nie że wszystko ląduje w jednym worku.
    """
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-11-21T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 400, "Wydatek", "2025-11-30T00:00:00.000Z"),
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2025-12-19T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 800, "Wydatek", "2025-12-20T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "split_wyplata.csv"))
    profile = {
        "osoba": {"tryb_okresu": "wyplata", "dzien_wyplaty": 21},
        "okresy": {"regime_change_date": "2020-01-01"},
    }
    windows = data.split_periods(df, profile)
    active = windows["active"]
    flow = data.monthly_flow(active, ["Konto oszczędnościowe"], drop_incomplete=False)

    nov = flow.loc[pd.Period("2025-11", freq="M")]
    dec = flow.loc[pd.Period("2025-12", freq="M")]
    assert nov["przychod"] == pytest.approx(5000)
    assert nov["wydatki"] == pytest.approx(400)  # 30.11 wciąż w cyklu listopadowym
    assert dec["przychod"] == pytest.approx(5000)
    assert dec["wydatki"] == pytest.approx(800)  # 20.12, po przesuniętej granicy 19.12


def test_split_periods_kalendarzowy_default_unchanged(sample_df: pd.DataFrame) -> None:
    """Brak tryb_okresu w profilu = zachowanie identyczne z dotychczasowym."""
    profile = {"okresy": {"regime_change_date": "2020-01-01"}}
    windows = data.split_periods(sample_df, profile)
    expected_months = sample_df["date"].dt.to_period("M")
    pd.testing.assert_series_equal(
        windows["active"]["month"].reset_index(drop=True),
        expected_months.reset_index(drop=True),
        check_names=False,
    )


def test_monthly_trends_wyplata_mode_reports_okres_od_do(tmp_path: Path) -> None:
    """monthly_trends w trybie 'wyplata' dorzuca realne granice okresu do wyniku."""
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-11-20T00:00:00.000Z"),
        _mk_row("PKO", "Zakupy", 1000, "Wydatek", "2026-11-25T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "trends_wyplata.csv"))
    profile = {
        "osoba": {"tryb_okresu": "wyplata", "dzien_wyplaty": 21},
        "okresy": {"regime_change_date": "2020-01-01"},
    }
    active = data.split_periods(df, profile)["active"]
    result = data.monthly_trends(active, ["Konto oszczędnościowe"])

    assert result["last_month"] == "2026-11"
    assert result["okres_od"] == "2026-11-20"
    assert result["okres_do"] is not None


def _loan(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "nazwa": "karnet Opener 2027",
        "kwota": 945,
        "konto_zrodlowe": "Konto oszczędnościowe",
        "rata_miesieczna": 94.5,
        "pierwsza_rata": "2026-09",
        "ostatnia_rata": "2027-07",
    }
    base.update(overrides)
    return base


def test_self_loan_progress_on_track_when_all_installments_paid(tmp_path: Path) -> None:
    rows = [
        _mk_row(
            "PKO",
            "Przelew, wypłata",
            94.5,
            "Wydatek",
            f"2026-{month:02d}-05T00:00:00.000Z",
            True,
            "rata",
        )
        for month in (9,)
    ] + [
        _mk_row(
            "Konto oszczędnościowe",
            "Przelew, wypłata",
            94.5,
            "Przychód",
            "2026-09-05T00:00:00.000Z",
            True,
            "rata",
        )
    ]
    df = data.load(_write_csv(rows, tmp_path / "loan_on_track.csv"))

    result = data.self_loan_progress(
        df, _loan(), ["Konto oszczędnościowe"], today=pd.Period("2026-09", freq="M")
    )

    assert result["raty_zalegle"] == 0
    assert result["na_czas"] is True
    assert result["splacono_total"] == pytest.approx(94.5)
    assert result["pozostalo_do_splaty"] == pytest.approx(945 - 94.5)


def test_self_loan_progress_flags_overdue_installment(tmp_path: Path) -> None:
    # Wrzesień: brak wpłaty raty w ogóle.
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-09-10T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "loan_overdue.csv"))

    result = data.self_loan_progress(
        df, _loan(), ["Konto oszczędnościowe"], today=pd.Period("2026-09", freq="M")
    )

    assert result["raty_zalegle"] == 1
    assert result["na_czas"] is False
    assert result["harmonogram"][0]["status"] == "zalegle"


def test_self_loan_progress_future_months_are_not_overdue(tmp_path: Path) -> None:
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-09-10T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "loan_future.csv"))

    result = data.self_loan_progress(
        df, _loan(), ["Konto oszczędnościowe"], today=pd.Period("2026-09", freq="M")
    )

    future_statuses = {row["status"] for row in result["harmonogram"][1:]}
    assert future_statuses == {"przyszly"}


def test_self_loan_progress_unrelated_transfer_does_not_count_as_repayment(
    tmp_path: Path,
) -> None:
    """Transfer PKO -> Revolut nie jest spłatą raty na konto oszczędnościowe."""
    rows = [
        _mk_row(
            "PKO", "Przelew, wypłata", 94.5, "Wydatek", "2026-09-05T00:00:00.000Z", True, "rev"
        ),
        _mk_row(
            "Revolut", "Przelew, wypłata", 94.5, "Przychód", "2026-09-05T00:00:00.000Z", True, "rev"
        ),
    ]
    df = data.load(_write_csv(rows, tmp_path / "loan_unrelated_transfer.csv"))

    result = data.self_loan_progress(
        df, _loan(), ["Konto oszczędnościowe"], today=pd.Period("2026-09", freq="M")
    )

    assert result["splacono_total"] == pytest.approx(0.0)
    assert result["raty_zalegle"] == 1


def test_self_loan_progress_requires_source_account_to_be_savings_account(
    tmp_path: Path,
) -> None:
    rows = [
        _mk_row("PKO", "Wynagrodzenie", 5000, "Przychód", "2026-09-10T00:00:00.000Z"),
    ]
    df = data.load(_write_csv(rows, tmp_path / "loan_bad_account.csv"))

    with pytest.raises(ValueError):
        data.self_loan_progress(df, _loan(), ["Inne konto oszczędnościowe"])
