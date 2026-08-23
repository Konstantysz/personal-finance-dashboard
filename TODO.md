# TODO / roadmap

The repo has no remote right now, so this is a task list instead of GitHub
Issues. Once pushed to GitHub, it's worth moving each section into a separate
issue.

Rule for each task below: implementation follows the `validate`/`analyze`
pattern in `src/personal_finance_dashboard/cli.py` - a function in `data.py` (pure,
testable), a thin wrapper in `cli.py` (JSON to stdout + file on disk), a test
in `tests/unit/test_data.py`. Don't bypass the CLI by writing logic in a
`.claude/commands/*.md` command - that's exactly the token cost the CLI is
meant to avoid.

## Known shortcomings (bare minimum for this session)

- [ ] `stopa_oszczedzania` in the `analyze` report is rounded to 0 by
      `.round(0)` on the whole table (it's a 0-1 fraction, not PLN). Format
      it separately as a percentage.
- [ ] The `post_gen_project.py` hook of the Copier template (git init / uv sync /
      pre-commit install / AGENTS.md) didn't run automatically despite
      `--trust` in the environment where this repo was created - done manually.
      Check on the target machine whether it was just a sandbox quirk.
- [ ] `copier.yml` in the template always includes `GEMINI.md` when
      `use_ai_agents=true`, regardless of the choice in `ai_agents` - removed
      manually. Worth reporting in `Konstantysz/python-repository-template`.
- [ ] `AGENTS.md` is a manual copy of `CLAUDE.md` - sync after each change
      to the latter (or make it a pre-commit hook).

**Fixed after "fresh clone from scratch" verification (worth noting, because
the previous session didn't catch this - end-to-end tests ran on a large,
13-month synthetic CSV, not on a minimal case):**

- ~~`config/profile.example.yaml` didn't make it into the repo archive~~ - the file
  existed locally during creation, but was never copied to
  `personal_finance_dashboard/config/`, so it disappeared during packaging. Fixed.
- ~~`detect_fixed_costs` threw `KeyError` on empty result~~ -
  `pd.DataFrame([])` from an empty list has no `mediana_miesieczna` column,
  `sort_values` on it exploded. Occurred for every CSV shorter than
  3 months (exactly the "I just started using this repo" case).
  Fixed + added regression test
  (`test_detect_fixed_costs_empty_result_does_not_crash`).

**Takeaway for the future:** for the next commands (`monthly`, `category`,
`invest`, `goal`), test end-to-end both on the full dataset and on a minimal
one (1 month, zero expenses, zero categories) - edge cases when starting with
an empty/small repo are exactly what a real user does first.

## `personal-finance-dashboard monthly` - month close

Spec: `.claude/commands/monthly.md`. Comparison of the last full month with the
previous one, rolling 3M, same month a year earlier (with a caveat about the
ACTIVE/ARCHIVE boundary). Reminder about the IKZE deadline in November/December.

## `personal-finance-dashboard category <name>` - deep dive into a category

Spec: `.claude/commands/category.md`. Amount distribution, top counterparties,
rolling 3M trend, context from ARCHIVE with a caveat about lifestyle change.

## `personal-finance-dashboard invest` - investment plan

Spec: `.claude/commands/investments.md`. Requires beforehand:
`check_parameters_freshness` (already in `data.py`) + an actual balance from
`analyze`. Always two scenarios (conservative/base), never one number.

## `personal-finance-dashboard taxes` (or a separate `invest --tax` flag) - IKE/IKZE

Spec: `.claude/commands/taxes.md`. Separate command or a flag to `invest` -
to be decided at implementation; the working name was not settled in this
session.

## `personal-finance-dashboard goal <name>` - goal simulation

Spec: `.claude/commands/goal.md`. Three scenarios (conservative/base/random
event), seasonality from ARCHIVE included in the annual projection.

## To consider, not planned

- [ ] `.claude/rules/` with `paths:` scope - skipped this session, because the repo
      is one small package without subfolders requiring different rules.
      Consider it if `src/personal_finance_dashboard/` grows into several modules with
      different conventions.
- [ ] The blocking hook (`block_raw_csv_read.py`) catches only `Read`/`View`/
      `Bash`. If a file-editing tool is added, check whether it should also be
      covered by the matcher.
- [ ] CI (`.github/workflows/ci.yml`) doesn't yet have a step for hook tests
      (`.claude/hooks/block_raw_csv_read.py`) - currently tested only manually
      at creation.
