from pathlib import Path

from personal_finance_dashboard import data, wallet_api


def _record(value: float, record_type: str, account: str, transfer: bool) -> dict[str, object]:
    return {
        "accountName": account,
        "amount": {"value": value, "currencyCode": "PLN"},
        "convertedAmount": {"value": value, "currencyCode": "PLN"},
        "category": {"name": "Rent"},
        "recordType": record_type,
        "counterParty": "Landlord; Sp. z o.o.",
        "note": "line1\nline2",
        "labels": [{"name": "a"}, {"name": "b"}],
        "recordDate": "2026-01-31T23:30:00.000Z",
        "transfer": {"transferId": "t1"} if transfer else None,
    }


def test_records_round_trip_through_data_load(tmp_path: Path) -> None:
    records = [
        _record(-100.5, "expense", "PKO", True),
        _record(100.5, "income", "Skarpeta", True),
    ]
    df = wallet_api.records_to_frame(records, {"Rent": "Czynsz"})
    path = tmp_path / "out.csv"
    wallet_api.write_csv(df, path)

    loaded = data.load(path)

    assert list(loaded["amount"]) == [100.5, 100.5]  # unsigned, like the export
    assert set(loaded["type"]) == {data.TYPE_EXPENSE, data.TYPE_INCOME}
    assert set(loaded["category"]) == {"Czynsz"}
    assert loaded["transfer"].all()
    assert loaded["payee"].iloc[0] == "Landlord; Sp. z o.o."
    assert loaded["labels"].iloc[0] == "a|b"
    assert str(loaded["month"].iloc[0]) == "2026-02"  # UTC -> Warsaw shifts the day
    assert len(data.audit_transfers(loaded).pairs) == 1


def test_read_token_from_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    import pytest

    assert isinstance(monkeypatch, pytest.MonkeyPatch)
    monkeypatch.delenv(wallet_api.TOKEN_ENV, raising=False)
    env = tmp_path / ".env"
    env.write_text(f'{wallet_api.TOKEN_ENV}="abc"\n', encoding="utf-8")
    assert wallet_api.read_token(env) == "abc"
    with pytest.raises(wallet_api.WalletApiError):
        wallet_api.read_token(tmp_path / "missing.env")


def test_plan_ppk_update_adds_only_missing_and_corrects_balance(tmp_path: Path) -> None:
    import pandas as pd

    cols = ["ordered", "valued", "kind", "period", "amount", "balance"]
    rows = [  # newest first, like the provider's export
        ["2026-02-14", "2026-02-16", "Wpłata pracownika", "01-2026", 100.0, 460.0],
        ["2026-01-14", "2026-01-16", "Wpłata pracownika", "12-2025", 100.0, 350.0],
    ]
    path = tmp_path / "ppk.ods"
    pd.DataFrame(rows, columns=cols).to_excel(path, engine="odf", index=False)
    existing = [
        {
            "recordDate": "2026-01-14T12:00:00Z",
            "amount": {"value": 100.0},
            "note": "Wpłata pracownika",
        }
    ]

    plan = wallet_api.plan_ppk_update(path, existing, current_balance=100.0)

    assert [r["amount"]["value"] for r in plan] == [100.0, 260.0]  # new deposit + gain
    assert plan[-1]["categoryId"] == wallet_api.PPK_CAT_GAIN
    assert wallet_api.plan_ppk_update(path, [*existing, plan[0]], 200.0 + 260.0) == []
