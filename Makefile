SHELL := /bin/bash

.PHONY: install-backend install-frontend install dev start-backend start-redis start-frontend test

requirements:
	cd backend && uv export --format requirements-txt --no-emit-project --output-file requirements.txt

install-backend:
	cd backend && uv sync

install-frontend:
	npm --prefix frontend ci

install: install-backend install-frontend

start-backend:
	cd backend && uv run uvicorn backend.main:asgi_app --app-dir src --reload --host 0.0.0.0 --port 8000

start-redis:
	docker run --rm --name chess-redis -p 6379:6379 redis:alpine

start-frontend:
	npm --prefix frontend run dev

dev:
	honcho start -f Procfile.dev

test:
	cd backend && uv run pytest