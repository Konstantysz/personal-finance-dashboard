# personal-finance-dashboard - personal finance analysis agent

Concisely, without decorative headings/emoji. Concrete facts, numbers, source of each number.

## Commands (uv)

- Install: `uv sync --locked`
- Tests: `uv run pytest -q`
- Format: `uv run ruff format . && uv run ruff check --fix .`
- Type check: `uv run mypy src`
- Lint (all): `uv run pre-commit run --all-files`
- CLI: `uv run personal-finance-dashboard <validate|analyze|monthly|category|invest|taxes|goal>`

## Overriding principle: CLI, not raw data

CSV transformation (parsing, pairing transfers, splitting into periods) is a
deterministic task - see `src/personal_finance_dashboard/data.py`, the only source of this logic.
**You do not read `data/raw/*.csv` directly** and you do not calculate anything
from it manually in the conversation context. Blocked by a hook
(`.claude/hooks/block_raw_csv_read.py`) - this is not just a request.

Instead: call `uv run personal-finance-dashboard <subcommand>`. Each subcommand writes
a full report to `output/reports/*.md` and charts to `output/charts/*.png`, and prints
**one line of JSON** to stdout with key numbers. Read this JSON and comment on
it - do not load entire reports back into context unless the user asks about
something the JSON does not cover.

Implemented: `validate`, `analyze`, `monthly`, `category`, `invest`, `taxes`, `goal`.

## Structure

- `src/personal_finance_dashboard/data.py` - parsing, transfers, time windows, fixed costs
- `src/personal_finance_dashboard/charts.py` - ready-made chart functions (always these, never ad hoc
  matplotlib called from non-CLI-wrapped code)
- `src/personal_finance_dashboard/cli.py` - Typer commands, the only entry point to `data.py`
- `config/profile.yaml` - user profile (gitignored, section below)
- `config/parameters.yaml` - market/tax rates with verification date
- `config/category_mapping.yaml` - mapping of categories changed over time
- `.claude/commands/*.md` - specifications of target command behavior
  (they load on-demand, do not clutter context at startup)

## The data spans two different periods of life

The profile (`config/profile.yaml`, key `okresy.regime_change_date`) divides
history into ARCHIVE (before) and ACTIVE (after). `analyze` by default
calculates only on the ACTIVE window. If the user asks about something from the
entire history or about seasonality - this is an exception; say explicitly
which window you are using.

## Accounts and savings

Savings are exclusively deposits to accounts listed in
`config/profile.yaml` → `konta.oszczednosciowe`. Do not guess by account name.
Balances from CSV are cumulative from the beginning of the export, not actual
states - actual balances are in the profile; do not calculate them from
transactions.

## Retirement accounts, bonds, ETFs - mechanics and current rates

Not in this file. Current numbers: `config/parameters.yaml` (has
`last_verified` - if older than 60 days, `analyze` returns `params_stale`
in JSON; warn the user instead of calculating on stale data).
Mechanics and instrument selection principles:
`.claude/commands/investments.md`, `.claude/commands/taxes.md` - read them for
the relevant task, not upfront.

## Boundaries

You are not an investment or tax advisor. Forecasts always in at least two
scenarios (conservative / base), never as a single number.

## Code rules

- Type hints and docstrings (Google style) on every public function.
- `src/` layout - do not create new top-level code directories. `data/`,
  `config/`, `output/` are data, not code - this is not an exception to discuss.
- Secrets in `.env`, never in the repo.
- New function in `data.py` = test in `tests/unit/test_data.py`.
- Format with `ruff`. `mypy --strict` must pass on `src/` before commit.
