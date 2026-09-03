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
	kill-frontend \
	kill-backend \
	kill-all

requirements:
	cd backend && uv export --format requirements-txt --no-emit-project --output-file requirements.txt

install-backend:
	cd backend && uv sync

install-frontend:
	npm --prefix frontend ci

install: install-backend install-frontend

start-backend:
	# Load environment variables from .env if present, otherwise fall back to .env.example
	cd backend && set -a; \
	if [ -f ../.env ]; then . ../.env; \
	elif [ -f ../.env.example ]; then . ../.env.example; \
	fi; \
	set +a; \
	uv run uvicorn backend.main:asgi_app --app-dir src --reload --host 0.0.0.0 --port 8000

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

# Kill processes listening on dev ports (useful if Ctrl-Z left them open)
kill-frontend:
	@echo "Checking for frontend process on port 5173..."
	@PIDS="$$(lsof -ti :5173 || true)"; \
	if [ -z "$$PIDS" ]; then \
		echo "No frontend process found on port 5173"; \
	else \
		echo "Killing frontend PIDs: $$PIDS"; \
		kill $$PIDS || (echo "SIGTERM failed, forcing kill" && kill -9 $$PIDS); \
	fi

kill-backend:
	@echo "Checking for backend process on port 8000..."
	@PIDS="$$(lsof -ti :8000 || true)"; \
	if [ -z "$$PIDS" ]; then \
		echo "No backend process found on port 8000"; \
	else \
		echo "Found backend PIDs: $$PIDS"; \
		# Show process details for visibility
		for p in $$PIDS; do ps -fp $$p || true; done; \
		echo "Attempting graceful kill..."; \
		kill $$PIDS 2>/dev/null || true; \
		# wait up to 5s for processes to exit
		for i in 1 2 3 4 5; do \
			sleep 1; \
			STILL="$$(lsof -ti :8000 || true)"; \
			if [ -z "$$STILL" ]; then break; fi; \
			echo "Still running: $$STILL"; \
		done; \
		STILL="$$(lsof -ti :8000 || true)"; \
		if [ -n "$$STILL" ]; then \
			echo "Forcing kill of PIDs: $$STILL"; \
			kill -9 $$STILL 2>/dev/null || true; \
		fi; \
		echo "Backend kill sequence complete."; \
	fi

kill-all: kill-frontend kill-backend