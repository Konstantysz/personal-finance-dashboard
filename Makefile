.PHONY: install test lint format typecheck


install:
	uv sync --locked

test:
	uv run pytest -q

lint:
	uv run pre-commit run --all-files

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src
