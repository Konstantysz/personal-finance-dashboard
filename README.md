# personal-finance-dashboard

Analiza finansów osobistych: CLI (działa samodzielnie) + agent Claude Code
(korzysta z tego samego CLI, nie z surowych danych bezpośrednio).

## Instalacja

```bash
uv sync --locked
cp config/profile.example.yaml config/profile.yaml   # wypełnij ręcznie albo przez agenta
# wrzuć eksport Wallet do data/raw/wallet_export.csv
```

## Użycie bez agenta

```bash
uv run personal-finance-dashboard validate                # kontrola jakości danych
uv run personal-finance-dashboard analyze                 # pełna analiza okna ACTIVE
```

Obie komendy piszą raport do `output/reports/` i (dla `analyze`) wykresy do
`output/charts/`, oraz drukują na stdout jedną linię JSON z kluczowymi
liczbami — wygodne do dalszego przetwarzania (`| python3 -m json.tool`,
`| jq`).

`monthly`, `category`, `invest`, `goal` są **zdefiniowane w CLI, ale
niezaimplementowane** — patrz `TODO.md` i specyfikacje w `.claude/commands/`.

## Użycie z Claude Code

```bash
claude
```

`CLAUDE.md` ładuje się automatycznie. Komendy slash w `.claude/commands/`:

| komenda | woła CLI | status |
|---|---|---|
| `/profil` | — (dialog + zapis YAML) | działa |
| `/waliduj` | `personal-finance-dashboard validate` | działa |
| `/analiza` | `personal-finance-dashboard analyze` | działa |
| `/miesiac` | `personal-finance-dashboard monthly` | spec, CLI to stub |
| `/kategoria <nazwa>` | `personal-finance-dashboard category` | spec, CLI to stub |
| `/inwestycje` | `personal-finance-dashboard invest` | spec, CLI to stub |
| `/podatki` | — | spec, brak decyzji o miejscu w CLI |
| `/cel <nazwa>` | `personal-finance-dashboard goal` | spec, CLI to stub |

Bezpośredni odczyt `data/raw/*.csv` przez agenta jest zablokowany hookiem
(`.claude/settings.json` → `.claude/hooks/block_raw_csv_read.py`) — nie
tylko zalecany przeciw, ale wymuszony. Cel: transformacja danych to zadanie
deterministyczne i powinno kosztować cykl CPU, nie tokeny.

## Rozwój

```bash
uv run pytest -q          # testy
uv run mypy src           # type check (--strict)
uv run ruff check --fix . && uv run ruff format .
uv run pre-commit run --all-files
```

## Struktura

```
CLAUDE.md / AGENTS.md      instrukcja agenta (AGENTS.md = ręczna kopia)
.claude/
  commands/                specyfikacje slash-komend
  hooks/block_raw_csv_read.py
  settings.json            rejestracja hooka
src/personal_finance_dashboard/
  data.py                  parsowanie, transfery, okna czasowe — jedno źródło prawdy
  charts.py                gotowe funkcje wykresów
  cli.py                   Typer, jedyny punkt wejścia do data.py
config/
  parameters.yaml          stawki rynkowe/podatkowe, z datą weryfikacji
  profile.yaml              profil użytkownika (gitignored)
  category_mapping.yaml    mapowanie zmienionych kategorii
data/raw/                  eksporty CSV (gitignored)
output/{reports,charts}/   wyniki (gitignored)
tests/unit/test_data.py    testy regresyjne na historyczne błędy interpretacji
TODO.md                    roadmapa (repo bez remote — surogat GitHub Issues)
```

## Trzy rzeczy, o których trzeba pamiętać

**1. Dane obejmują dwa różne życia.** Domyślne okno analizy to ACTIVE (od
`config/profile.yaml` → `okresy.regime_change_date`). Historia sprzed tej
daty służy do sezonowości i długoterminowych trendów, nie do średnich
wydatków bieżących.

**2. Transfery nie są przychodem ani wydatkiem.** Występują parami.
Oszczędnościami są wyłącznie wpłaty na konta wskazane w profilu jako
oszczędnościowe — logika w `src/personal_finance_dashboard/data.py`, przetestowana w
`tests/unit/test_data.py` właśnie pod kątem historycznych błędów
interpretacji tych danych.

**3. `config/parameters.yaml` się starzeje.** Oprocentowanie obligacji
zmienia się co miesiąc. `personal-finance-dashboard analyze` sprawdza wiek pliku i zwraca
`params_stale` w JSON — nie ignoruj tego przy pytaniach inwestycyjnych.

## Zastrzeżenie

Narzędzie analityczne, nie doradztwo inwestycyjne ani podatkowe.
