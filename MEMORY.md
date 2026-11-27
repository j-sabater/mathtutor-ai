# MEMORY.md — Memoria de Trabajo del Agente CLI

> **Actualiza este archivo al terminar cada tarea** (ver `AGENTS.md` sección "Forma de trabajar y Memoria").

---

## 📋 Estado Actual del Proyecto

### ✅ Completado (Baseline MVP - Spec 01)
- [x] Estructura base del repositorio (carpetas, pyproject.toml, Makefile, Docker)
- [x] **Dominio puro** (`src/mathtutor/domain/`):
  - Entidades: `Concepto`, `Ejercicio`, `Intento`, `PatronDeError`, `User`, `SesionEstudio`
  - Value Objects: `PasoMatematico`, `PatronErrorRef`, `MasterySnapshot`, `LatexString`, `OCRResult`, `StepValidation`, `ErrorClassification`, `GraphUpdateResult`
  - Eventos: `IntentoCreado`, `IntentoCorregido`, `MasteryActualizado`, `PatronErrorDetectado`, `EjercicioRecomendado`, `ApunteGenerado`
  - Reglas: RV-01 a RV-06 (`validate_prerequisite_dag`, `validate_test_weights_sum`, `validate_mastery_bounds`, `validate_latex_parseable`, `validate_ocr_confidence`, `validate_paso_sequencial`)
- [x] **Adaptador Neo4j** (`src/mathtutor/graph/`):
  - `GraphRepository` protocol + DTOs
  - Mappers entidad ↔ nodo
  - Session manager (driver, session, transaction)
  - Queries .cypher separadas por entidad (schema, conceptos, ejercicios, intentos, patrones, mastery, recommendations)
- [x] **Herramientas deterministas** (`src/mathtutor/agent/tools/`):
  - `SymPyToolProtocol` (8 operaciones atómicas)
  - `Latex2SymPyTool` implementation (latex2sympy2 + SymPy)
  - `ErrorClassifierEngine` + `DefaultErrorClassifierEngine` (reglas puras: chain rule, sign error, L'Hôpital, indeterminación, constante integración, simplificación, dominio)
- [x] **Capa LLM agnóstica** (`src/mathtutor/llm/`):
  - `LLMProtocol` + `ToolCallingLLM`
  - Adapters: Anthropic, OpenAI, Ollama
  - `LLMFactory` por config
- [x] **Pipeline OCR** (`src/mathtutor/ingestion/`):
  - `OCRStrategy` protocol
  - `Pix2TextStrategy` (local, GPU)
  - `MathpixStrategy` (fallback API)
  - `OCRPipeline` orquestador híbrido (local → fallback)
- [x] **API REST** (`src/mathtutor/api/`):
  - Schemas v1 (Pydantic frozen, extra=forbid)
  - Routes: ingest, review, correction, progress, notes, agent, websocket
  - Dependencies (DI para repos, LLM, OCR, SymPy, ErrorClassifier)
- [x] **Core & CLI**:
  - Config (Pydantic Settings), Logging (structlog), Exceptions
  - Typer CLI: version, config, check-db, seed, migrate
- [x] **Tests unitarios** (`tests/unit/`):
  - Entidades, reglas, value objects, error classifier
- [x] **Infra**: Docker, docker-compose, seed script, .env.example, README

### 🔄 En Progreso / Próximos Pasos (Spec 02 - Agent Architecture)
- [ ] `AgentState` ya definido en `agent/state.py`
- [ ] Nodos del grafo LangGraph: `IngestNode`, `ReviewOCRNode`, `CorrectNode`, `ClassifyErrorsNode`, `UpdateGraphNode`, `GenerateRecommendationNode`
- [ ] `build_main_graph()` con checkpointer (SqliteSaver) + `interrupt_before=["review_ocr"]`
- [ ] Saga pattern en `UpdateGraphNode` (compensación/rollback)
- [ ] Generate-validate-retry loop en `GenerateRecommendationNode`
- [ ] Prompt management (`agent/prompts/versions/current/`)
- [ ] Streaming `StreamChunk` via WebSocket

### 📦 Pendientes (Spec 03 - Tools & Contracts completados parcialmente)
- [ ] GraphRepository implementation real (Cypher execution via session)
- [ ] SymPyTool integration completa en `CorrectNode`
- [ ] OCR pipeline integration real en `IngestNode`

### 🎯 Objetivos de Aprendizaje Actuales
1. **LangGraph**: StateGraph, interrupts, checkpointer, streaming
2. **Neo4j real**: Testcontainers para integration tests, transacciones, rollback
3. **Evals anti-alucinación**: Dataset EvAU, runners, métricas Precision/Recall/Hallucination
4. **Prompt engineering**: Jinja2 templates, versionado, A/B testing

---

## 🎯 Contexto de la Tarea Actual

> **Tarea**: Configurar repositorio GitHub público, crear README narrativo, MEMORY.md, actualizar AGENTS.md con sección de memoria, crear carpeta skills.

> **Spec activa**: Ninguna (setup inicial completado). Próxima: `specs/02-agent-architecture-and-workflows.md`

> **Último commit**: Baseline MVP - Domain module + infrastructure (Spec 01)

---

## 📝 Decisiones Técnicas Clave (para no repetir debates)

| Decisión | Razón | Spec/Regla |
|----------|-------|------------|
| `returns.Result` para operaciones fallibles | Sin exceptions en flujo controlado, tipado explícito | AGENTS.md P3, Spec 03 |
| `LatexString` valida con `sympy.parse_latex` | RV-04: LaTeX debe ser parseable por SymPy | Spec 01 §6 |
| `frozen=True` + `extra='forbid'` en todos los Pydantic | Inmutabilidad, detección temprana de typos | AGENTS.md 3.3, Spec 03 §1 |
| Cypher solo en `graph/queries/*.cypher` | Separación capas, testabilidad, migrabilidad | AGENTS.md P2 |
| `LLMProtocol` + `LLMFactory` | Agnosticismo proveedores, evals, costes | AGENTS.md P3, Spec 03 §4 |
| `structlog` + contextvars | Observabilidad unificada, correlación trazas | AGENTS.md P5 |
| Kahn's algorithm para validar DAG | RV-01: prerrequisitos sin ciclos | Spec 01 §5, `rules.py` |
| EWMA (α=0.3) para Mastery Level | RN-05: recálculo event-driven, suave | Spec 01 §4.4, `mastery.cypher` |
| Strategy Pattern para OCR | Local (GPU) → Fallback (API) configurable | Spec 03 §3.4-3.6 |
| ErrorClassifierEngine puro (sin LLM) | Determinista, 100% testeable, 0 alucinaciones | Spec 02 §3.4, Spec 03 §6 |

---

## 🐛 Issues Conocidos / Deuda Técnica

1. **GraphRepository implementation**: Falta implementación real ejecutando queries Cypher via `Neo4jSessionManager`. Actualmente solo protocol + DTOs.
2. **SymPyTool timeout handling**: `timeout_seconds` configurado pero no enforceado con `asyncio.wait_for`.
3. **OCR local strategy**: `Pix2TextStrategy` requiere modelo descargado y GPU; fallback a CPU no testeado.
4. **Prompt templates**: Carpeta `agent/prompts/` creada pero vacía. Pendiente Spec 02 §6.
5. **LangGraph checkpointer**: `SqliteSaver` configurado pero no probado con interrupts reales.
6. **Testcontainers**: `tests/integration/` vacío. Necesario para `make test-int`.

---

## 📚 Referencias Rápidas

| Archivo | Qué Contiene |
|---------|--------------|
| `AGENTS.md` | Reglas de proceso, convenciones, prohibiciones, workflow SDD |
| `specs/01-domain-and-graph-schema.md` | Ontología, grafo, reglas negocio, queries, VOs, eventos |
| `specs/02-agent-architecture-and-workflows.md` | LangGraph, nodos, workflows, compensaciones, streaming |
| `specs/03-tools-and-data-contracts.md` | Pydantic schemas, SymPyTool, LLMProtocol, OCRStrategy |
| `specs/04-testing-evals-and-infra.md` | Testing strategy, evals, Docker, CI/CD |
| `pyproject.toml` | Ruff, MyPy, Pytest, deps, scripts |
| `Makefile` | Comandos: install, up, test, lint, dev, seed, ci |
| `docker/docker-compose.yml` | Neo4j + Redis + API (dev) |
| `scripts/seed_graph.py` | Puebla BD con currículo Matemáticas II |

---

## 🔄 Próximas Acciones (Prioridad)

1. **Implementar GraphRepositoryImpl** con queries Cypher reales
2. **Crear nodos LangGraph** según Spec 02 §3
3. **Conectar IngestNode → ReviewOCRNode → CorrectNode** con checkpointer
4. **Tests de integración** con Neo4j testcontainer
5. **Primera eval** anti-alucinación con dataset EvAU mínimo

---

*Última actualización: 2026-11-26 — Baseline MVP completado (Spec 01)*
---

## 🐳 Estado Docker / WSL (Sesión Actual)

> **Contexto**: Docker instalado en WSL2, usuario añadido al grupo `docker`, pero **requiere nueva sesión** para aplicar cambios de grupo.

### Próximo paso inmediato al reabrir terminal:
```bash
# 1. Verificar Docker funcionando
docker run --rm hello-world

# 2. Si OK, levantar infra
make up

# 3. Poblar BD
make seed

# 4. Iniciar API dev
make dev
```

### Comandos alternativos si persisten problemas de permisos:
```bash
# Temporal (solo sesión actual)
sudo chmod 666 /var/run/docker.sock

# O usar sudo directamente
sudo docker compose -f docker/docker-compose.yml up -d
```

---

*Última actualización: 2026-11-26 — Baseline MVP completado (Spec 01) | Docker WSL pendiente reinicio sesión*

---

## 🐳 Estado Docker / WSL (Sesión Actual) - RESUELTO ✅

> **Problemas resueltos**: 
> - Neo4j 6.x async API (usar `AsyncGraphDatabase` no `GraphDatabase`)
> - Pydantic v2 `with_info_plain_validator_function` signature change
> - `latex2sympy2.latex2sympy` function vs `Latex2Sympy` class
> - `returns.result` Success/Failure imports
> - Session/Transaction close() await patterns

### Próximo paso inmediato al reabrir terminal:
```bash
# 1. Verificar Docker funcionando
docker run --rm hello-world

# 2. Levantar infra
make up

# 3. Poblar BD (ya seed, pero por si acaso)
make seed

# 4. Iniciar API dev
make dev
```

---

## 📊 Estado Actual Verificado (2026-11-27)

| Componente | Estado |
|------------|--------|
| **API Health** | ✅ `{"status":"ok","version":"0.1.0"}` |
| **Swagger UI** | ✅ http://localhost:8000/docs |
| **Neo4j** | ✅ Conectado, 16 conceptos, 18 prerrequisitos, 1 usuario |
| **Seed Graph** | ✅ Completado sin warnings |
| **CLI** | ✅ `check-db`, `seed`, `config`, `version`, `migrate` |
| **SymPy Tool** | ✅ Parse, Diff, Equals funcionando |
| **Error Classifier** | ✅ Chain rule, Sign error detectados |

---

## 🎯 Próximos Pasos (Spec 02 - Agent Architecture)

1. **Implementar nodos LangGraph** según `specs/02-agent-architecture-and-workflows.md`:
   - `IngestNode` - OCR + estructura LaTeX
   - `ReviewOCRNode` - Human-in-the-loop (interrupt)
   - `CorrectNode` - SymPy validation paso a paso
   - `ClassifyErrorsNode` - ErrorClassifierEngine
   - `UpdateGraphNode` - Saga pattern con compensación
   - `GenerateRecommendationNode` - Generate-validate-retry loop

2. **Configurar checkpointer** (SqliteSaver) + `interrupt_before=["review_ocr"]`

3. **Prompt management** (`agent/prompts/versions/current/`)

4. **Streaming WebSocket** (`StreamChunk`)

---

## 📝 Decisiones Técnicas Recientes

| Decisión | Archivo | Razón |
|----------|---------|-------|
| `AsyncGraphDatabase.driver` en lugar de `GraphDatabase.driver` | `session.py` | Neo4j 6.x usa driver async nativo |
| `await session.run()` y `await tx.run()` | `session.py` | Neo4j 6.x coroutines |
| `await session.close()` y `await driver.close()` | `session.py` | Neo4j 6.x async close |
| `latex2sympy2.latex2sympy()` function | `sympy_tool.py` | API cambió de clase a función |
| `with_info_plain_validator_function(cls._validate, serialization=...)` | `value_objects.py` | Pydantic v2 keyword-only args |
| `from returns.result import Success, Failure` | `error_classifier.py` | API correcta de returns |

---

## 🔄 Próximas Acciones (Prioridad)

1. **Spec 02**: Implementar nodos LangGraph + workflows
2. **Tests de integración**: `tests/integration/` con testcontainers
3. **Evals**: Dataset EvAU mínimo + runners anti-alucinación
4. **Prompt templates**: Jinja2 versionados en `agent/prompts/`

---

*Última actualización: 2026-11-27 — Spec 01 completo + Neo4j 6.x/Pydantic v2 fixes pushed to https://github.com/j-sabater/mathtutor-ai*
