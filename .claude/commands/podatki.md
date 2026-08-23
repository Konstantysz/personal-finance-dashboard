---
description: Optymalizacja IKE/IKZE — limity roku bieżącego i deadline 31.12
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


**Ustal najpierw:**
- dzisiejszą datę i ile dni zostało do 31 grudnia
- rok podatkowy i limity z `config/parameters.yaml`
- formę zatrudnienia (etat vs JDG — różne limity IKZE) i próg podatkowy
- ile użytkownik już wpłacił w tym roku (`stan_wdrozenia`) — jeżeli nie wie,
  zapytaj, nie zakładaj zera

**Policz:**
- pozostały limit IKE i IKZE na ten rok
- wartość ulgi IKZE = planowana wpłata × stawka podatkowa. Podaj kwotę w złotych,
  nie procent.
- ile z tego realnie stać użytkownika, biorąc pod uwagę bilans miesięczny
  i poduszkę. **Nie sugeruj maksymalizacji limitu, jeżeli oznaczałaby to
  naruszenie poduszki finansowej.** Limit to sufit, nie cel.

**Co gdzie umieścić:**
Zasada: w opakowaniu podatkowym najwięcej zyskują aktywa, które inaczej
zapłaciłyby najwyższy podatek i mają najdłuższy horyzont. Przy porównywalnych
stawkach to zwykle część akcyjna. Ale pokaż rachunek, nie regułę — policz
różnicę w złotych dla obu wariantów na horyzoncie użytkownika.

Uwaga na częsty błąd: obligacje skarbowe **nie są** zwolnione z podatku Belki.
Zwolnione są dopiero w IKE/IKZE.

**Kalendarz:**
- IKZE: wpłata musi być zaksięgowana do 31.12. Uwzględnij czas przelewu
  i ewentualne zakładanie konta (kilka dni roboczych).
- limit niewykorzystany przepada, nie przechodzi na kolejny rok

Jeżeli do końca roku zostało < 45 dni — postaw kalendarz na początku odpowiedzi.
Jeżeli > 6 miesięcy — nie strasz deadline'em, po prostu zaplanuj rozłożenie wpłat.

Raport: `output/reports/podatki_YYYY.md`.
Zastrzeżenie: to nie jest porada podatkowa.
