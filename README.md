# personal-finance-dashboard

Personal finance analysis: CLI + Claude Code agent.

## Installation

```bash
uv sync --locked
cp config/profile.example.yaml config/profile.yaml   # fill in manually or via the agent
# put the Wallet export in data/raw/wallet_export.csv
```

## Usage without the agent

```bash
uv run personal-finance-dashboard validate                # data quality check
uv run personal-finance-dashboard analyze                 # full ACTIVE window analysis
```

Both commands write a report to `output/reports/` and (for `analyze`) charts to
`output/charts/`, and print one line of JSON to stdout with key
numbers — convenient for further processing (`| python3 -m json.tool`,
`| jq`).

`monthly`, `category`, `invest`, `goal` are **defined in the CLI but
not implemented** — see `TODO.md` and the specs in `.claude/commands/`.

## Usage with Claude Code

```bash
claude
```

`CLAUDE.md` loads automatically. Slash commands in `.claude/commands/`:

| command | calls CLI | status |
|---|---|---|
| `/profil` | — (dialog + YAML save) | works |
| `/waliduj` | `personal-finance-dashboard validate` | works |
| `/analiza` | `personal-finance-dashboard analyze` | works |
| `/miesiac` | `personal-finance-dashboard monthly` | spec, CLI is a stub |
| `/kategoria <nazwa>` | `personal-finance-dashboard category` | spec, CLI is a stub |
| `/inwestycje` | `personal-finance-dashboard invest` | spec, CLI is a stub |
| `/podatki` | — | spec, no decision yet on CLI placement |
| `/cel <nazwa>` | `personal-finance-dashboard goal` | spec, CLI is a stub |

Direct reads of `data/raw/*.csv` by the agent are blocked by a hook
(`.claude/settings.json` → `.claude/hooks/block_raw_csv_read.py`) — not
just recommended against, but enforced. Goal: data transformation is a
deterministic task and should cost CPU cycles, not tokens.

## Development

```bash
uv run pytest -q          # tests
uv run mypy src           # type check (--strict)
uv run ruff check --fix . && uv run ruff format .
uv run pre-commit run --all-files
```

## Structure

```
CLAUDE.md / AGENTS.md      agent instructions (AGENTS.md = manual copy)
.claude/
  commands/                slash command specs
  hooks/block_raw_csv_read.py
  settings.json            hook registration
src/personal-finance-dashboard/
  data.py                  parsing, transfers, time windows — single source of truth
  charts.py                ready-made chart functions
  cli.py                   Typer, the only entry point to data.py
config/
  parameters.yaml          market/tax rates, with verification date
  profile.yaml             user profile (gitignored)
  category_mapping.yaml    mapping of renamed categories
data/raw/                  CSV exports (gitignored)
output/{reports,charts}/   results (gitignored)
tests/unit/test_data.py    regression tests for historical interpretation errors
TODO.md                    roadmap (repo without a remote — surrogate for GitHub Issues)
```

## Three things to remember

**1. The data spans two different lives.** The default analysis window is ACTIVE (from
`config/profile.yaml` → `okresy.regime_change_date`). History before that
date is used for seasonality and long-term trends, not for current average
spending.

**2. Transfers are neither income nor expenses.** They occur in pairs.
Only deposits to accounts marked in the profile as savings are treated as
savings — logic in `src/personal-finance-dashboard/data.py`, tested in
`tests/unit/test_data.py` specifically for historical errors in
interpreting this data.

**3. `config/parameters.yaml` goes stale.** Bond interest rates change
every month. `personal-finance-dashboard analyze` checks the file age and returns
`params_stale` in the JSON — don't ignore this for investment questions.

## Disclaimer

Analytical tool, not investment or tax advice.
