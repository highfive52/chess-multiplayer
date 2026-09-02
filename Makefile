SHELL := /bin/bash

.PHONY: \
	requirements \
	install-backend \
	install-frontend \
	install \
	start-backend \
	start-frontend \
	dev \
	test \
	infra-up \
	infra-down \
	infra-logs \
	postgres-up \
	postgres-down \
	postgres-logs \
	migrate

requirements:
	cd backend && uv export --format requirements-txt --no-emit-project --output-file requirements.txt

install-backend:
	cd backend && uv sync

install-frontend:
	npm --prefix frontend ci

install: install-backend install-frontend

start-backend:
	cd backend && uv run uvicorn backend.main:asgi_app --app-dir src --reload --host 0.0.0.0 --port 8000

start-frontend:
	npm --prefix frontend run dev

dev:
	honcho start -f Procfile.dev

test:
	cd backend && uv run pytest

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f postgres redis

postgres-up:
	docker compose up -d postgres

postgres-down:
	docker compose stop postgres

postgres-logs:
	docker compose logs -f postgres

migrate:
	cd backend && uv run alembic -c alembic.ini upgrade head


integration:
	docker compose up -d postgres redis
	cd backend && uv run pytest -q -k integration

integration-docker:
	docker compose up -d postgres redis
	docker run --rm -v $(PWD)/backend:/app -w /app python:3.11-slim bash -c "pip install --no-cache-dir \"psycopg[binary]\" alembic python-chess pytest && pytest -q tests/test_integration_db.py"