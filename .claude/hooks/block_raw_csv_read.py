#!/usr/bin/env python3
"""
PreToolUse hook: blokuje bezpośredni odczyt data/raw/*.csv przez Claude'a.

Decyzja projektowa: agent ma czytać wyniki
`personal-finance-dashboard validate` / `personal-finance-dashboard
analyze` (JSON na stdout + raporty w output/), nie surowe transakcje. To
oszczędza tokeny (transformacja danych to zadanie deterministyczne, patrz
checklist.md — Moduł 7) i zapobiega sytuacji, w której logika liczenia
(transfery, okna czasowe) jest przepisywana ad hoc w kontekście rozmowy
zamiast żyć w jednym miejscu (src/personal_finance_dashboard/data.py).

Łapie:
  - Read/View na ścieżce pasującej do data/raw/*.csv
  - Bash z cat/head/tail/less/python(pandas.read_csv)/awk/sed na tej ścieżce

Nie łapie:
  - odczytu output/, config/, kodu źródłowego
  - poleceń `uv run personal-finance-dashboard ...` (to jest dozwolona ścieżka)

Kod wyjścia 2 = blokada. Kod 0 = przepuść.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED_PATTERN = re.compile(r"data/raw/[^\s\"']*\.csv", re.IGNORECASE)

# Polecenia, które w Bashu oznaczają "czytam plik", nie "wołam CLI".
READ_LIKE_COMMANDS = re.compile(
    r"\b(cat|head|tail|less|more|awk|sed|python3?\s.*read_csv|pandas)\b"
)


def _tool_input_text(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    # Read/View: pole "path" albo "file_path"
    for key in ("path", "file_path"):
        if key in tool_input:
            return str(tool_input[key])
    # Bash: pole "command"
    if "command" in tool_input:
        return str(tool_input["command"])
    return json.dumps(tool_input)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # nie blokuj na niezrozumiałym wejściu — fail open

    tool_name = payload.get("tool_name", "")
    text = _tool_input_text(payload)

    if not BLOCKED_PATTERN.search(text):
        return 0

    if tool_name == "Bash" and (
        "personal-finance-dashboard" in text or not READ_LIKE_COMMANDS.search(text)
    ):
        # Dopuszczamy polecenia, które nie "czytają" pliku wprost, np.
        # `ls data/raw/` albo `uv run personal-finance-dashboard validate --csv data/raw/x.csv`.
        return 0

    print(
        "Zablokowano: bezpośredni dostęp do data/raw/*.csv.\n"
        "Użyj `uv run personal-finance-dashboard validate` lub"
        "`uv run personal-finance-dashboard analyze` - logika parsowania i okien czasowych "
        "żyje w src/personal-finance-dashboard/data.py, "
        "nie w kontekście rozmowy. Zobacz CLAUDE.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
