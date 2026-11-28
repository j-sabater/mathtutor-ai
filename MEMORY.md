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

### ✅ Completado (Spec 02 - Agent Architecture)
- [x] `AgentState` ya definido en `agent/state.py`
- [x] Nodos del grafo LangGraph implementados:
  - `IngestNode` - OCR pipeline + LaTeX structuring + validación RV-04
  - `ReviewOCRNode` - Human-in-the-loop interrupt (approve/correct LaTeX)
  - `CorrectNode` - SymPy validation paso a paso vs `ejercicio.pasos_solucion`
  - `ClassifyErrorsNode` - `DefaultErrorClassifierEngine` (7 reglas puras)
  - `UpdateGraphNode` - Saga pattern con compensación real (delete/unlink rollback)
  - `GenerateRecommendationNode` - Generate-validate-retry loop con LLM + SymPy
- [x] `build_main_graph()` + `build_main_graph_with_deps()` con `AsyncSqliteSaver` + `interrupt_before=["review_ocr"]`
- [x] Saga compensation real: `delete_intento`, `unlink_intento_error`, `unlink_recommendation`
- [x] Generate-validate-retry: LLM genera → SymPy valida (LaTeX parseable + solución correcta) → retry máx 3
- [x] Prompt management: `PromptRegistry` con Jinja2 versionado (`v1.0.0` + symlink `current`)
- [x] 4 plantillas: `generate_exercise.j2`, `explain_error.j2`, `correction_feedback.j2`, `generate_note.j2`

### ✅ Completado (Spec 03 - Tools & Contracts)
- [x] `GraphRepository` implementation real: `Neo4jRepositories` en `repositories_impl.py` (CRUD completo + delete/unlink)
- [x] `SymPyTool` integration completa en `CorrectNode` (comparación paso a paso con solución canónica)
- [x] OCR pipeline integration real en `IngestNode` (mock OCR pipeline con validación LaTeX)

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

1. **SymPyTool timeout handling**: `timeout_seconds` configurado pero no enforceado con `asyncio.wait_for`.
2. **OCR local strategy**: `Pix2TextStrategy` requiere modelo descargado y GPU; fallback a CPU no testeado.
3. **LangGraph checkpointer**: `AsyncSqliteSaver` funciona con interrupts, pero cleanup de context manager pendiente.
4. **Testcontainers**: `tests/integration/` vacío. Necesario para `make test-int`.
5. **WebSocket streaming**: Endpoint `WS /api/ws/agent/{trace_id}` no implementado aún.
6. **Resume API**: Endpoint para reanudar tras `review_ocr` interrupt pendiente.

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
| **LangGraph Workflow** | ✅ 6 nodos + AsyncSqliteSaver + interrupt review_ocr |
| **Prompt Registry** | ✅ Jinja2 versionado (v1.0.0 + current symlink) |
| **Saga Compensation** | ✅ delete_intento, unlink_intento_error, unlink_recommendation |
| **LLM Integration** | ✅ GenerateRecommendationNode con LLMProtocol real |

---

## 🎯 Próximos Pasos (Spec 02 Completion & Spec 04)

1. **Tests unitarios** (`tests/unit/agent/nodes/`): test cada nodo con mocks
2. **Tests de contrato** (`tests/contract/agent/`): validar transiciones AgentState
3. **WebSocket streaming**: `WS /api/ws/agent/{trace_id}` + `StreamChunk` emission
4. **Resume API**: POST endpoint para reanudar tras `review_ocr` interrupt
5. **Integration tests** (`tests/integration/`): testcontainers Neo4j + LLM mock
6. **Evals anti-alucinación**: Dataset EvAU mínimo + runners Precision/Recall/Hallucination

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

*Última actualización: 2026-11-27 — Spec 02 Agent Architecture completed + pushed to https://github.com/j-sabater/mathtutor-ai (branch: feat/spec2-agent-architecture)*
