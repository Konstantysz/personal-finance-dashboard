---
title: Forecast
description: Spending forecast for the next N months - statistics + known obligations
author: Konstanty Szumigaj
date: 2026-09-06
version: 1.0
---

## How to use

Run: `uv run personal-finance-dashboard forecast`

Or change the horizon:
`uv run personal-finance-dashboard forecast --months 6`

Forecasts spending for the next N months (default 3) from the ACTIVE window
only, plus obligations that are already known.

## What is actually forecast - and what is not

Three separate lines. Only the first one is a forecast; mixing them into a
single average is the mistake this command exists to avoid.

1. **`wydatki_konsumpcyjne`** - the only genuinely forecast line. Median (P50)
   and P75 of monthly totals from `expenses()`. Quantiles, not means: a single
   trip wrecks a mean and leaves a median alone.
2. **`wplaty_inwestycyjne`** - a known position, not a forecast. Median of the
   **last 3 months only**, because the amount has been growing and a longer
   window would understate it. Reported without an interval. The raw
   month-by-month series ships in `wplaty_seria` so the trend and any skipped
   month stay visible.
3. **`raty`** - known to the złoty, from `cele.pozyczki_wlasne` in the profile.
   Summed per month from each loan's `pierwsza_rata`/`ostatnia_rata` range.

Total = `odplyw_calkowity`. Because lines 2 and 3 are known numbers, P50 and
P75 differ only by the spread on line 1.

## No seasonality - by design

The ACTIVE window is currently ~13 months, which is roughly one observation
per calendar month. That cannot separate "December is expensive" from "that
December you bought a washing machine". No seasonal index is fitted, and none
should be added until ACTIVE spans two or more full years.

**Consequence:** the per-month forecasts are identical. Months differ only by
the instalments falling due in them. Do not present this as a model that
predicted three similar months - it is a flat baseline plus known obligations.
The report states this explicitly; keep it that way.

## Windows

Generated, not hardcoded: every 3 months up to the length of ACTIVE. With 13
months that is 3/6/9/12; the list grows on its own as history accumulates and
never exceeds available data.

`okna` reports P50 for each window. The headline number always uses the
**shortest window (3m)** - it tracks the current way of living and requires no
choice.

## Backtest - runs on every call

Walk-forward: predicting month M uses only the months strictly before M.
Tested over roughly the last 6 months, MAPE reported per window.

`rekomendowane_okno` names the lowest-MAPE window, but the forecast **does not
switch to it**. At this sample size an 11% vs 12% difference over 6 test points
is noise, and auto-switching would make the command change its window month to
month. `uzyte_okno` says which window the headline actually came from - report
both when they disagree, do not quietly present the recommendation as the
result.

**Read the MAPE before quoting any number.** It is the measured error of this
forecast on this data. If it sits near 20%, say so and lean on P75 rather than
P50 when the user is planning against it.

## Outliers

Months beyond 1.5x IQR are **reported, never removed** - the forecast is
computed on the full data including them. Removing a point from a 13-month
sample is a silent bet that it will not recur; at a 3-month horizon that bet is
not safe. Use `outliers` to explain *why* the interval is wide, and offer
`/category` on that month if the user wants to know what drove it.

## JSON output

- `horyzont` - the forecast months
- `okna` - P50 expenses per window
- `backtest_mape` - MAPE per window (keys match `okna`); `null` where a window
  had too little prior history
- `rekomendowane_okno` - lowest MAPE, informational only
- `uzyte_okno` - the window the headline number used (always the shortest)
- `prognoza` - per month: `wydatki_p50`, `wydatki_p75`,
  `wplaty_inwestycyjne`, `raty`, `odplyw_p50`, `odplyw_p75`
- `suma_<N>m` - totals over the horizon (key named after the horizon)
- `wplaty_seria` - raw investment contributions, last 3 months
- `outliers` - `miesiac`, `kwota`, `odchylenie_iqr`
- `aktywne_od`, `n_miesiecy` - the window the whole thing rests on

**Report file:** `output/reports/forecast_YYYY-MM-DD.md`

No chart: without seasonality the forecast is flat, so a fan chart would be a
horizontal line carrying nothing the two numbers do not already say.

## Definition: outflow

`outflow()` counts a transfer leaving an account in `konta.biezace` for an
account **outside** `biezace` (savings, investment, or excluded from net
worth). PKO -> Revolut moves are not outflow. Only one side of each pair is
counted - counting both doubles the amount.

Ambiguous pairing keys (two transfers on the same day for the same amount) are
resolved via `audit_transfers()` and land in `malformed` rather than being
guessed at, so they are left out of outflow. If `validate` reports a non-zero
`transfer_malformed`, the investment line may be understated - check that
before trusting it.

## Boundaries

Money leaving the current accounts is not money lost: contributions to XTB or
bonds reduce monthly cash flow while leaving net worth intact. Say
"outflow", not "spending", for lines 2 and 3.

Two scenarios always (P50 and P75), never a single number - CLAUDE.md.
