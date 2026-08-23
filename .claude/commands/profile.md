---
title: Profile
description: User profiling - run once, then only updates
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

> **Status: spec, not implementation.** There is no `personal-finance-dashboard profile`
> in the CLI yet (see `TODO.md`). Carry this out as a normal dialog: ask questions,
> then save the answers to `config/profile.yaml` yourself (copy the structure
> from `config/profile.example.yaml`). This does not require reading CSV, so the hook
> won't block you here - but stick to the YAML format from the example.

Build or update `config/profile.yaml` based on `config/profile.example.yaml`.

First run `uv run personal-finance-dashboard validate` (or use the result if it was already
run in this session). The report in `output/reports/validate_*.md` contains a
"## Accounts" section with the list of accounts, transaction counts, and date
ranges for each - read that section of the file, not the raw CSV. Without this,
it's impossible to ask about accounts sensibly.

Ask questions **one at a time**, waiting for an answer. Don't send a list of ten
questions at once. Order:

1. Age.
2. Employment form (etat / JDG) - determines the IKZE limit.
3. Tax bracket (12% / 32%) - determines the value of the IKZE deduction.
4. Net monthly income and whether it is stable.
5. **Accounts**: show the detected list and ask which are savings, which are
   current, which to exclude from assets (lunch card, etc.). This question is
   critical - the entire savings analysis depends on it.
6. **Actual balances** of accounts as of today. Explain why: balances calculated
   from CSV are cumulative sums from the start of the export, not real states.
7. **Regime change date**: show the date you detected empirically from the jump
   in housing categories, and ask for confirmation or correction. Also ask
   whether there were other significant life changes in 2022–2025 (job change,
   moving out, end of studies) that should be marked.
8. Short-term goals: what, how much, by when.
9. Long-term goals.
10. Risk tolerance and knowledge level.
11. **Implementation status**: whether IKE/IKZE are already opened, whether
    contributions were made this year, which instruments are actually held.
    Ask about the actual state, not plans.
12. Excluded instruments and whether anyone advises externally.

At the end, show the filled-in file for approval, and only then save it.
Suggest `/validate` as the next step.
