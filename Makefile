# Makefile for managing backend and frontend development tasks, infrastructure, and migrations.

SHELL := /bin/bash

# Load environment variables from .env.local if present, otherwise fall back to .env.example
ifneq (,$(wildcard .env.local))
include .env.local
else
include .env.example
endif
export

.PHONY: \
	requirements \
	install-python \
	install-frontend \
	install \
	start-backend \
	start-frontend \
	dev \
	test-backend \
	test-ml \
	test \
	model-publish \
	infra-up \
	infra-down \
	infra-logs \
	postgres-up \
	postgres-down \
	postgres-logs \
	migrate \
	integration \
	integration-docker \
	kill-frontend \
	kill-backend \
	kill-all

#-----------------------------
# Dependency management

requirements:
	uv export --package backend --format requirements-txt --no-emit-project --output-file apps/backend/requirements.txt

install-python:
	uv sync

install-frontend:
	npm --prefix frontend ci

install: install-python install-frontend

#-----------------------------
# Tests

test-backend:
	uv run --package backend pytest apps/backend/tests

test-ml:
	uv run --package chess-ml pytest apps/trainer/tests packages/chess_core/tests

test: test-backend test-ml

#-----------------------------
# Model artifacts

model-publish:
	uv run --package chess-ml python scripts/model_publish.py

#-----------------------------
# Development servers

start-backend:
	uv run --package backend backend

start-frontend:
	npm --prefix frontend run dev

dev:
	honcho start -f Procfile.dev

#-----------------------------
# Infrastructure management

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
	uv run --package backend alembic -c apps/backend/alembic.ini upgrade head

#-----------------------------
# Integration tests

integration:
	docker compose up -d postgres redis
	uv run --package backend pytest -q apps/backend/tests -k integration

integration-docker:
	docker compose up -d postgres redis
	docker run --rm -v $(PWD)/apps/backend:/app -w /app python:3.11-slim bash -c "pip install --no-cache-dir \"psycopg[binary]\" alembic python-chess pytest && pytest -q tests/test_integration_db.py"

#-----------------------------
# Kill development processes

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
		for p in $$PIDS; do ps -fp $$p || true; done; \
		echo "Attempting graceful kill..."; \
		kill $$PIDS 2>/dev/null || true; \
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