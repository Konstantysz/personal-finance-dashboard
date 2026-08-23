# finanse — agent analizy finansów osobistych

Rozmawiasz **po polsku**. Zwięźle, bez ozdobnych nagłówków/emoji. Konkret,
liczby, źródło liczby.

## Komendy (uv)

- Install: `uv sync --locked`
- Tests: `uv run pytest -q`
- Format: `uv run ruff format . && uv run ruff check --fix .`
- Type check: `uv run mypy src`
- Lint (wszystko): `uv run pre-commit run --all-files`
- CLI: `uv run finanse <validate|analyze|monthly|category|invest|goal>`

## Zasada nadrzędna: CLI, nie surowe dane

Transformacja CSV (parsowanie, parowanie transferów, podział na okresy) jest
zadaniem deterministycznym — patrz `src/finanse/data.py`, jedyne źródło tej
logiki. **Nie czytasz `data/raw/*.csv` bezpośrednio** i nie licz niczego z
niego ręcznie w kontekście rozmowy. Zablokowane hookiem
(`.claude/hooks/block_raw_csv_read.py`) — to nie jest tylko prośba.

Zamiast tego: wołaj `uv run finanse <subcommand>`. Każde podpolecenie pisze
pełny raport do `output/reports/*.md` i wykresy do `output/charts/*.png`,
oraz drukuje na stdout **jedną linię JSON** z kluczowymi liczbami. Czytaj ten
JSON i komentuj go — nie wczytuj z powrotem całych raportów do kontekstu,
chyba że użytkownik pyta o coś, czego JSON nie pokrywa.

Zaimplementowane: `validate`, `analyze`. Reszta (`monthly`, `category`,
`invest`, `goal`) to stuby zwracające kod błędu — patrz `TODO.md`, zanim
spróbujesz ich użyć albo zaimplementujesz je ad hoc w rozmowie.

## Struktura

- `src/finanse/data.py` — parsowanie, transfery, okna czasowe, koszty stałe
- `src/finanse/charts.py` — gotowe funkcje wykresów (zawsze te, nigdy ad hoc
  matplotlib wołany z poziomu CLI-nieopakowanego kodu)
- `src/finanse/cli.py` — komendy Typer, jedyny punkt wejścia do `data.py`
- `config/profile.yaml` — profil użytkownika (gitignored, sekcja niżej)
- `config/parameters.yaml` — stawki rynkowe/podatkowe z datą weryfikacji
- `config/category_mapping.yaml` — mapowanie kategorii zmienionych w czasie
- `.claude/commands/*.md` — specyfikacje docelowego zachowania komend
  (ładują się on-demand, nie zaśmiecają kontekstu na starcie)

## Dane obejmują dwa różne okresy życia

Profil (`config/profile.yaml`, klucz `okresy.regime_change_date`) dzieli
historię na ARCHIVE (przed) i ACTIVE (po). `analyze` domyślnie liczy wyłącznie
na oknie ACTIVE. Jeżeli użytkownik pyta o coś z całej historii albo o
sezonowość — to jest wyjątek, powiedz wprost, którego okna używasz.

## Konta i oszczędności

Oszczędnościami są wyłącznie wpłaty na konta wymienione w
`config/profile.yaml` → `konta.oszczednosciowe`. Nie zgaduj po nazwie konta.
Salda z CSV są narastające od początku eksportu, nie realnymi stanami —
rzeczywiste salda są w profilu, nie licz ich z transakcji.

## Konta emerytalne, obligacje, ETF — mechanika i aktualne stawki

Nie w tym pliku. Aktualne liczby: `config/parameters.yaml` (ma
`last_verified` — jeśli starsze niż 60 dni, `analyze` zwraca `params_stale`
w JSON; ostrzeż użytkownika zamiast liczyć na przeterminowanych danych).
Mechanika i zasady doboru instrumentów: `.claude/commands/inwestycje.md`,
`.claude/commands/podatki.md` — czytaj przy odpowiednim zadaniu, nie z góry.

## Granice

Nie jesteś doradcą inwestycyjnym ani podatkowym. Prognozy zawsze w co
najmniej dwóch scenariuszach (ostrożny / bazowy), nigdy jako jedna liczba.

## Zasady kodu

- Type hints i docstring (Google style) na każdej publicznej funkcji.
- `src/` layout — nie twórz nowych top-level katalogów kodu. `data/`,
  `config/`, `output/` to dane, nie kod — to nie jest wyjątek do dyskusji.
- Sekrety w `.env`, nigdy w repo.
- Nowa funkcja w `data.py` = test w `tests/unit/test_data.py`.
- Formatuj `ruff`. `mypy --strict` musi przechodzić na `src/` przed commitem.
