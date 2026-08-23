---
description: Plan inwestycyjny na bazie profilu i aktualnych parametrów rynkowych
---

> **Status: spec, nie implementacja.** Odpowiadający subcommand CLI
> (`personal-finance-dashboard invest`) to na razie stub zwracający kod błędu 2 — patrz
> `TODO.md`. Ten plik opisuje DOCELOWE zachowanie, nie sposób na
> obejście braku implementacji. **Nie realizuj tego ręcznie** wczytując
> `data/raw/*.csv` do kontekstu (i tak zablokowane hookiem) — to jest
> dokładnie ten wzorzec (liczenie w kontekście rozmowy), którego CLI ma
> unikać. Zamiast tego: powiedz użytkownikowi, że to niezaimplementowane,
> i zaproponuj albo zaimplementowanie subcommand w `src/personal_finance_dashboard/` wg
> wzorca `validate`/`analyze`, albo poczekanie.


**Zanim policzysz cokolwiek:**

1. Sprawdź `last_verified` w `config/parameters.yaml`. Starsze niż 60 dni —
   powiedz użytkownikowi, że parametry wymagają odświeżenia, i podaj źródła.
   Nie licz na przeterminowanych danych bez ostrzeżenia.
2. Sprawdź `stan_wdrozenia` w profilu. Jeżeli użytkownik ma już jakieś pozycje —
   planujesz **kolejny krok**, nie zaczynasz od zera.
3. Sprawdź, ile realnie zostaje miesięcznie (bilans z `/analiza`). Plan
   inwestycyjny przekraczający realną nadwyżkę jest bezużyteczny. Jeżeli bilans
   jest ujemny — powiedz to i zapytaj, czy planujemy mimo to, czy najpierw
   zajmujemy się przepływem.

**Kolejność, nie do negocjacji:**
1. Poduszka finansowa = próg przetrwania × liczba miesięcy (ustal z użytkownikiem,
   typowo 3–6 przy stabilnym dochodzie). Płynna, dostępna od ręki.
2. Dopiero nadwyżka ponad poduszkę idzie w cele.
3. Cel krótkoterminowy (< 5 lat) — instrumenty o niskiej zmienności. Akcje
   odpadają: przy horyzoncie 3 lat ryzyko, że trzeba sprzedawać w dołku, jest realne.
4. Cel długoterminowy (> 10 lat) — tu ma sens część akcyjna.

**Co przedstawiasz:**
- podział kapitału startowego i wpłaty miesięcznej między cele
- dla każdego celu: instrumenty, uzasadnienie mechaniką (nie "bo dobre"),
  koszty, płynność, opodatkowanie
- ile z tego mieści się w IKE i IKZE w tym roku (limity z parameters.yaml)
- **dwa scenariusze** projekcji: ostrożny i bazowy. Nigdy jedna liczba.
- co się dzieje, jeżeli wpłaty spadną o 30% albo pojawi się większy wydatek

**Uczciwość rachunku:**
- odsetki od obligacji poza IKE/IKZE podlegają podatkowi Belki 19%. Podawaj
  netto, nie brutto.
- porównuj z alternatywami, których użytkownik nie rozważa (konto oszczędnościowe
  na 6% netto ≈ 4,86% vs EDO 5,35% brutto ≈ 4,33% netto — to nie jest oczywiste
  zwycięstwo obligacji, jak było przy 8%)
- jeżeli plan opiera się na założeniu, które w danych rynkowych już nie
  obowiązuje — powiedz to wprost

Raport: `output/reports/inwestycje_YYYY-MM-DD.md`.
Zakończ zdaniem, że to symulacja na założeniach, nie porada inwestycyjna.
