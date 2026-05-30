.PHONY: dev jupyter test lint format

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

jupyter:
	uv run jupyter lab --notebook-dir=notebooks

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

install:
	uv sync

install-dev:
	uv sync --dev
