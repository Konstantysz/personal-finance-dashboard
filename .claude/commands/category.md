---
title: Category
description: Detailed analysis of a single category - /category <nazwa>
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

## How to use

Run: `uv run personal-finance-dashboard category <nazwa>`

Shows detailed analysis of a single category: historical trends, top counterparties, outliers, fixed vs. variable split.

Argument: category name. If missing or ambiguous - show a list of matches and ask.

Analyze:

**In the ACTIVE window**
- sum, monthly average, median, deviation
- distribution: histogram of individual transaction amounts
- rolling 3M trend
- top 10 counterparties (`payee`) with sums and transaction counts
- distribution by day of week and day of the pay cycle
- outliers (> mean + 2σ) - list with date, amount, note

**Context from ARCHIVE**
- what this category looked like before the move
- **with a caveat**: if this is a housing or groceries category, the comparison
  shows a lifestyle change, not extravagance. Say that.

**Conclusions**
- which part is fixed (untouchable), which is variable
- where something can realistically be changed and by how much - with a number,
  not "worth cutting back"
- whether a pattern is visible (shopping near the end of the cycle, weekend clustering)

Chart: `output/charts/kategoria_<nazwa>.png` - monthly series with the move date
marked.

Don't moralize. Show numbers and options; the decision belongs to the user.
