"""
Jedyne źródło prawdy dla wczytywania i czyszczenia danych transakcyjnych.

`cli.py` importuje stąd i jest jedynym dozwolonym miejscem wywołującym te
funkcje na surowym CSV. Agent (Claude Code) nie czyta data/raw/*.csv
bezpośrednio — patrz CLAUDE.md i .claude/settings.json (hook blokujący).
Nie duplikuj logiki transferów ani podziału okresów gdzie indziej — trzy
błędy w poprzedniej (ręcznej) analizie wzięły się dokładnie z tego, że
reguły były przepisywane ad hoc przy każdym pytaniu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

TYPE_INCOME = "Przychód"
TYPE_EXPENSE = "Wydatek"


# --------------------------------------------------------------------------
# Wczytywanie
# --------------------------------------------------------------------------


def load(csv_path: str | Path) -> pd.DataFrame:
    """Wczytuje eksport Wallet i normalizuje typy. Nie filtruje niczego."""
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8", dtype=str)

    required = {"account", "category", "amount", "type", "date", "transfer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Brakuje kolumn w CSV: {sorted(missing)}")

    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ".", regex=False), errors="coerce")
    if "ref_currency_amount" in df.columns:
        df["ref_amount"] = pd.to_numeric(
            df["ref_currency_amount"].str.replace(",", ".", regex=False),
            errors="coerce",
        )
    else:
        df["ref_amount"] = df["amount"]

    df["date"] = pd.to_datetime(df["date"], format="ISO8601", utc=True)
    # Wallet zapisuje w UTC; konwersja na czas lokalny, bo cykle wypłatowe
    # i granice miesięcy liczymy w czasie warszawskim.
    df["date"] = df["date"].dt.tz_convert("Europe/Warsaw").dt.tz_localize(None)

    df["transfer"] = df["transfer"].astype(str).str.strip().str.lower() == "true"
    df["type"] = df["type"].astype(str).str.strip()

    for col in ("account", "category", "payee", "note", "labels", "payment_type"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["month"] = df["date"].dt.to_period("M")
    return df.sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------
# Transfery
# --------------------------------------------------------------------------


@dataclass
class TransferAudit:
    """Wynik dopasowania par transferów. Sieroty ZAWSZE pokaż użytkownikowi."""

    pairs: pd.DataFrame = field(default_factory=pd.DataFrame)
    orphans: pd.DataFrame = field(default_factory=pd.DataFrame)
    malformed: pd.DataFrame = field(default_factory=pd.DataFrame)

    def summary(self) -> str:
        return (
            f"Pary transferów: {len(self.pairs)}. "
            f"Sieroty: {len(self.orphans)}. "
            f"Błędne pary (obie strony tego samego typu): {len(self.malformed)}."
        )


def audit_transfers(df: pd.DataFrame) -> TransferAudit:
    """
    Dopasowuje transfery w pary po kluczu (date, amount).

    Poprawna para: dokładnie 2 rekordy, jeden Wydatek + jeden Przychód.
    Wszystko inne wymaga decyzji użytkownika.
    """
    t = df[df["transfer"]].copy()
    if t.empty:
        return TransferAudit()

    grouped = t.groupby(["date", "amount"], sort=False)

    pair_rows, orphan_rows, malformed_rows = [], [], []
    for (dt, amt), g in grouped:
        if len(g) == 1:
            orphan_rows.append(g)
        elif len(g) == 2 and set(g["type"]) == {TYPE_INCOME, TYPE_EXPENSE}:
            src = g[g["type"] == TYPE_EXPENSE].iloc[0]
            dst = g[g["type"] == TYPE_INCOME].iloc[0]
            pair_rows.append(
                {
                    "date": dt,
                    "amount": amt,
                    "from_account": src["account"],
                    "to_account": dst["account"],
                    "note": dst.get("note", ""),
                }
            )
        else:
            malformed_rows.append(g)

    return TransferAudit(
        pairs=pd.DataFrame(pair_rows),
        orphans=pd.concat(orphan_rows) if orphan_rows else pd.DataFrame(),
        malformed=pd.concat(malformed_rows) if malformed_rows else pd.DataFrame(),
    )


# --------------------------------------------------------------------------
# Podstawowe filtry — używaj ICH, nie własnych warunków
# --------------------------------------------------------------------------


def income(df: pd.DataFrame) -> pd.DataFrame:
    """Rzeczywisty przychód: transfery NIE są przychodem."""
    return df[(df["type"] == TYPE_INCOME) & (~df["transfer"])]


def expenses(df: pd.DataFrame) -> pd.DataFrame:
    """Rzeczywisty wydatek: transfery NIE są wydatkiem."""
    return df[(df["type"] == TYPE_EXPENSE) & (~df["transfer"])]


def savings(df: pd.DataFrame, savings_accounts: list[str]) -> pd.DataFrame:
    """
    Oszczędności = wyłącznie przychodząca strona transferu na konto
    oznaczone w profilu jako oszczędnościowe.

    Liczenie obu stron pary podwaja kwotę. Liczenie wszystkich transferów
    wciąga w to przesunięcia PKO -> Revolut, które oszczędnościami nie są.
    """
    if not savings_accounts:
        raise ValueError(
            "Lista kont oszczędnościowych jest pusta. Uzupełnij config/profile.yaml "
            "— nie zgaduj po nazwach kont."
        )
    return df[df["transfer"] & (df["type"] == TYPE_INCOME) & (df["account"].isin(savings_accounts))]


# --------------------------------------------------------------------------
# Podział okresów
# --------------------------------------------------------------------------


def load_profile(path: str | Path = "config/profile.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Brak {p}. Uruchom /profil zanim zaczniesz analizę.")
    with p.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def split_periods(df: pd.DataFrame, profile: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Zwraca okna: archive / active / recent / all.

    ACTIVE to domyślne okno KAŻDEJ analizy budżetowej. ARCHIVE służy tylko do
    sezonowości, inflacji koszyka i historii — nie do średnich wydatków.
    """
    change = pd.Timestamp(profile["okresy"]["regime_change_date"])

    active = df[df["date"] >= change]
    archive = df[df["date"] < change]

    if active.empty:
        recent = active
    else:
        last_full = active["month"].max() - 1
        recent = active[active["month"] > (last_full - 3)]

    return {"all": df, "archive": archive, "active": active, "recent": recent}


def detect_regime_change(
    df: pd.DataFrame, keywords: list[str] | None = None
) -> tuple[pd.Period | None, pd.Series]:
    """
    Szuka skokowej zmiany poziomu w kategoriach mieszkaniowych.
    Wynik to PROPOZYCJA do potwierdzenia przez użytkownika, nie ustalenie.
    """
    keywords = keywords or [
        "czynsz",
        "mieszkan",
        "media",
        "prąd",
        "prad",
        "internet",
        "gaz",
        "woda",
        "wynajem",
    ]
    exp = expenses(df).copy()
    mask = exp["category"].str.lower().str.contains("|".join(keywords), na=False)
    housing = exp[mask]
    if housing.empty:
        return None, pd.Series(dtype=float)

    # Uzupełnij brakujące miesiące zerami — inaczej "kategoria pojawiła się
    # od zera" jest nieodróżnialne od "kategoria istniała cały czas".
    monthly = housing.groupby("month")["amount"].sum()
    full_idx = pd.period_range(df["month"].min(), df["month"].max(), freq="M")
    monthly = monthly.reindex(full_idx, fill_value=0.0)

    # Przypadek 1: kategoria po prostu pojawia się i już nie znika.
    # Wtedy pierwszy niezerowy miesiąc JEST datą przełomu.
    nonzero = monthly[monthly > 0]
    if not nonzero.empty:
        first = nonzero.index[0]
        before = monthly[monthly.index < first]
        after = monthly[monthly.index >= first]
        if len(before) >= 3 and (before == 0).all() and (after > 0).mean() >= 0.8:
            return first, monthly

    # Przypadek 2: skok poziomu. Szukaj podziału maksymalizującego różnicę
    # median, wymagając >=3 miesiące po obu stronach.
    best: pd.Period | None = None
    best_ratio = 0.0
    for i in range(3, len(monthly) - 2):
        b, a = monthly.iloc[:i], monthly.iloc[i:]
        if b.median() <= 0:
            continue
        ratio = a.median() / b.median()
        if ratio > best_ratio and ratio > 1.8:
            best, best_ratio = monthly.index[i], ratio

    fallback: pd.Period = monthly.idxmax()  # type: ignore[assignment]
    return (best or fallback), monthly


# --------------------------------------------------------------------------
# Koszty stałe
# --------------------------------------------------------------------------


def detect_fixed_costs(
    df: pd.DataFrame, min_months: int = 3, tolerance: float = 0.20
) -> pd.DataFrame:
    """
    Kandydaci na koszty stałe: ta sama (kategoria, payee) w >= min_months
    kolejnych miesiącach, kwota w granicach +/- tolerance wokół mediany.

    To HEURYSTYKA. Wynik pokaż użytkownikowi do zatwierdzenia — nie traktuj
    jako ustalonego faktu.
    """
    exp = expenses(df).copy()
    exp["key"] = exp["category"] + " | " + exp.get("payee", "")

    out = []
    for key, g in exp.groupby("key"):
        per_month = g.groupby("month")["amount"].sum()
        if len(per_month) < min_months:
            continue
        med = per_month.median()
        if med <= 0:
            continue
        within = ((per_month - med).abs() <= tolerance * med).sum()
        if within >= min_months and within / len(per_month) >= 0.6:
            out.append(
                {
                    "pozycja": key,
                    "mediana_miesieczna": round(med, 2),
                    "miesiecy": len(per_month),
                    "stabilnych": int(within),
                    "ostatni_miesiac": str(per_month.index.max()),
                }
            )

    columns = ["pozycja", "mediana_miesieczna", "miesiecy", "stabilnych", "ostatni_miesiac"]
    if not out:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(out, columns=columns)
        .sort_values("mediana_miesieczna", ascending=False)
        .reset_index(drop=True)
    )


# --------------------------------------------------------------------------
# Parametry rynkowe — świeżość
# --------------------------------------------------------------------------


def check_parameters_freshness(
    path: str | Path = "config/parameters.yaml", max_age_days: int = 60
) -> dict[str, Any]:
    """Zwraca, czy config/parameters.yaml jest starszy niż max_age_days."""
    import datetime as _dt

    p = Path(path)
    if not p.exists():
        return {"exists": False, "stale": True, "age_days": None}

    with p.open(encoding="utf-8") as f:
        params: dict[str, Any] = yaml.safe_load(f)

    last_verified = params.get("last_verified")
    if last_verified is None:
        return {"exists": True, "stale": True, "age_days": None}

    verified_date = pd.Timestamp(last_verified).date()
    age_days = (_dt.date.today() - verified_date).days
    return {"exists": True, "stale": age_days > max_age_days, "age_days": age_days}


# --------------------------------------------------------------------------
# Zestawienie miesięczne
# --------------------------------------------------------------------------


def monthly_flow(df: pd.DataFrame, savings_accounts: list[str]) -> pd.DataFrame:
    """Przychód / wydatki / oszczędności / bilans, miesiąc po miesiącu."""
    inc = income(df).groupby("month")["amount"].sum()
    exp = expenses(df).groupby("month")["amount"].sum()
    sav = savings(df, savings_accounts).groupby("month")["amount"].sum()

    out = pd.DataFrame({"przychod": inc, "wydatki": exp, "oszczednosci": sav})
    out = out.fillna(0.0)
    out["bilans"] = out["przychod"] - out["wydatki"] - out["oszczednosci"]
    out["stopa_oszczedzania"] = out["oszczednosci"] / out["przychod"].replace(0, pd.NA)
    return out


def rolling_view(flow: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Rolling + ostatni miesiąc osobno.

    Powód: średnia z całego okresu potrafi pokazywać deficyt w momencie, gdy
    ostatni miesiąc jest już dodatni. Zawsze raportuj obie liczby.
    """
    r = flow[["przychod", "wydatki", "oszczednosci", "bilans"]].rolling(window).mean()
    r.columns = [f"{c}_r{window}m" for c in r.columns]
    return flow.join(r)
