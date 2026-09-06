---
title: Categories
description: Expenses per category per period - fixed vs variable - /categories [months]
author: Konstanty Szumigaj
date: 2026-09-06
version: 1.0
---

## How to use

Run: `uv run personal-finance-dashboard categories`

Change the window: `uv run personal-finance-dashboard categories --months 6`

Keep the running (unfinished) period: add `--include-last`. Default drops
it, because a period analyzed before it closes shows only part of its
spending and would pull every median down.

## What it computes

Expenses (never transfers) per category per period over the last N closed
periods of the ACTIVE window. Periods follow `osoba.tryb_okresu` - in
`wyplata` mode a period is labeled by the month it funds: the payday of
19 June opens the window 19 June .. 20 July, labeled `2026-07`. The JSON
field `tryb_okresu` says which mode was used; say it when quoting labels.

Every category gets a class from its behaviour in the window, not from its
name:

- `staly` - present in at least 80% of periods and coefficient of variation
  (stdev / mean, zero months included) at most 0.35, **or** listed in the
  profile under `koszty_stale.potwierdzone` (user-confirmed; a payment that
  slipped across a period boundary does not demote it).
- `sporadyczny` - present in fewer than half of the periods.
- `zmienny` - everything else.

This is a heuristic. Present it for approval, and expect edge cases: a
subscription paid quarterly lands in `sporadyczny`, a rent that changed
once may drop to `zmienny`. `detect_fixed_costs` in `analyze` works at the
(category, payee) level and is the better tool for spotting individual
recurring payments; this command answers the budget-level question "how much
of a month is committed before I decide anything". When the user confirms a
category as fixed, add it to `koszty_stale.potwierdzone` in the profile
instead of remembering it in conversation.

## Groups and events

`config/category_tree.json` (Wallet's group -> subgroup -> leaf tree) rolls
every category up to its top-level group; `grupy` in the JSON and the
report carry that rollup. Every transaction has a category, so a name that
is in the export but not in the tree is a config gap, not a bucket: the
command exits with code 2 and names the categories. Wallet renames are
resolved through `config/category_mapping.yaml` (`aliasy`: export name ->
tree name) - add the missing name there, or to the tree, after confirming
with the user which branch it belongs to.

`okresy.wydarzenia` in the profile (items with `od`, `do`, `opis`) marks
every overlapping period in `adnotacje`. Use it to explain a spike (a trip,
a move) before calling it an outlier, and add new events there when the
user mentions one.

## JSON output

- `okresy`, `n_okresow` - the period labels used, oldest first
- `tryb_okresu` - `kalendarzowy` or `wyplata`
- `sumy_klas` - per class: `mediana_miesieczna` (median of per-period class
  totals), `suma` over the window, `liczba` of categories
- `top` - per class, up to 8 categories by mean, with `mediana`, `srednia`
  and `obecna_w` (number of periods the category appears in). For
  `sporadyczny` the median is usually 0 - read `srednia` there.

**Report file:** `output/reports/kategorie_YYYY-MM-DD.md` - full pivot
(category x period) grouped by class. Open it only when the user asks about
a category not in `top`.

## Boundaries

`mediana_miesieczna` of `staly` is the committed floor of a month. Compare it
with typical income from `analyze` to say how much room is left for the
variable part. Do not add the classes' medians and call it a forecast - the
median of a sum is not the sum of medians. For a forecast use `/forecast`.
