---
description: Szczegółowa analiza jednej kategorii — /kategoria <nazwa>
---

> **Status: spec, nie implementacja.** Odpowiadający subcommand CLI
> (`personal-finance-dashboard category`) to na razie stub zwracający kod błędu 2 — patrz
> `TODO.md`. Ten plik opisuje DOCELOWE zachowanie, nie sposób na
> obejście braku implementacji. **Nie realizuj tego ręcznie** wczytując
> `data/raw/*.csv` do kontekstu (i tak zablokowane hookiem) — to jest
> dokładnie ten wzorzec (liczenie w kontekście rozmowy), którego CLI ma
> unikać. Zamiast tego: powiedz użytkownikowi, że to niezaimplementowane,
> i zaproponuj albo zaimplementowanie subcommand w `src/personal_finance_dashboard/` wg
> wzorca `validate`/`analyze`, albo poczekanie.


Argument: nazwa kategorii. Jeżeli brak lub niejednoznaczna — pokaż listę
dopasowań i zapytaj.

Analizuj:

**W oknie ACTIVE**
- suma, średnia miesięczna, mediana, odchylenie
- rozkład: histogram kwot pojedynczych transakcji
- trend rolling 3M
- top 10 kontrahentów (`payee`) z sumami i liczbą transakcji
- rozkład wg dnia tygodnia i dnia cyklu wypłatowego
- transakcje odstające (> średnia + 2σ) — wypisz z datą, kwotą, notatką

**Kontekst z ARCHIVE**
- jak ta kategoria wyglądała przed przeprowadzką
- **z zastrzeżeniem**: jeżeli to kategoria mieszkaniowa lub spożywcza,
  porównanie pokazuje zmianę stylu życia, nie rozrzutność. Napisz to.

**Wnioski**
- jaka część jest stała (nie do ruszenia), jaka zmienna
- gdzie realnie da się coś zmienić i o ile — z liczbą, nie "warto ograniczyć"
- czy widać wzorzec (zakupy pod koniec cyklu, kumulacja w weekendy)

Wykres: `output/charts/kategoria_<nazwa>.png` — przebieg miesięczny z zaznaczoną
linią przeprowadzki.

Nie moralizuj. Pokaż liczby i możliwości, decyzja należy do użytkownika.
