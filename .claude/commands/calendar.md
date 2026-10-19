---
title: Calendar
description: Payday calendar - income, fixed costs, instalments and investment contributions by day with running balance
---

Run: `uv run personal-finance-dashboard calendar` (next payday window) or
`calendar --current` (window running today).

Rows: payday income, `cele.pozyczki_wlasne` instalments (on payday), each
`koszty_stale.potwierdzone` category dated by the median offset (days since
the window opened) of its largest payment per closed window, and one
contribution row per account in `konta.inwestycyjne` (XTB, bonds).

Amounts: fixed costs use P50 and P75 of the per-window total. Contributions
are a known position, not a forecast: median of the last 3 closed windows,
identical in both scenarios, dated like fixed costs; `inwestycje` in the JSON
is their sum. Balance runs on P50. Variable spending is excluded - the bottom
line is what remains for it. Report: `output/reports/calendar_<window>.md`.
