---
description: Pełna analiza okna ACTIVE — przepływ, kategorie, koszty stałe
---

Wymaga `config/profile.yaml`. Jeżeli brak — powiedz użytkownikowi, że profil
nie istnieje, i zaproponuj `/profil` (komenda niezaimplementowana w CLI —
patrz `TODO.md`; do czasu implementacji zapytaj o dane profilu bezpośrednio
w rozmowie i zapisz je do `config/profile.yaml` ręcznie, wzorując się na
`config/profile.example.yaml`).

Uruchom `uv run personal-finance-dashboard analyze`. To polecenie samo liczy okno ACTIVE,
pisze raport i wykresy — nie duplikuj tej logiki w rozmowie.

Przeczytaj JSON. Kluczowe pola: `months_in_window`, `last_month_balance`,
`avg_balance`, `avg_balance_3m`, `fixed_costs_candidates`, `params_stale`.

**Zawsze pokaż `last_month_balance` obok `avg_balance`** — jeśli się różnią
kierunkiem (jedno dodatnie, drugie ujemne), to jest najważniejsza informacja
w odpowiedzi, nie szczegół na końcu.

Jeżeli `params_stale` jest `true` — zaznacz to, jeśli rozmowa dotyczy
inwestycji czy podatków; przy czystej analizie budżetu można pominąć.

Otwórz pełny raport (ścieżka w `report`) tylko jeśli użytkownik pyta o coś,
czego nie ma w JSON (konkretne kategorie, lista kosztów stałych do
zatwierdzenia). Wykresy są w `charts` — możesz je pokazać bezpośrednio.

Zakończ 2-3 konkretnymi propozycjami kolejnego kroku, dopasowanymi do tego,
co wyszło (np. jeśli `fixed_costs_candidates` > 0: zaproponuj przegląd i
zatwierdzenie listy; jeśli bilans ujemny: zaproponuj `/kategoria` na
największej pozycji z raportu).
