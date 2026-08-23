---
description: Kontrola jakości danych — uruchamiaj przy każdym nowym CSV
---

Uruchom `uv run personal-finance-dashboard validate` (opcjonalnie `--csv <ścieżka>` jeśli
użytkownik wskazał inny plik niż domyślny `data/raw/wallet_export.csv`).

To polecenie **jest** implementacją tej komendy — nie licz niczego ręcznie
z CSV, nie czytaj go bezpośrednio (i tak zablokowane hookiem).

Przeczytaj JSON ze stdout. Kluczowe pola: `transfer_orphans`,
`transfer_malformed`, `duplicates`, `large_transactions`, `sparse_months`.

Jeżeli którekolwiek z nich > 0 — **nie idź dalej automatycznie**. Otwórz
pełny raport (`report` w JSON, plik w `output/reports/`) tylko w zakresie
sekcji dotyczącej problemu, pokaż użytkownikowi konkrety (daty, kwoty) i
zapytaj, co to jest. Nie zgaduj.

Jeżeli wszystko czyste — powiedz to jednym zdaniem z liczbami z JSON
(zakres dat, liczba transakcji, liczba kont) i zaproponuj `/analiza`.
