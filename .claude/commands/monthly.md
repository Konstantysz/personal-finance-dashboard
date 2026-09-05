---
title: Monthly
description: Month close - full month analysis with all categories vs trends
author: Konstanty Szumigaj
date: 2026-08-24
version: 3.0
---

## How to use

Run: `uv run personal-finance-dashboard monthly`

Or analyze a specific month:
`uv run personal-finance-dashboard monthly --month 2026-07`

Analyzes a month (default: last full month) with full category breakdown and budget planning data.

**Report format:**

- Month balance (expenses, income, savings, bilans)
- Trend comparison: month vs 3M/6M/12M averages (with % change)
- Fixed costs estimate: sum of all detected recurring payments
- **Category breakdown table:** all categories with:
  - Amount spent this month
  - % of total expenses
  - % change vs previous month
  - % change vs 3M/6M/12M averages
- Top 3 categories with largest increases (vs 3M average)
- Top 3 categories with largest decreases (vs 3M average)
- List of new categories that appeared this month
- New fixed cost candidates (for approval before budget planning)
- IKZE deadline reminder if Nov/Dec

**JSON output:**

- last_month, last_month_balance
- pct_vs_3m, pct_vs_12m
- top_3_up, top_3_down (category names and changes)
- new_categories count
- new_fixed_costs count
- **fixed_costs_total** — estimated sum of all recurring expenses

**Report file:** `output/reports/miesiac_YYYY-MM.md`

## Use case: Budget planning

Use this to estimate how much you can spend:

1. Get monthly income (from `last_month_balance` + expenses)
2. Subtract `fixed_costs_total` → remaining budget for variable spending
3. Review category trends to identify opportunities to cut or increase spending
