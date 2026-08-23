---
description: Symulacja celu finansowego — /cel <nazwa>
---

> **Status: spec, nie implementacja.** Odpowiadający subcommand CLI
> (`personal-finance-dashboard goal`) to na razie stub zwracający kod błędu 2 — patrz
> `TODO.md`. Ten plik opisuje DOCELOWE zachowanie, nie sposób na
> obejście braku implementacji. **Nie realizuj tego ręcznie** wczytując
> `data/raw/*.csv` do kontekstu (i tak zablokowane hookiem) — to jest
> dokładnie ten wzorzec (liczenie w kontekście rozmowy), którego CLI ma
> unikać. Zamiast tego: powiedz użytkownikowi, że to niezaimplementowane,
> i zaproponuj albo zaimplementowanie subcommand w `src/personal_finance_dashboard/` wg
> wzorca `validate`/`analyze`, albo poczekanie.


Argument: nazwa celu. Jeżeli jest w `config/profile.yaml` — weź parametry stamtąd.
Jeżeli nie — dopytaj o kwotę i termin, potem dopisz do profilu.

**Policz w obie strony:**

A) **Ile trzeba odkładać**, żeby osiągnąć kwotę X do daty Y — przy obecnym
   kapitale i realistycznym zwrocie. Podaj wymaganą wpłatę miesięczną.

B) **Kiedy cel zostanie osiągnięty** przy obecnym tempie oszczędzania — to jest
   ważniejsza liczba, bo opiera się na faktach, nie na deklaracji.

Jeżeli A > realna nadwyżka miesięczna z `/analiza` — **powiedz to wprost**.
Nie proponuj planu, którego użytkownik nie udźwignie. Zamiast tego pokaż opcje:
przesunięcie terminu, obniżenie kwoty, zwiększenie dochodu, cięcie kosztów
(z konkretnych kategorii i konkretnymi kwotami).

**Dobór instrumentów wg horyzontu:**
- < 2 lata: tylko płynne i nisko zmienne
- 2–5 lat: obligacje indeksowane, konto oszczędnościowe; akcje najwyżej marginalnie
- > 10 lat: część akcyjna ma sens

**Scenariusze — zawsze co najmniej trzy:**
- ostrożny (niższy zwrot, wyższa inflacja)
- bazowy
- ze zdarzeniem losowym: wypadnięcie 3 miesięcy wpłat albo wydatek 15 000 zł

Uwzględnij sezonowość z ARCHIVE: jeżeli użytkownik ma drogie miesiące
(wakacje, grudzień), realne roczne oszczędności są niższe niż 12 × miesięczna wpłata.
Policz to i pokaż różnicę.

Wykres: `output/charts/cel_<nazwa>.png` — narastanie kapitału, trzy scenariusze,
pozioma linia celu, pionowa linia terminu.

Raport: `output/reports/cel_<nazwa>_YYYY-MM-DD.md`.
