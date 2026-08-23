---
title: Taxes
description: IKE/IKZE optimization - current-year limits and the 31.12 deadline
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

## How to use

Run: `uv run finanse taxes`

Calculates current-year IKE and IKZE remaining limits, deduction value (in PLN, not %), and the December 31 deadline. Shows how much can be contributed this year and optimal allocation between IKE/IKZE based on tax bracket and employment form.

**Establish first:**
- today's date and how many days remain until December 31
- the tax year and limits from `config/parameters.yaml`
- employment form (etat vs JDG - different IKZE limits) and tax bracket
- how much the user has already contributed this year (`stan_wdrozenia`) - if they don't know,
  ask; don't assume zero

**Calculate:**
- remaining IKE and IKZE limit for this year
- value of the IKZE deduction = planned contribution × tax rate. Give the amount in PLN,
  not a percentage.
- how much of this the user can realistically afford, considering the monthly balance
  and the emergency fund. **Don't suggest maximizing the limit if it would mean
  touching the emergency fund.** The limit is a ceiling, not a target.

**What to put where:**
Principle: the assets that gain the most in a tax wrapper are those that would
otherwise pay the highest tax and have the longest horizon. At comparable rates
this is usually the equity portion. But show the calculation, not the rule -
calculate the difference in PLN for both variants over the user's horizon.

Beware a common mistake: treasury bonds **are not** exempt from Belka tax.
They are exempt only inside IKE/IKZE.

**Calendar:**
- IKZE: the contribution must be booked by 31.12. Account for transfer time
  and possible account setup (a few business days).
- an unused limit is lost; it does not roll over to the next year

If fewer than 45 days remain until year-end - put the calendar at the top of the answer.
If more than 6 months - don't scare with the deadline; just plan spaced-out contributions.

Report: `output/reports/taxes_YYYY.md`.
Disclaimer: this is not tax advice.
