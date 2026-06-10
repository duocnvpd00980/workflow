.PHONY: dev jupyter test lint format install install-dev mg mu md m

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

# Migration
mig:
	uv run alembic revision --autogenerate -m "$(msg)"

mu:
	uv run alembic upgrade head

md:
	uv run alembic downgrade -1

mg: mig mu