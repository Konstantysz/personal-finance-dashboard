---
title: Category
description: Detailed analysis of a single category - /category <nazwa>
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

> **Status: spec, not implementation.** The corresponding CLI subcommand
> (`personal-finance-dashboard category`) is currently a stub returning error code 2 - see
> `TODO.md`. This file describes the TARGET behavior, not a way to
> work around the lack of implementation. **Do not do this manually** by loading
> `data/raw/*.csv` into context (blocked by a hook anyway) - that is exactly
> the pattern (calculating in the conversation context) the CLI is meant to
> avoid. Instead: tell the user it's not implemented, and suggest either
> implementing the subcommand in `src/personal_finance_dashboard/` following the
> `validate`/`analyze` pattern, or waiting.

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
