---
description: Profilowanie użytkownika — uruchom raz, potem tylko aktualizacje
---

> **Status: spec, nie implementacja.** Nie ma jeszcze `personal-finance-dashboard profile`
> w CLI (patrz `TODO.md`). Realizuj to jako zwykły dialog: zadawaj pytania,
> potem sam zapisz odpowiedzi do `config/profile.yaml` (skopiuj strukturę
> z `config/profile.example.yaml`). To nie wymaga czytania CSV, więc hook
> Cię tu nie zablokuje — ale trzymaj się formatu YAML z przykładu.


Zbuduj lub zaktualizuj `config/profile.yaml` na bazie `config/profile.example.yaml`.

Najpierw uruchom `uv run personal-finance-dashboard validate` (albo użyj wyniku, jeśli już był
uruchomiony w tej sesji). Raport w `output/reports/waliduj_*.md` zawiera
sekcję "## Konta" z listą kont, liczbą transakcji i zakresem dat na każdym —
przeczytaj tę sekcję pliku, nie surowy CSV. Bez tego nie da się sensownie
zapytać o konta.

Zadawaj pytania **pojedynczo**, czekając na odpowiedź. Nie wysyłaj listy dziesięciu
pytań naraz. Kolejność:

1. Wiek.
2. Forma zatrudnienia (etat / JDG) — determinuje limit IKZE.
3. Próg podatkowy (12% / 32%) — determinuje wartość ulgi IKZE.
4. Dochód netto miesięcznie i czy jest stabilny.
5. **Konta**: pokaż wykrytą listę i zapytaj, które są oszczędnościowe, które bieżące,
   które wykluczyć z majątku (karta lunchowa itp.). To pytanie jest krytyczne —
   od niego zależy cała analiza oszczędności.
6. **Rzeczywiste salda** kont na dziś. Wyjaśnij po co: salda liczone z CSV to sumy
   narastające od początku eksportu, nie prawdziwe stany.
7. **Data przełomu**: pokaż datę, którą wykryłeś empirycznie ze skoku w kategoriach
   mieszkaniowych, i poproś o potwierdzenie lub korektę. Zapytaj też, czy w latach
   2022–2025 były inne istotne zmiany sytuacji (zmiana pracy, wyprowadzka, koniec
   studiów), które trzeba oznaczyć.
8. Cele krótkoterminowe: co, ile, do kiedy.
9. Cele długoterminowe.
10. Tolerancja ryzyka i poziom wiedzy.
11. **Stan wdrożenia**: czy IKE/IKZE są już założone, czy były wpłaty w tym roku,
    jakie instrumenty faktycznie posiada. Pytaj o stan faktyczny, nie o plany.
12. Instrumenty wykluczone i czy ktoś doradza z zewnątrz.

Na koniec pokaż wypełniony plik do zatwierdzenia, dopiero potem zapisz.
Zaproponuj `/waliduj` jako następny krok.
