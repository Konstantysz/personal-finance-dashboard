#!/usr/bin/env python3
"""
PreToolUse hook: blocks direct reads of data/raw/*.csv by Claude.

Design decision: the agent should read the results of
`personal-finance-dashboard validate` / `personal-finance-dashboard
analyze` (JSON on stdout + reports in output/), not raw transactions. This
saves tokens (data transformation is a deterministic task, see checklist.md -
Module 7) and prevents a situation where calculation logic (transfers, time
windows) is rewritten ad hoc in the conversation context instead of living in
one place (src/personal_finance_dashboard/data.py).

Catches:
  - Read/View on a path matching data/raw/*.csv
  - Bash with cat/head/tail/less/python(pandas.read_csv)/awk/sed on that path

Does not catch:
  - reads of output/, config/, source code
  - `uv run personal-finance-dashboard ...` commands (this is the allowed path)

Exit code 2 = block. Exit code 0 = pass through.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED_PATTERN = re.compile(r"data/raw/[^\s\"']*\.csv", re.IGNORECASE)

# Commands that in Bash mean "I am reading a file", not "I am calling the CLI".
READ_LIKE_COMMANDS = re.compile(
    r"\b(cat|head|tail|less|more|awk|sed|python3?\s.*read_csv|pandas)\b"
)


def _tool_input_text(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    # Read/View: "path" or "file_path" field
    for key in ("path", "file_path"):
        if key in tool_input:
            return str(tool_input[key])
    # Bash: "command" field
    if "command" in tool_input:
        return str(tool_input["command"])
    return json.dumps(tool_input)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # don't block on unintelligible input - fail open

    tool_name = payload.get("tool_name", "")
    text = _tool_input_text(payload)

    if not BLOCKED_PATTERN.search(text):
        return 0

    if tool_name == "Bash" and (
        "personal-finance-dashboard" in text or not READ_LIKE_COMMANDS.search(text)
    ):
        # Allow commands that don't "read" the file directly, e.g.
        # `ls data/raw/` or `uv run personal-finance-dashboard validate --csv data/raw/x.csv`.
        return 0

    print(
        "Blocked: direct access to data/raw/*.csv.\n"
        "Use `uv run personal-finance-dashboard validate` or"
        "`uv run personal-finance-dashboard analyze` - parsing and time-window logic "
        "lives in src/personal-finance-dashboard/data.py, "
        "not in the conversation context. See CLAUDE.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
