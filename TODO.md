# TODO / roadmapa

Repo nie ma zdalnego remote w tej chwili, więc to jest lista zadań zamiast
GitHub Issues. Po wypchnięciu na GitHub warto przenieść każdą sekcję do
osobnego issue.

Zasada dla każdego zadania poniżej: implementacja idzie za wzorcem
`validate`/`analyze` w `src/personal_finance_dashboard/cli.py` — funkcja w `data.py` (czysta,
testowalna), cienki wrapper w `cli.py` (JSON na stdout + plik na dysk),
test w `tests/unit/test_data.py`. Nie omijaj CLI pisząc logikę w komendzie
`.claude/commands/*.md` — to dokładnie ten koszt tokenów, którego CLI ma
unikać.

## Znane niedoróbki (bare minimum tej sesji)

- [ ] `stopa_oszczedzania` w raporcie `analyze` jest zaokrąglana do 0 przez
      `.round(0)` na całej tabeli (to ułamek 0-1, nie PLN). Formatować
      osobno jako procent.
- [ ] Hook `post_gen_project.py` szablonu Copier (git init / uv sync /
      pre-commit install / AGENTS.md) nie odpalił się automatycznie mimo
      `--trust` w środowisku, w którym powstało to repo — zrobione ręcznie.
      Sprawdź na docelowej maszynie, czy to był tylko quirk sandboksa.
- [ ] `copier.yml` w szablonie dołącza `GEMINI.md` zawsze przy
      `use_ai_agents=true`, niezależnie od wyboru w `ai_agents` — usunięty
      ręcznie. Warto zgłosić w `Konstantysz/python-repository-template`.
- [ ] `AGENTS.md` to ręczna kopia `CLAUDE.md` — zsynchronizuj po każdej
      zmianie tego drugiego (albo zrób z tego pre-commit hook).

**Naprawione po weryfikacji "świeży clone od zera" (warte odnotowania, bo
poprzednia sesja tego nie złapała — testy end-to-end szły na dużym,
13-miesięcznym syntetycznym CSV, a nie na minimalnym przypadku):**

- ~~`config/profile.example.yaml` nie trafił do archiwum repo~~ — plik
  istniał lokalnie podczas tworzenia, ale nigdy nie został skopiowany do
  `personal_finance_dashboard/config/`, więc zniknął przy pakowaniu. Naprawione.
- ~~`detect_fixed_costs` rzucał `KeyError` przy pustym wyniku~~ —
  `pd.DataFrame([])` z pustej listy nie ma kolumny `mediana_miesieczna`,
  `sort_values` na niej wybuchał. Występowało przy każdym CSV krótszym niż
  3 miesiące (dokładnie przypadek "dopiero zacząłem używać tego repo").
  Naprawione + dodany test regresyjny
  (`test_detect_fixed_costs_empty_result_does_not_crash`).

**Wniosek na przyszłość:** przy kolejnych komendach (`monthly`, `category`,
`invest`, `goal`) testuj end-to-end zarówno na pełnym datasecie, jak i na
minimalnym (1 miesiąc, zero wydatków, zero kategorii) — edge case'y przy
starcie z pustym/małym repo są dokładnie tym, co realny użytkownik robi
najpierw.

## `personal-finance-dashboard monthly` — zamknięcie miesiąca

Spec: `.claude/commands/miesiac.md`. Porównanie ostatniego pełnego miesiąca
z poprzednim, rolling 3M, tym samym miesiącem rok wcześniej (z zastrzeżeniem
o granicy ACTIVE/ARCHIVE). Przypomnienie o deadline IKZE w listopadzie/grudniu.

## `personal-finance-dashboard category <name>` — deep dive w kategorię

Spec: `.claude/commands/kategoria.md`. Rozkład kwot, top kontrahenci, trend
rolling 3M, kontekst z ARCHIVE z zastrzeżeniem o zmianie stylu życia.

## `personal-finance-dashboard invest` — plan inwestycyjny

Spec: `.claude/commands/inwestycje.md`. Wymaga wcześniej: `check_parameters_freshness`
(już jest w `data.py`) + realny bilans z `analyze`. Dwa scenariusze zawsze
(ostrożny/bazowy), nigdy jedna liczba.

## `personal-finance-dashboard podatki` (albo osobna flaga `invest --tax`) — IKE/IKZE

Spec: `.claude/commands/podatki.md`. Osobna komenda czy flaga do `invest` —
do decyzji przy implementacji, w tej sesji nazwa robocza nie została ustalona.

## `personal-finance-dashboard goal <name>` — symulacja celu

Spec: `.claude/commands/cel.md`. Trzy scenariusze (ostrożny/bazowy/zdarzenie
losowe), sezonowość z ARCHIVE uwzględniona w rocznej projekcji.

## Do rozważenia, nie zaplanowane

- [ ] `.claude/rules/` ze scope `paths:` — pominięte w tej sesji, bo repo
      jest jednym małym pakietem bez podfolderów wymagających różnych
      reguł. Rozważ, jeśli `src/personal_finance_dashboard/` urośnie w kilka modułów o różnych
      konwencjach.
- [ ] Hook blokujący (`block_raw_csv_read.py`) łapie tylko `Read`/`View`/
      `Bash`. Jeśli dojdzie narzędzie do edycji plików, sprawdź, czy też
      powinno być objęte matcherem.
- [ ] CI (`.github/workflows/ci.yml`) nie ma jeszcze kroku na testy hooka
      (`.claude/hooks/block_raw_csv_read.py`) — obecnie testowany tylko
      ręcznie przy tworzeniu.
