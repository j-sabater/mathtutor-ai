# Makefile para MathTutor-AI
# Ejecutar desde la raíz del repo

.PHONY: help install up down lint format typecheck check test test-int test-e2e test-all eval eval-quick dev cli seed ci clean

# Default target
help:
	@echo "MathTutor-AI - Comandos disponibles:"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Instala dependencias (pip install -e .[dev]) + pre-commit"
	@echo "  make up          - Levanta infraestructura (Neo4j, Redis) con docker-compose"
	@echo "  make down        - Para y limpia infraestructura (docker-compose down -v)"
	@echo ""
	@echo "Calidad de Código:"
	@echo "  make lint        - Ruff check (E,F,W,I,UP,B,C4)"
	@echo "  make format      - Ruff format + auto-fix"
	@echo "  make typecheck   - MyPy strict en src/"
	@echo "  make check       - lint + typecheck + tests unit (rápido)"
	@echo ""
	@echo "Tests:"
	@echo "  make test        - Tests unitarios + contract (pytest -xvs)"
	@echo "  make test-int    - Tests integración (requiere Neo4j testcontainer)"
	@echo "  make test-e2e    - Tests end-to-end (requiere API arriba)"
	@echo "  make test-all    - test + test-int + test-e2e"
	@echo ""
	@echo "Evaluaciones (Anti-alucinación):"
	@echo "  make eval        - Suite completa de evals"
	@echo "  make eval-quick  - Smoke test rápido de evals"
	@echo ""
	@echo "Desarrollo:"
	@echo "  make dev         - Uvicorn con reload (puerto 8000)"
	@echo "  make cli         - CLI administrativa (Typer)"
	@echo "  make seed        - Puebla BD con currículo base"
	@echo ""
	@echo "CI Local (simula GitHub Actions):"
	@echo "  make ci          - check + test + eval-quick + build-docker"
	@echo ""
	@echo "Limpieza:"
	@echo "  make clean       - Limpia caches y artefactos"

# ── Setup ──────────────────────────────────────────────────────────────

install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down -v

# ── Calidad de Código ──────────────────────────────────────────────────

lint:
	ruff check . --select=E,F,W,I,UP,B,C4

format:
	ruff check . --select=E,F,W,I,UP,B,C4 --fix
	ruff format .

typecheck:
	mypy --strict src/

check: lint typecheck test

# ── Tests ──────────────────────────────────────────────────────────────

test:
	pytest -xvs tests/unit tests/contract

test-int:
	pytest -xvs tests/integration

test-e2e:
	pytest -xvs tests/e2e

test-all: test test-int test-e2e

# ── Evals ──────────────────────────────────────────────────────────────

eval:
	python -m evals.runners.full_suite

eval-quick:
	python -m evals.runners.quick_smoke

# ── Desarrollo ─────────────────────────────────────────────────────────

dev:
	uvicorn mathtutor.api.main:app --reload --port 8000

cli:
	python -m mathtutor.cli --help

seed:
	python scripts/seed_graph.py

# ── CI Local ───────────────────────────────────────────────────────────

ci: check test eval-quick build-docker

build-docker:
	docker build -f docker/Dockerfile -t mathtutor-ai:latest .

# ── Limpieza ───────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist build *.egg-info .coverage htmlcov 2>/dev/null || true
