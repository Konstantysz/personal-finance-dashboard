---
title: Goal
description: Financial goal simulation - /goal <nazwa>
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

> **Status: spec, not implementation.** The corresponding CLI subcommand
> (`personal-finance-dashboard goal`) is currently a stub returning error code 2 - see
> `TODO.md`. This file describes the TARGET behavior, not a way to
> work around the lack of implementation. **Do not do this manually** by loading
> `data/raw/*.csv` into context (blocked by a hook anyway) - that is exactly
> the pattern (calculating in the conversation context) the CLI is meant to
> avoid. Instead: tell the user it's not implemented, and suggest either
> implementing the subcommand in `src/personal_finance_dashboard/` following the
> `validate`/`analyze` pattern, or waiting.

Argument: goal name. If it's in `config/profile.yaml` - take the parameters from there.
If not - ask for the amount and deadline, then add it to the profile.

**Calculate both ways:**

A) **How much needs to be saved** to reach amount X by date Y - given current
   capital and a realistic return. Provide the required monthly contribution.

B) **When the goal will be reached** at the current savings pace - this is the
   more important number, because it's based on facts, not on a declaration.

If A > the real monthly surplus from `/analysis` - **say it directly**.
Don't propose a plan the user can't carry. Instead, show options: moving the
deadline, lowering the amount, increasing income, cutting costs (from specific
categories and with specific amounts).

**Instrument selection by horizon:**
- < 2 years: only liquid and low-volatility
- 2–5 years: inflation-indexed bonds, savings account; equities at most marginally
- > 10 years: an equity portion makes sense

**Scenarios - always at least three:**
- conservative (lower return, higher inflation)
- base
- with a random event: 3 months of missed contributions or a 15,000 PLN expense

Account for seasonality from ARCHIVE: if the user has expensive months
(holidays, December), real annual savings are lower than 12 × monthly contribution.
Calculate this and show the difference.

Chart: `output/charts/goal_<nazwa>.png` - capital accumulation, three scenarios,
horizontal goal line, vertical deadline line.

Report: `output/reports/goal_<nazwa>_YYYY-MM-DD.md`.
