# MathTutor-AI

> **Sistema agéntico de tutoría matemática para Bachillerato/EvAU (Matemáticas II: Cálculo)**

---

## 🎯 Por qué este proyecto

Este proyecto nace de dos motores:

### 1. Mi hambre por aprender y hacer cosas nuevas
- **Spec-Driven Development (SDD)**: Descubrí esta metodología y me enamoró la idea de que *la especificación es la ley*. No se escribe código sin que exista una spec y un test que la valide. Es disciplina pura aplicada a ingeniería de software.
- **Knowledge Graphs con Neo4j**: Siempre quise trabajar con grafos de conocimiento reales, no solo teóricos. Modelar el currículo matemático como un DAG de prerrequisitos, trackear mastery levels con EWMA, y detectar patrones de error recurrentes — todo eso vive naturalmente en un grafo.
- **Arquitectura híbrida LLM + Determinista**: La regla de oro **P1** ("LLM nunca calcula matemáticas") me parece brillante. SymPy es el oráculo, el LLM orquesta. Cero alucinaciones matemáticas por diseño.

### 2. Mi necesidad real como profesor particular de matemáticas
- **Corregir ejercicios a mano consume horas** que podrían dedicarse a explicar, motivar, adaptar.
- **Detectar patrones de error** (regla de la cadena, signos, indeterminaciones) es repetitivo y propenso a fatiga.
- **Generar ejercicios adaptados** a los huecos de cada alumna requiere conocer su historial, sus prerrequisitos fallados, su racha de aciertos.
- **Crear apuntes personalizados** con ejemplos contrarios y práctica guiada es el "santo grial" de la tutoría 1-a-1.

**MathTutor-AI automatiza todo eso**: la alumna sube una foto → OCR → corrección paso a paso con SymPy → actualización del grafo de conocimiento → siguiente ejercicio recomendado → apunte personalizado si hay patrones recurrentes.

---

## 🏗️ Arquitectura (Single Source of Truth: `specs/`)

| Spec | Qué Gobierna |
|------|--------------|
| [`specs/01-domain-and-graph-schema.md`](specs/01-domain-and-graph-schema.md) | Ontología, nodos/relaciones Neo4j, constraints, reglas de negocio invariantes |
| [`specs/02-agent-architecture-and-workflows.md`](specs/02-agent-architecture-and-workflows.md) | StateGraph LangGraph, nodos, transiciones, compensaciones, human-in-the-loop |
| [`specs/03-tools-and-data-contracts.md`](specs/03-tools-and-data-contracts.md) | Pydantic schemas, SymPyTool, LLMProtocol, OCRStrategy, ErrorClassifierEngine |
| [`specs/04-testing-evals-and-infra.md`](specs/04-testing-evals-and-infra.md) | Testing strategy, evals anti-alucinación, Docker, CI/CD |

**Regla de oro**: *Si la spec no lo cubre, no se implementa. Se discute, se documenta en spec, luego se implementa.*

---

## 🛠️ Stack Técnico

- **Python 3.11+**, FastAPI, Neo4j 5.x (Docker), SymPy, Pydantic v2
- **LLM Agnóstico**: Anthropic / OpenAI / Ollama (via `LLMProtocol` + `LLMFactory`)
- **OCR Híbrido**: Local (Pix2Text, GPU) → Fallback API (Mathpix)
- **Testing**: Pytest (unit/contract/integration/e2e), testcontainers para Neo4j
- **Calidad**: Ruff (lint/format), MyPy strict, pre-commit
- **Evals**: Dataset EvAU curado, métricas Precision@1 ≥ 0.92, Hallucination Rate = 0%

---

## 🚀 Quick Start

```bash
# 1. Instalar dependencias
make install

# 2. Levantar infraestructura (Neo4j, Redis)
make up

# 3. Poblar BD con currículo base Matemáticas II
make seed

# 4. Iniciar API en modo desarrollo
make dev
```

**Endpoints principales**:
- `POST /api/ingest` — Subir imágenes/PDF → OCR → LaTeX estructurado
- `POST /api/intentos/{trace_id}/review` — Profesor aprueba/corrige LaTeX (human-in-the-loop)
- `GET /api/intentos/{intento_id}/correction` — Resultado: puntuación, feedback, errores, mastery actualizado
- `GET /api/progress/{alumna_id}` — Dashboard: mastery por concepto, top errores, racha, recomendación
- `POST /api/notes/generate` — Apunte personalizado (async)
- `WS /api/ws/agent/{trace_id}` — Streaming en tiempo real (HTMX)

---

## 📁 Estructura del Proyecto

```
mathtutor-ai/
├── AGENTS.md                    # Instrucciones maestras para agente CLI (SDD workflow)
├── MEMORY.md                    # Memoria de trabajo del agente (actualizada tras cada tarea)
├── specs/                       # Especificaciones vinculantes (SOLO .md)
│   ├── 01-domain-and-graph-schema.md
│   ├── 02-agent-architecture-and-workflows.md
│   ├── 03-tools-and-data-contracts.md
│   └── 04-testing-evals-and-infra.md
├── src/mathtutor/
│   ├── domain/                  # Entidades, VOs, reglas, eventos (PURA, sin I/O)
│   ├── graph/                   # Adaptador Neo4j (repos, mappers, queries .cypher)
│   ├── agent/                   # Orquestación LangGraph (state, nodes, tools, workflows)
│   ├── llm/                     # Capa agnóstica LLM (Protocol + Adapters + Factory)
│   ├── ingestion/               # Pipeline OCR multimodal (Strategy pattern)
│   ├── api/                     # FastAPI routers, dependencies, schemas v1
│   ├── core/                    # Config, logging (structlog), exceptions
│   └── cli/                     # Comandos Typer (seed, check-db, migrate, version)
├── tests/                       # Unit, Contract, Integration, E2E
├── evals/                       # Dataset y runners anti-alucinación
├── docker/                      # Dockerfile, compose (dev + test)
├── scripts/                     # seed_graph.py, migraciones
├── skills/                      # Skills para agente CLI (vacío por ahora)
├── pyproject.toml               # Config Ruff, MyPy, Pytest, deps
├── Makefile                     # Comandos: install, up, test, lint, dev, seed, ci
└── .env.example                 # Template de variables de entorno
```

---

## 🔄 Flujo de Trabajo SDD (Mi día a día)

```bash
# Inicio de sesión
make up          # Infra
make check       # Lint + typecheck + tests unitarios

# Ciclo por Spec
1. LEER spec relevante (specs/01, 02, 03, 04)
2. ¿Test existe? → No: ESCRIBIR test rojo (tests/unit|contract)
3. EJECUTAR test → ROJO
4. IMPLEMENTAR MÍNIMO en src/ para pasar
5. REFACTORIZAR manteniendo VERDE
6. make check (lint + typecheck + test suite completo)
7. COMMIT atómico: feat/chore/fix + scope (domain, graph, agent, llm, ingestion, api, cli, eval, infra, deps)
```

**Definición de Done por Spec**:
- ✅ Tests unitarios + contract pasan (`pytest -xvs`)
- ✅ Evals relevantes sin regresión
- ✅ `ruff check . --select=E,F,W,I,UP,B,C4` limpio
- ✅ `mypy --strict src/` limpio (cero `# type: ignore` sin justificación)
- ✅ Docstrings Google-style + `specs/` actualizada si cambió contrato

---

## 🎓 Lo que estoy aprendiendo (y practicando)

| Habilidad | Aplicación en este proyecto |
|-----------|----------------------------|
| **Spec-Driven Development** | Especs como contrato único, tests antes que código, commits atómicos |
| **Domain-Driven Design** | Entidades puras, Value Objects, Repositories, Domain Events |
| **Graph Data Modeling** | Neo4j: nodos, relaciones, constraints, índices, queries canónicas, DAG validation |
| **Hybrid AI Architecture** | LLM orquesta (planifica, explica), SymPy valida (cálculo, equivalencia) |
| **LangGraph Workflows** | StateGraph, checkpointer (SQLite), interrupts (human-in-the-loop), streaming |
| **Dependency Injection** | FastAPI Depends + Protocols para LLM, OCR, Graph, SymPy |
| **Property-based Testing** | Reglas de dominio puras (RV-01..RV-06) 100% testeables |
| **Eval-Driven Development** | Dataset EvAU, métricas anti-alucinación, regression detection |
| **Observability** | Structlog + contextvars (request_id, trace_id), Prometheus metrics |

---

## 📊 Métricas de Calidad Objetivo

| Métrica | Target | Medición |
|---------|--------|----------|
| Cobertura unit + contract | **≥ 90%** | `pytest --cov=mathtutor --cov-fail-under=90` |
| Cobertura integration | **≥ 70%** | `pytest --cov=mathtutor --cov-fail-under=70 tests/integration` |
| Precision@1 (Detección error EvAU) | **≥ 0.92** | `evals/runners/precision_recall.py` |
| Recall@1 (Detección error EvAU) | **≥ 0.88** | `evals/runners/precision_recall.py` |
| Latencia P95 corrección | **< 3.0s** | `evals/runners/latency.py` |
| Tasa alucinación matemática | **0%** | `evals/runners/hallucination_check.py` (SymPy oracle) |

---

## 🤝 Contribuir

Este es un proyecto de aprendizaje personal, pero si quieres explorar:

1. Lee `AGENTS.md` y `MEMORY.md` (cómo trabaja el agente CLI)
2. Revisa las `specs/` (son la ley)
3. `make check` debe pasar antes de cualquier PR
4. Commits: **Conventional Commits + scope** (`feat(agent): ...`, `fix(graph): ...`)

---

## 📝 Licencia

Proyecto educativo personal. Código abierto para aprendizaje y referencia.

---

> *"La mejor forma de aprender es construyendo algo que necesitas de verdad."*
>
> — Un profesor de matemáticas que quiere recuperar sus noches.