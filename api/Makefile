.PHONY: dev jupyter test lint format

dev:
	uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

jupyter:
	HF_HUB_OFFLINE=1 uv run python -m jupyterlab --notebook-dir=notebooks

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
