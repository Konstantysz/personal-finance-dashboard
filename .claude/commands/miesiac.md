---
description: Zamknięcie miesiąca — porównanie nowego CSV z poprzednią analizą
---

> **Status: spec, nie implementacja.** Odpowiadający subcommand CLI
> (`personal-finance-dashboard monthly`) to na razie stub zwracający kod błędu 2 — patrz
> `TODO.md`. Ten plik opisuje DOCELOWE zachowanie, nie sposób na
> obejście braku implementacji. **Nie realizuj tego ręcznie** wczytując
> `data/raw/*.csv` do kontekstu (i tak zablokowane hookiem) — to jest
> dokładnie ten wzorzec (liczenie w kontekście rozmowy), którego CLI ma
> unikać. Zamiast tego: powiedz użytkownikowi, że to niezaimplementowane,
> i zaproponuj albo zaimplementowanie subcommand w `src/personal_finance_dashboard/` wg
> wzorca `validate`/`analyze`, albo poczekanie.


Do comiesięcznego użytku. Wymaga poprzedniego raportu w `output/reports/`.

1. Wczytaj nowy CSV, uruchom skróconą walidację (transfery, luki, anomalie).
2. Zidentyfikuj ostatni pełny miesiąc.
3. Porównaj go z:
   - poprzednim miesiącem
   - średnią rolling 3M
   - tym samym miesiącem rok wcześniej (jeżeli mieści się w ACTIVE; jeżeli
     wpada w ARCHIVE — powiedz, że porównanie jest niemiarodajne i dlaczego)

**Raport zamknięcia — maksymalnie jedna strona:**
- bilans miesiąca i czy dodatni
- 3 kategorie z największą zmianą w górę, 3 w dół — z kwotami
- czy oszczędności poszły zgodnie z planem
- czy pojawiła się nowa kategoria albo nowy koszt stały
- stan realizacji celów: ile odłożone, ile brakuje, czy tempo wystarcza
- jedno zdanie: co poszło dobrze, co wymaga uwagi

Jeżeli listopad lub grudzień — dopisz przypomnienie o deadline IKZE (31.12)
i ile limitu zostało niewykorzystane.

Zapisz `output/reports/miesiac_YYYY-MM.md`. Zaktualizuj wykres przepływu.
Nie generuj pełnego zestawu wykresów.
