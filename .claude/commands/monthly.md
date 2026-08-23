---
title: Monthly
description: Month close - last full month vs 3M/6M/12M trends
author: Konstanty Szumigaj
date: 2026-08-24
version: 2.0
---

## How to use

Run: `uv run personal-finance-dashboard monthly`

Compares the last full month with 3M, 6M, and 12M average expenses. Identifies
top 3 category increases and decreases versus 3M average. Flags new categories
and new fixed cost candidates. Adds IKZE deadline reminder in Nov/Dec.

**One-page report format:**

- Month balance (expenses, income, savings, bilans)
- Trend comparison: last month vs 3M/6M/12M averages (with % change)
- Top 3 categories with largest increases
- Top 3 categories with largest decreases
- List of new categories that appeared this month
- New fixed cost candidates (with stability info)
- IKZE deadline reminder if Nov/Dec

**JSON output:** last_month, last_month_balance, pct_vs_3m, pct_vs_12m, top_3_up,
top_3_down, new_categories count, new_fixed_costs count

**Report file:** `output/reports/miesiac_YYYY-MM.md`
