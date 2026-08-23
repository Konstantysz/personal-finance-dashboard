---
title: Validate
description: Data quality check — run with every new CSV
author: Konstanty Szumigaj
date: 2026-08-23
version: 1.0
---

Run `uv run personal-finance-dashboard validate` (optionally `--csv <path>` if the user
pointed to a file other than the default `data/raw/wallet_export.csv`).

This command **is** the implementation of this command — don't calculate anything
manually from the CSV, don't read it directly (blocked by a hook anyway).

Read the JSON from stdout. Key fields: `transfer_orphans`,
`transfer_malformed`, `duplicates`, `large_transactions`, `sparse_months`.

If any of them > 0 — **don't proceed automatically**. Open the full report
(`report` in the JSON, file in `output/reports/`) only for the section
concerning the problem, show the user the specifics (dates, amounts), and
ask what it is. Don't guess.

If everything is clean — say so in one sentence with the numbers from the JSON
(date range, transaction count, account count) and suggest `/analysis`.
