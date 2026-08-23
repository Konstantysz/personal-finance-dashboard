---
title: Monthly
description: Month close - comparison of new CSV with the previous analysis
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

## How to use

Run: `uv run finanse monthly`

Compares the last full month with previous month, rolling 3M average, and same month year-ago (with caveat if it falls in ARCHIVE period).

For monthly use. Requires a previous report in `output/reports/`.

1. Load the new CSV, run an abbreviated validation (transfers, gaps, anomalies).
2. Identify the last full month.
3. Compare it with:
   - the previous month
   - the rolling 3M average
   - the same month a year earlier (if it falls within ACTIVE; if it falls
     in ARCHIVE - say that the comparison is unreliable and why)

**Closing report - one page at most:**
- month balance and whether positive
- 3 categories with the largest change up, 3 down - with amounts
- whether savings went according to plan
- whether a new category or new fixed cost appeared
- goal progress: how much saved, how much remaining, whether the pace is sufficient
- one sentence: what went well, what needs attention

If November or December - add a reminder about the IKZE deadline (31.12)
and how much of the limit remains unused.

Save `output/reports/miesiac_YYYY-MM.md`. Update the flow chart.
Don't generate a full set of charts.
