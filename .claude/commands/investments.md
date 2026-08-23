---
title: Investments
description: Investment plan based on the profile and current market parameters
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

> **Status: spec, not implementation.** The corresponding CLI subcommand
> (`personal-finance-dashboard invest`) is currently a stub returning error code 2 - see
> `TODO.md`. This file describes the TARGET behavior, not a way to
> work around the lack of implementation. **Do not do this manually** by loading
> `data/raw/*.csv` into context (blocked by a hook anyway) - that is exactly
> the pattern (calculating in the conversation context) the CLI is meant to
> avoid. Instead: tell the user it's not implemented, and suggest either
> implementing the subcommand in `src/personal_finance_dashboard/` following the
> `validate`/`analyze` pattern, or waiting.

**Before you calculate anything:**

1. Check `last_verified` in `config/parameters.yaml`. Older than 60 days -
   tell the user that parameters require refreshing, and provide sources.
   Don't calculate on stale data without a warning.
2. Check `stan_wdrozenia` in the profile. If the user already has positions -
   you are planning the **next step**, not starting from scratch.
3. Check how much is actually left each month (balance from `/analysis`). An
   investment plan exceeding the real surplus is useless. If the balance is
   negative - say so and ask whether we plan anyway or first address the flow.

**Order, not negotiable:**
1. Emergency fund = survival threshold × number of months (establish with the user,
   typically 3–6 with stable income). Liquid, immediately accessible.
2. Only the surplus above the emergency fund goes toward goals.
3. Short-term goal (< 5 years) - low-volatility instruments. Equities are out:
   with a 3-year horizon, the risk of having to sell in a downturn is real.
4. Long-term goal (> 10 years) - an equity portion makes sense here.

**What you present:**
- split of starting capital and monthly contribution between goals
- for each goal: instruments, justification by mechanics (not "because they're good"),
  costs, liquidity, taxation
- how much of this fits into IKE and IKZE this year (limits from parameters.yaml)
- **two projection scenarios**: conservative and base. Never one number.
- what happens if contributions drop by 30% or a larger expense appears

**Honesty in the calculation:**
- interest on bonds outside IKE/IKZE is subject to 19% Belka tax. Show net,
  not gross.
- compare against alternatives the user isn't considering (a savings account at
  6% net ≈ 4.86% vs EDO at 5.35% gross ≈ 4.33% net - this is not the obvious
  victory for bonds it was at 8%)
- if the plan relies on an assumption that no longer holds in market data -
  say so directly

Report: `output/reports/inwestycje_YYYY-MM-DD.md`.
End with a sentence that this is a simulation on assumptions, not investment advice.
