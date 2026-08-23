---
title: Analysis
description: Full ACTIVE window analysis - flow, categories, fixed costs
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

Requires `config/profile.yaml`. If missing - tell the user that the profile
does not exist, and suggest `/profil` (command not implemented in the CLI -
see `TODO.md`; until implementation, ask for the profile data directly in
conversation and save it to `config/profile.yaml` manually, following the
pattern in `config/profile.example.yaml`).

Run `uv run personal-finance-dashboard analyze`. This command itself calculates the ACTIVE
window, writes the report and charts - do not duplicate this logic in
conversation.

Read the JSON. Key fields: `months_in_window`, `last_month_balance`,
`avg_balance`, `avg_balance_3m`, `fixed_costs_candidates`, `params_stale`.

**Always show `last_month_balance` next to `avg_balance`** - if they differ
in direction (one positive, the other negative), that is the most important
piece of information in the answer, not a detail at the end.

If `params_stale` is `true` - note it if the conversation concerns investments
or taxes; for pure budget analysis it can be skipped.

Open the full report (path in `report`) only if the user asks about something
not in the JSON (specific categories, the list of fixed costs for approval).
Charts are in `charts` - you can show them directly.

Finish with 2-3 concrete next-step proposals, matched to what came out (e.g.,
if `fixed_costs_candidates` > 0: suggest reviewing and approving the list; if
the balance is negative: suggest `/category` on the largest item from the
report).
