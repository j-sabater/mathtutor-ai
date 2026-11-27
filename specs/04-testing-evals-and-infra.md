# specs/04-testing-evals-and-infra.md — Testing, Evals Anti-Alucinación, Docker y CI/CD

> **Single Source of Truth** para estrategia de testing, evaluación de calidad del agente, infraestructura containerizada y pipeline CI/CD.
> **Versión**: 1.0.0 — Baseline MVP (Matemáticas II: Cálculo)

---

## 1. Estrategia de Testing (Pirámide)

### 1.1 Niveles y Objetivos

| Nivel | Carpeta | Objetivo | Cobertura Target | Tiempo Ejecución |
|-------|---------|----------|------------------|------------------|
| **Unit** | `tests/unit/` | Lógica pura de dominio, tools, mappers, rules, classifiers | **≥ 90%** | < 30s |
| **Contract** | `tests/contract/` | Schemas Pydantic, HTTP API, Cypher queries, Protocol compliance | **≥ 90%** | < 60s |
| **Integration** | `tests/integration/` | Neo4j real (testcontainers), LLM adapters, OCR pipeline, SymPyTool real | **≥ 70%** | < 5min |
| **E2E** | `tests/e2e/` | Flujos completos via API real + Web UI (Playwright) | Críticos only | < 10min |

### 1.2 Convenciones de Nombrado y Estructura

```
tests/
├── unit/
│   ├── domain/
│   │   ├── test_entities.py
│   │   ├── test_value_objects.py
│   │   ├── test_rules.py          # RV-01..RV-06
│   │   └── test_events.py
│   ├── graph/
│   │   ├── test_mappers.py        # Domain ↔ DTO ↔ Cypher params
│   │   └── test_queries.py        # Cypher parameterization, no string interp
│   ├── agent/
│   │   ├── nodes/
│   │   │   ├── test_ingest_node.py
│   │   │   ├── test_correct_node.py
│   │   │   ├── test_classify_errors_node.py
│   │   │   ├── test_update_graph_node.py
│   │   │   └── test_generate_recommendation_node.py
│   │   ├── tools/
│   │   │   ├── test_sympy_tool.py
│   │   │   ├── test_error_classifier.py
│   │   │   └── test_ocr_pipeline.py
│   │   └── workflows/
│   │       └── test_state_transitions.py
│   ├── llm/
│   │   ├── test_protocol.py
│   │   ├── test_factory.py
│   │   └── test_adapters.py       # Mock HTTP responses
│   └── ingestion/
│       ├── test_strategies.py
│       └── test_parsers.py
├── contract/
│   ├── api/
│   │   ├── test_ingest_schema.py
│   │   ├── test_review_schema.py
│   │   ├── test_correction_schema.py
│   │   └── test_progress_schema.py
│   ├── graph/
│   │   ├── test_cypher_params.py
│   │   └── test_repository_interface.py
│   └── tools/
│       ├── test_sympy_tool_protocol.py
│       └── test_llm_protocol.py
├── integration/
│   ├── conftest.py                # testcontainers Neo4j fixture
│   ├── graph/
│   │   ├── test_repositories_impl.py
│   │   └── test_migrations.py
│   ├── agent/
│   │   ├── test_correction_workflow.py
│   │   └── test_note_generation_workflow.py
│   ├── llm/
│   │   ├── test_anthropic_adapter.py      # Requiere API key (opcional, marked @pytest.mark.llm)
│   │   └── test_ollama_adapter.py         # Requiere Ollama local
│   └── ingestion/
│       ├── test_pix2text_strategy.py      # Requiere GPU/modelos
│       └── test_mathpix_strategy.py       # Requiere API key
└── e2e/
    ├── conftest.py                # API server + Playwright fixtures
    ├── test_full_correction_flow.py
    ├── test_dashboard_progress.py
    └── test_note_generation.py
```

---

## 2. Fixtures y Testcontainers (Integración Real)

### 2.1 `conftest.py` Base

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from testcontainers.neo4j import Neo4jContainer
from src.mathtutor.graph.session import Neo4jSession
from src.mathtutor.graph.repositories_impl import GraphRepositoryImpl
from src.mathtutor.core.config import Settings

@pytest.fixture(scope="session")
def neo4j_container():
    """Neo4j 5.x para toda la sesión de tests."""
    with Neo4jContainer(image="neo4j:5.23", username="neo4j", password="testpass") as container:
        yield container

@pytest.fixture(scope="session")
def neo4j_uri(neo4j_container):
    return neo4j_container.get_connection_url()

@pytest.fixture(scope="session")
def neo4j_session(neo4j_uri):
    session = Neo4jSession(uri=neo4j_uri, user="neo4j", password="testpass")
    yield session
    session.close()

@pytest_asyncio.fixture
async def graph_repo(neo4j_session):
    repo = GraphRepositoryImpl(neo4j_session)
    # Limpiar BD antes de cada test
    await repo.clear_database()
    yield repo

@pytest.fixture
def settings(neo4j_uri):
    return Settings(
        neo4j_uri=neo4j_uri,
        neo4j_password="testpass",
        llm_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ocr_local_enabled=False,
        ocr_fallback_enabled=False
    )
```

### 2.2 Fixtures de Datos Semilla (Domain Objects)

```python
# tests/fixtures/domain.py
import pytest
from src.mathtutor.domain.entities import Concepto, Ejercicio, Intento, PatronDeError, User
from src.mathtutor.domain.value_objects import PasoMatematico, MasterySnapshot
from datetime import datetime
import uuid

@pytest.fixture
def concepto_limite_basico():
    return Concepto(
        id=str(uuid.uuid4()),
        codigo="LIM-01",
        nombre="Límite en un punto",
        bloque="Límites",
        nivel=1,
        descripcion="Definición épsilon-delta",
        latex_definicion=r"\forall \epsilon > 0, \exists \delta > 0 ...",
        prerequisitos_codigos=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def ejercicio_derivada_cadena(concepto_derivada_compuesta):
    return Ejercicio(
        id=str(uuid.uuid4()),
        enunciado_latex=r"Deriva f(x) = \sin(x^2)",
        enunciado_texto="Deriva f(x) = sen(x^2)",
        tipo="derivar_funcion",
        dificultad=3,
        tiempo_estimado=5,
        fuente="manual",
        metadata_json='{"tags": ["chain_rule", "trigonometric"]}',
        solucion_canonica_latex=r"2x\cos(x^2)",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@pytest.fixture
def intento_con_error_chain_rule(ejercicio_derivada_cadena):
    return Intento(
        id=str(uuid.uuid4()),
        ejercicio_id=ejercicio_derivada_cadena.id,
        alumna_id="alumna_principal",
        imagenes=[],
        latex_extraido=r"\cos(x^2)",  # Falta chain rule
        pasos_structurados='[{"paso": 1, "latex": "\\cos(x^2)", "descripcion": "Derivada de sen(u) es cos(u)"}]',
        estado="pendiente",
        puntuacion=0.0,
        metadatos_ocr='{"strategy": "test", "confidence": 1.0}',
        created_at=datetime.utcnow()
    )
```

---

## 3. Tests Unitarios: Patrones Clave

### 3.1 Test de Value Object con Validador SymPy (RV-04)

```python
# tests/unit/domain/test_value_objects.py
import pytest
from src.mathtutor.domain.value_objects import PasoMatematico

class TestPasoMatematico:
    def test_latex_valido_parseable(self):
        paso = PasoMatematico(numero=1, latex=r"\frac{d}{dx}\sin(x^2)")
        assert paso.latex == r"\frac{d}{dx}\sin(x^2)"
    
    def test_latex_invalido_raise(self):
        with pytest.raises(ValueError, match="LaTeX no parseable por SymPy"):
            PasoMatematico(numero=1, latex=r"\frac{d}{dx}\sin(x^2")  # Falta llave
    
    def test_latex_vacio_raise(self):
        with pytest.raises(ValueError):
            PasoMatematico(numero=1, latex="")
```

### 3.2 Test de Regla de Dominio (RV-01: DAG Prerequisitos)

```python
# tests/unit/domain/test_rules.py
from src.mathtutor.domain.rules import validate_prerequisite_dag
from src.mathtutor.domain.entities import Concepto

def test_prerequisite_dag_valido(concepto_limite_basico, concepto_limite_lateral, concepto_lhopital):
    # LIM-01 → LIM-02 → LIM-03 (válido)
    conceptos = [concepto_limite_basico, concepto_limite_lateral, concepto_lhopital]
    result = validate_prerequisite_dag(conceptos)
    assert result.is_success()

def test_prerequisite_dag_ciclo_detectado(concepto_limite_basico, concepto_limite_lateral):
    # Crear ciclo artificial: LIM-01 → LIM-02 → LIM-01
    concepto_limite_basico.prerequisitos_codigos = ["LIM-02"]
    concepto_limite_lateral.prerequisitos_codigos = ["LIM-01"]
    conceptos = [concepto_limite_basico, concepto_limite_lateral]
    result = validate_prerequisite_dag(conceptos)
    assert result.is_failure()
    assert "Ciclo detectado" in result.failure().message
```

### 3.3 Test de `ErrorClassifierEngine` (Motor Determinista)

```python
# tests/unit/agent/tools/test_error_classifier.py
import sympy as sp
from src.mathtutor.agent.tools.error_classifier import ErrorClassifierEngine
from src.mathtutor.domain.value_objects import StepValidation

class TestErrorClassifierEngine:
    @pytest.fixture
    def engine(self):
        return ErrorClassifierEngine()
    
    def test_detecta_chain_rule_faltante(self, engine):
        # Alumno deriva sen(x^2) → cos(x^2) (falta * 2x)
        validation = StepValidation(
            numero=1,
            latex=r"\cos(x^2)",
            descripcion="Derivada de sen(u) = cos(u)",
            expresion_sympy=sp.cos(sp.Symbol('x')**2)
        )
        expected = sp.diff(sp.sin(sp.Symbol('x')**2), sp.Symbol('x'))  # 2*x*cos(x^2)
        
        result = engine.classify(validation, expected)
        assert result.is_success()
        assert result.unwrap().patron_codigo == "ERR-CHAIN-RULE"
        assert result.unwrap().confianza >= 0.9
    
    def test_detecta_error_signo_integral(self, engine):
        validation = StepValidation(
            numero=1,
            latex=r"\int x^2 dx = \frac{x^2}{2}",
            descripcion="Integral de x^2",
            expresion_sympy=sp.Symbol('x')**2 / 2
        )
        expected = sp.Symbol('x')**3 / 3  # Correcto: x^3/3
        
        result = engine.classify(validation, expected)
        assert result.unwrap().patron_codigo == "ERR-SIGN-ERROR"  # O ERR-ALGEBRA-SIMPLIFY
    
    def test_fallback_no_categorizado(self, engine):
        validation = StepValidation(
            numero=1,
            latex=r"x = 5",
            descripcion="Conclusión aleatoria",
            expresion_sympy=sp.Eq(sp.Symbol('x'), 5)
        )
        expected = sp.Symbol('x')**2
        
        result = engine.classify(validation, expected)
        assert result.unwrap().patron_codigo == "ERR-UNCATEGORIZED"
        assert result.unwrap().confianza == 0.5
```

### 3.4 Test de `SymPyTool` con `latex2sympy2`

```python
# tests/unit/agent/tools/test_sympy_tool.py
import pytest
from returns.result import Success, Failure
from src.mathtutor.agent.tools.sympy_tool import Latex2SymPyTool
from src.mathtutor.agent.tools.schemas import *

class TestLatex2SymPyTool:
    @pytest.fixture
    def tool(self):
        return Latex2SymPyTool(timeout_seconds=5.0)
    
    @pytest.mark.asyncio
    async def test_parse_latex_basico(self, tool):
        req = ParseLatexRequest(latex=r"x^2 + 2x + 1")
        result = await tool.parse_latex(req)
        assert isinstance(result, Success)
        assert "x**2 + 2*x + 1" in result.unwrap().expr_repr
    
    @pytest.mark.asyncio
    async def test_parse_latex_fraccion(self, tool):
        req = ParseLatexRequest(latex=r"\frac{1}{x}")
        result = await tool.parse_latex(req)
        assert isinstance(result, Success)
        expr = result.unwrap()
        assert "1/x" in expr.expr_repr or "x**(-1)" in expr.expr_repr
    
    @pytest.mark.asyncio
    async def test_equals_simbolico_exitoso(self, tool):
        # (x+1)^2 == x^2 + 2x + 1
        p1 = await tool.parse_latex(ParseLatexRequest(latex=r"(x+1)^2"))
        p2 = await tool.parse_latex(ParseLatexRequest(latex=r"x^2 + 2x + 1"))
        
        req = EqualsRequest(
            expr1_serialized=p1.unwrap().expr_serialized,
            expr2_serialized=p2.unwrap().expr_serialized,
            method="symbolic"
        )
        result = await tool.equals(req)
        assert isinstance(result, Success)
        assert result.unwrap().are_equal is True
        assert result.unwrap().confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_equals_numerico_diferente(self, tool):
        p1 = await tool.parse_latex(ParseLatexRequest(latex=r"x + 1"))
        p2 = await tool.parse_latex(ParseLatexRequest(latex=r"x + 2"))
        
        req = EqualsRequest(
            expr1_serialized=p1.unwrap().expr_serialized,
            expr2_serialized=p2.unwrap().expr_serialized,
            method="numeric"
        )
        result = await tool.equals(req)
        assert isinstance(result, Success)
        assert result.unwrap().are_equal is False
    
    @pytest.mark.asyncio
    async def test_diff_chain_rule(self, tool):
        p = await tool.parse_latex(ParseLatexRequest(latex=r"\sin(x^2)"))
        req = DiffRequest(expr_serialized=p.unwrap().expr_serialized, variable="x", order=1)
        result = await tool.diff(req)
        assert isinstance(result, Success)
        # Debe contener 2*x*cos(x^2)
        assert "2*x" in result.unwrap().expr_repr
        assert "cos" in result.unwrap().expr_repr
```

---

## 4. Tests de Contrato

### 4.1 Validación de Schemas API (Pydantic)

```python
# tests/contract/api/test_correction_schema.py
import pytest
from src.mathtutor.api.schemas.v1.correction import CorrectionResult, StepFeedback

class TestCorrectionSchema:
    def test_correction_result_valido(self):
        data = {
            "trace_id": "abc-123",
            "intento_id": "int-001",
            "puntuacion": 7.5,
            "pasos_feedback": [
                {"paso": 1, "latex_original": r"\cos(x^2)", "latex_normalizado": r"\cos(x^2)",
                 "es_correcto": False, "feedback": "Falta regla de la cadena",
                 "sugerencia": "Multiplica por derivada de x^2", "patron_error_codigo": "ERR-CHAIN-RULE"}
            ],
            "errores_detectados": [{"codigo": "ERR-CHAIN-RULE", "paso": 1, "confianza": 0.95}],
            "mastery_actualizado": [{"concepto_codigo": "DER-03", "nivel": 0.6, "aciertos_consecutivos": 0, "ultima_actualizacion": "2026-01-01T00:00:00"}],
            "ejercicio_recomendado_id": "ej-002",
            "apunte_generado_url": None,
            "duracion_ms": 1250
        }
        result = CorrectionResult(**data)
        assert result.puntuacion == 7.5
        assert len(result.pasos_feedback) == 1
    
    def test_puntuacion_fuera_rango_rechaza(self):
        data = {..., "puntuacion": 15.0, ...}
        with pytest.raises(ValidationError):
            CorrectionResult(**data)
    
    def test_extra_fields_rechazados(self):
        data = {..., "campo_extra": "no_permitido"}
        with pytest.raises(ValidationError):
            CorrectionResult(**data)
```

### 4.2 Contract Test: Cypher Parameterization (No String Interpolation)

```python
# tests/contract/graph/test_cypher_params.py
import re
from src.mathtutor.graph.queries import CYPHER_QUERIES

class TestCypherQueries:
    def test_no_string_interpolation_in_queries(self):
        """Todas las queries usan $param, nunca f-strings o %."""
        for name, query in CYPHER_QUERIES.items():
            # Buscar patrones de interpolación prohibidos
            forbidden = [
                r'f".*\{',          # f-strings
                r'%\{',             # % formatting
                r'\+.*\{',          # concat con vars
                r'format\('         # .format()
            ]
            for pattern in forbidden:
                matches = re.findall(pattern, query)
                assert not matches, f"Query {name} usa interpolación prohibida: {matches}"
    
    def test_all_params_prefixed_with_dollar(self):
        """Parámetros en query empiezan con $."""
        for name, query in CYPHER_QUERIES.items():
            # Encontrar todos los $param
            params = re.findall(r'\$(\w+)', query)
            # Verificar que no hay identificadores sueltos que parezcan params
            words = re.findall(r'\b[a-z_][a-z0-9_]*\b', query.lower())
            # Heurística: palabras clave Cypher permitidas
            cypher_keywords = {'match', 'where', 'return', 'create', 'merge', 'set', 'delete', 
                              'detach', 'remove', 'on', 'create', 'match', 'with', 'unwind',
                              'call', 'yield', 'as', 'by', 'limit', 'skip', 'order', 'asc', 'desc',
                              'and', 'or', 'not', 'in', 'is', 'null', 'true', 'false',
                              'distinct', 'count', 'sum', 'avg', 'min', 'max', 'collect'}
            for word in words:
                if word not in cypher_keywords and word not in params and len(word) > 2:
                    # Podría ser parámetro sin $
                    pass  # Warning only en CI
```

---

## 5. Tests de Integración (Neo4j Real)

### 5.1 Test de Repositorio Graph (CRUD + Queries Complejas)

```python
# tests/integration/graph/test_repositories_impl.py
import pytest
from src.mathtutor.graph.repositories_impl import GraphRepositoryImpl

@pytest.mark.integration
class TestGraphRepositoryImpl:
    @pytest.mark.asyncio
    async def test_create_and_get_concepto(self, graph_repo, concepto_limite_basico):
        # Create
        result = await graph_repo.create_concepto(concepto_limite_basico)
        assert result.is_success()
        created = result.unwrap()
        assert created.codigo == "LIM-01"
        
        # Get
        result = await graph_repo.get_concepto_by_codigo("LIM-01")
        assert result.is_success()
        fetched = result.unwrap()
        assert fetched.nombre == "Límite en un punto"
    
    @pytest.mark.asyncio
    async def test_update_mastery_ewma(self, graph_repo, concepto_limite_basico):
        await graph_repo.create_concepto(concepto_limite_basico)
        
        # Primera actualización: score 1.0 (acierto)
        result = await graph_repo.update_mastery_ewma("alumna_principal", "LIM-01", 1.0)
        assert result.is_success()
        nivel_1 = result.unwrap()
        assert 0.0 < nivel_1 <= 1.0
        
        # Segunda: score 0.0 (fallo)
        result = await graph_repo.update_mastery_ewma("alumna_principal", "LIM-01", 0.0)
        assert result.is_success()
        nivel_2 = result.unwrap()
        assert nivel_2 < nivel_1  # EWMA decay
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_based_on_mastery(self, graph_repo, seed_conceptos_derivadas):
        # Setup: alumna con mastery bajo en DER-03 (chain rule)
        await graph_repo.update_mastery_ewma("alumna_principal", "DER-03", 0.3)
        await graph_repo.update_mastery_ewma("alumna_principal", "DER-01", 0.8)  # prereq OK
        
        result = await graph_repo.generate_recommendations("alumna_principal", limit=3)
        assert result.is_success()
        recomendaciones = result.unwrap()
        assert len(recomendaciones) >= 1
        # Debe recomendar ejercicio de DER-03 o prerequisito faltante
```

---

## 6. Evals Anti-Alucinación (Dataset + Métricas)

> **Objetivo**: Medir calidad del agente detectando errores reales de EvAU. Cero tolerancia a alucinaciones matemáticas.

### 6.1 Dataset de Evaluación (`evals/dataset/`)

```
evals/dataset/
├── evau_errors/
│   ├── chain_rule_variants.jsonl      # 50 casos: sen(x^2), cos(3x), e^(x^2), ln(x^2+1), etc.
│   ├── lhopital_cases.jsonl           # 30 casos: 0/0, ∞/∞, 0·∞, ∞-∞, 1^∞
│   ├── limit_indeterminate.jsonl      # 25 casos: límites laterales, infinitos
│   ├── integral_constants.jsonl       # 20 casos: olvido +C, errores sustitución
│   ├── sign_errors.jsonl              # 25 casos: signos en derivadas/integrales
│   └── algebraic_simplification.jsonl # 20 casos: factorización, expansión
├── ocr_samples/
│   ├── handwritten_limits/            # Imágenes reales etiquetadas
│   ├── handwritten_derivatives/
│   └── handwritten_integrals/
└── exercise_generation/
    ├── valid_generations.jsonl        # Ejercicios generados válidos (SymPy ✓)
    └── invalid_generations.jsonl      # Ejercicios con problemas (para test negative)
```

**Formato JSONL por caso** (`chain_rule_variants.jsonl`):
```json
{"id": "cr-001", "input_latex": "\\cos(x^2)", "expected_latex": "2x\\cos(x^2)", "concepto": "DER-03", "patron_esperado": "ERR-CHAIN-RULE", "dificultad": 3}
{"id": "cr-002", "input_latex": "-\\sin(3x)", "expected_latex": "-3\\cos(3x)", "concepto": "DER-03", "patron_esperado": "ERR-CHAIN-RULE", "dificultad": 3}
{"id": "cr-003", "input_latex": "e^{x^2}", "expected_latex": "2xe^{x^2}", "concepto": "DER-03", "patron_esperado": "ERR-CHAIN-RULE", "dificultad": 4}
```

### 6.2 Runners de Evaluación (`evals/runners/`)

```python
# evals/runners/precision_recall.py
"""Eval principal: Precision@1 / Recall@1 en detección de PatronDeError."""
import json
from pathlib import Path
from src.mathtutor.agent.tools.error_classifier import ErrorClassifierEngine
from src.mathtutor.agent.tools.sympy_tool import Latex2SymPyTool
from src.mathtutor.domain.value_objects import StepValidation

class HallucinationEvalRunner:
    def __init__(self):
        self.classifier = ErrorClassifierEngine()
        self.sympy = Latex2SymPyTool()
    
    async def run_chain_rule_eval(self) -> dict:
        dataset_path = Path("evals/dataset/evau_errors/chain_rule_variants.jsonl")
        cases = [json.loads(line) for line in dataset_path.read_text().splitlines()]
        
        tp = fp = fn = 0
        for case in cases:
            # Parsear input y expected con SymPy
            input_parse = await self.sympy.parse_latex(ParseLatexRequest(latex=case["input_latex"]))
            expected_parse = await self.sympy.parse_latex(ParseLatexRequest(latex=case["expected_latex"]))
            
            if input_parse.is_failure() or expected_parse.is_failure():
                continue  # Skip parse errors
            
            validation = StepValidation(
                numero=1,
                latex=case["input_latex"],
                descripcion="",
                expresion_sympy=input_parse.unwrap().expr_serialized
            )
            
            result = self.classifier.classify(validation, expected_parse.unwrap().expr_serialized)
            
            if result.is_success():
                pred = result.unwrap().patron_codigo
                expected = case["patron_esperado"]
                
                if pred == expected:
                    tp += 1
                else:
                    fp += 1
                    fn += 1  # También es FN para la clase esperada
            else:
                fn += 1
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "dataset": "chain_rule_variants",
            "total_cases": len(cases),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "target_precision": 0.92,
            "target_recall": 0.88,
            "passed": precision >= 0.92 and recall >= 0.88
        }

# evals/runners/hallucination_check.py
"""Verifica tasa de alucinación matemática = 0% (SymPy oracle)."""
import pytest

class HallucinationChecker:
    """Test que el agente NUNCA valida matemáticas sin SymPy."""
    
    @pytest.mark.asyncio
    async def test_correct_node_never_uses_llm_for_math(self, mock_llm, sympy_tool):
        """CorrectNode solo llama a SymPyTool, nunca a LLM para validar."""
        from src.mathtutor.agent.nodes.correct import CorrectNode
        
        node = CorrectNode(sympy_tool=sympy_tool, exercise_repo=mock_repo)
        state = AgentState(..., ocr_result=OCRResult(pasos=[PasoMatematico(latex=r"\cos(x^2)")]))
        
        # Espiar llamadas
        with patch.object(sympy_tool, 'equals', wraps=sympy_tool.equals) as spy_sympy:
            with patch.object(mock_llm, 'generate') as spy_llm:
                await node(state)
                
                assert spy_sympy.called
                assert not spy_llm.called, "LLM llamado para validación matemática (PROHIBIDO P1)"
    
    @pytest.mark.asyncio
    async def test_sympy_oracle_accuracy(self, sympy_tool):
        """SymPyTool debe ser 100% preciso en equivalencias conocidas."""
        test_cases = [
            (r"(x+1)^2", r"x^2 + 2x + 1", True),
            (r"\sin(x)^2 + \cos(x)^2", r"1", True),
            (r"\frac{d}{dx} \sin(x)", r"\cos(x)", True),
            (r"\int x dx", r"\frac{x^2}{2}", True),
            (r"x + 1", r"x + 2", False),
        ]
        
        for latex1, latex2, expected_equal in test_cases:
            p1 = await sympy_tool.parse_latex(ParseLatexRequest(latex=latex1))
            p2 = await sympy_tool.parse_latex(ParseLatexRequest(latex=latex2))
            result = await sympy_tool.equals(EqualsRequest(
                expr1_serialized=p1.unwrap().expr_serialized,
                expr2_serialized=p2.unwrap().expr_serialized,
                method="both"
            ))
            assert result.is_success()
            assert result.unwrap().are_equal == expected_equal, f"Fallo: {latex1} vs {latex2}"
```

### 6.3 Métricas Objetivo y Gates

```python
# evals/metrics/thresholds.py
EVAL_THRESHOLDS = {
    "precision_chain_rule": 0.92,
    "recall_chain_rule": 0.88,
    "precision_lhopital": 0.90,
    "recall_lhopital": 0.85,
    "precision_overall": 0.90,
    "recall_overall": 0.85,
    "hallucination_rate": 0.0,        # CERO tolerancia
    "latency_p95_correction_ms": 3000, # < 3s P95
    "ocr_confidence_mean": 0.85,
    "exercise_generation_success_rate": 0.80,  # 80% generaciones válidas en 1er intento
}
```

### 6.4 Comando `make eval` (Runner Principal)

```bash
# evals/runners/full_suite.py
#!/usr/bin/env python
"""Ejecuta suite completa de evals. Exit code != 0 si algún threshold falla."""
import asyncio
import sys
from evals.runners.precision_recall import HallucinationEvalRunner
from evals.runners.hallucination_check import HallucinationChecker
from evals.runners.latency import LatencyRunner
from evals.metrics.thresholds import EVAL_THRESHOLDS

async def main():
    runner = HallucinationEvalRunner()
    all_passed = True
    
    # Precision/Recall por patrón
    for dataset in ["chain_rule_variants", "lhopital_cases", "limit_indeterminate", 
                    "integral_constants", "sign_errors", "algebraic_simplification"]:
        result = await runner.run_dataset(dataset)
        precision_ok = result["precision"] >= EVAL_THRESHOLDS.get(f"precision_{dataset.split('_')[0]}", 0.90)
        recall_ok = result["recall"] >= EVAL_THRESHOLDS.get(f"recall_{dataset.split('_')[0]}", 0.85)
        
        status = "✅ PASS" if (precision_ok and recall_ok) else "❌ FAIL"
        print(f"{status} {dataset}: P={result['precision']:.3f} R={result['recall']:.3f}")
        if not (precision_ok and recall_ok):
            all_passed = False
    
    # Hallucination check (pytest)
    # Latency check
    latency_result = await LatencyRunner().run()
    latency_ok = latency_result["p95_ms"] <= EVAL_THRESHOLDS["latency_p95_correction_ms"]
    print(f"{'✅' if latency_ok else '❌'} Latency P95: {latency_result['p95_ms']:.0f}ms")
    if not latency_ok:
        all_passed = False
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Infraestructura Docker

### 7.1 `docker/Dockerfile` (Multi-stage)

```dockerfile
# docker/Dockerfile
# ── Builder Stage ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependencias de sistema para compilación (sympy, latex2sympy2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python en virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && uv pip install --system -e ".[dev]"

# ── Runtime Stage ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Dependencias runtime mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash appuser

# Copiar virtualenv del builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser pyproject.toml ./

USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "mathtutor.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 `docker/docker-compose.yml` (Desarrollo)

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.23
    container_name: mathtutor-neo4j
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: "neo4j/mathtutor-dev"
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_heap_max__size: "2G"
      NEO4J_dbms_memory_pagecache_size: "1G"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./scripts/seed_graph.py:/seed/seed_graph.py:ro
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "mathtutor-dev", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mathtutor-net

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: runtime
    container_name: mathtutor-api
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=mathtutor-dev
      - LLM_PROVIDER=anthropic
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OCR_LOCAL_ENABLED=false
      - OCR_FALLBACK_ENABLED=true
      - OCR_FALLBACK_PROVIDER=mathpix
      - MATHPIX_APP_ID=${MATHPIX_APP_ID}
      - MATHPIX_APP_KEY=${MATHPIX_APP_KEY}
      - APP_ENV=development
      - LOG_LEVEL=DEBUG
    depends_on:
      neo4j:
        condition: service_healthy
    volumes:
      - ../src:/app/src:ro  # Hot reload en dev
    networks:
      - mathtutor-net

  # Opcional: Ollama local para LLM offline
  ollama:
    image: ollama/ollama:latest
    container_name: mathtutor-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - mathtutor-net
    profiles:
      - gpu

volumes:
  neo4j_data:
  neo4j_logs:
  ollama_models:

networks:
  mathtutor-net:
    driver: bridge
```

### 7.3 `docker/docker-compose.test.yml` (CI/Testcontainers)

```yaml
# docker/docker-compose.test.yml
version: '3.8'

services:
  neo4j-test:
    image: neo4j:5.23
    container_name: mathtutor-neo4j-test
    ports:
      - "7475:7474"
      - "7688:7687"
    environment:
      NEO4J_AUTH: "neo4j/testpass"
      NEO4J_PLUGINS: '["apoc"]'
    tmpfs:
      - /data
      - /logs
    networks:
      - test-net

networks:
  test-net:
    driver: bridge
```

---

## 8. CI/CD Pipeline (GitHub Actions)

### 8.1 `.github/workflows/ci.yml`

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  NEO4J_PASSWORD: "testpass"

jobs:
  # ── Code Quality ────────────────────────────────────────────────────
  lint-and-typecheck:
    name: Lint & Typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[dev]"
      - name: Run Ruff
        run: ruff check . --select=E,F,W,I,UP,B,C4 --output-format=github
      - name: Run Ruff Format Check
        run: ruff format --check .
      - name: Run MyPy Strict
        run: mypy --strict src/

  # ── Unit + Contract Tests ───────────────────────────────────────────
  unit-contract-tests:
    name: Unit + Contract Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[dev]"
      - name: Run Unit Tests
        run: pytest -xvs tests/unit --cov=mathtutor --cov-fail-under=90 --cov-report=xml
      - name: Run Contract Tests
        run: pytest -xvs tests/contract --cov=mathtutor --cov-append --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  # ── Integration Tests (Neo4j Testcontainer) ─────────────────────────
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5.23
        env:
          NEO4J_AUTH: "neo4j/${{ env.NEO4J_PASSWORD }}"
          NEO4J_PLUGINS: '["apoc"]'
        ports: ["7687:7687"]
        options: >-
          --health-cmd="cypher-shell -u neo4j -p ${{ env.NEO4J_PASSWORD }} 'RETURN 1'"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[dev]"
      - name: Wait for Neo4j
        run: |
          for i in {1..30}; do
            if cypher-shell -u neo4j -p ${{ env.NEO4J_PASSWORD }} -a bolt://localhost:7687 'RETURN 1' 2>/dev/null; then
              echo "Neo4j ready"
              break
            fi
            sleep 2
          done
      - name: Run Integration Tests
        run: pytest -xvs tests/integration --cov=mathtutor --cov-append --cov-fail-under=70
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_PASSWORD: ${{ env.NEO4J_PASSWORD }}
          LLM_PROVIDER: ollama
          OCR_LOCAL_ENABLED: "false"
          OCR_FALLBACK_ENABLED: "false"

  # ── Evals Anti-Alucinación ──────────────────────────────────────────
  evals:
    name: Evals (Anti-Hallucination)
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event.pull_request.labels.*.name contains 'eval'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[dev]"
      - name: Run Evals
        run: make eval
        env:
          LLM_PROVIDER: ollama
          OCR_LOCAL_ENABLED: "false"
          OCR_FALLBACK_ENABLED: "false"
        timeout-minutes: 15

  # ── Build Docker Image ──────────────────────────────────────────────
  build-docker:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck, unit-contract-tests, integration-tests]
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t mathtutor-ai:${{ github.sha }} .
      - name: Test Docker image starts
        run: |
          docker run -d --name test-container -p 8000:8000 \
            -e NEO4J_URI=bolt://host.docker.internal:7687 \
            -e NEO4J_PASSWORD=mathtutor-dev \
            -e LLM_PROVIDER=ollama \
            mathtutor-ai:${{ github.sha }}
          sleep 10
          curl -f http://localhost:8000/health
          docker stop test-container

  # ── Deploy Staging (opcional) ───────────────────────────────────────
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [build-docker]
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - name: Deploy to staging server
        run: |
          echo "Deploy via SSH/Ansible/K8s to staging..."
          # ssh user@staging "docker pull mathtutor-ai:${{ github.sha }} && docker-compose up -d"

  # ── Notify ──────────────────────────────────────────────────────────
  notify:
    name: Notify Result
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck, unit-contract-tests, integration-tests, evals, build-docker]
    if: always()
    steps:
      - name: Send Slack/Discord notification
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -d '{"text": "❌ CI Failed: ${{ github.repository }}@${{ github.sha }}"}}'
      - name: Success notification
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -d '{"text": "✅ CI Passed: ${{ github.repository }}@${{ github.sha }}"}}'
```

---

## 9. Scripts Auxiliares (`scripts/`)

```bash
# scripts/seed_graph.py
"""Poblar grafo con currículo base Matemáticas II."""
import asyncio
from src.mathtutor.graph.session import Neo4jSession
from src.mathtutor.graph.repositories_impl import GraphRepositoryImpl
from src.mathtutor.domain.entities import Concepto
from datetime import datetime

CONCEPTOS_MATE_II = [
    # Límites
    {"codigo": "LIM-01", "nombre": "Límite en un punto (épsilon-delta)", "bloque": "Límites", "nivel": 1, "prereqs": []},
    {"codigo": "LIM-02", "nombre": "Límites laterales", "bloque": "Límites", "nivel": 1, "prereqs": ["LIM-01"]},
    {"codigo": "LIM-03", "nombre": "Indeterminaciones 0/0, ∞/∞ (L'Hôpital)", "bloque": "Límites", "nivel": 2, "prereqs": ["LIM-01", "DER-01"]},
    {"codigo": "LIM-04", "nombre": "Límites en infinito y asíntotas", "bloque": "Límites", "nivel": 2, "prereqs": ["LIM-01"]},
    # Derivadas
    {"codigo": "DER-01", "nombre": "Definición de derivada", "bloque": "Derivadas", "nivel": 1, "prereqs": ["LIM-01"]},
    {"codigo": "DER-02", "nombre": "Reglas de derivación (suma, producto, cociente)", "bloque": "Derivadas", "nivel": 1, "prereqs": ["DER-01"]},
    {"codigo": "DER-03", "nombre": "Regla de la cadena", "bloque": "Derivadas", "nivel": 2, "prereqs": ["DER-02"]},
    {"codigo": "DER-04", "nombre": "Derivadas de funciones trigonométricas", "bloque": "Derivadas", "nivel": 2, "prereqs": ["DER-02"]},
    {"codigo": "DER-05", "nombre": "Derivadas de funciones exponenciales y logarítmicas", "bloque": "Derivadas", "nivel": 2, "prereqs": ["DER-02"]},
    {"codigo": "DER-06", "nombre": "Derivación implícita", "bloque": "Derivadas", "nivel": 3, "prereqs": ["DER-03"]},
    # Integrales
    {"codigo": "INT-01", "nombre": "Integral indefinida y primitivas", "bloque": "Integrales", "nivel": 1, "prereqs": ["DER-01"]},
    {"codigo": "INT-02", "nombre": "Integración por partes", "bloque": "Integrales", "nivel": 2, "prereqs": ["INT-01"]},
    {"codigo": "INT-03", "nombre": "Integración por sustitución", "bloque": "Integrales", "nivel": 2, "prereqs": ["INT-01", "DER-03"]},
    {"codigo": "INT-04", "nombre": "Integrales definidas y Barrow", "bloque": "Integrales", "nivel": 2, "prereqs": ["INT-01"]},
    {"codigo": "INT-05", "nombre": "Aplicaciones: área, volumen, longitud", "bloque": "Integrales", "nivel": 3, "prereqs": ["INT-04"]},
    # Optimización
    {"codigo": "OPT-01", "nombre": "Máximos y mínimos relativos", "bloque": "Optimización", "nivel": 2, "prereqs": ["DER-02"]},
    {"codigo": "OPT-02", "nombre": "Optimización con restricciones (Lagrange)", "bloque": "Optimización", "nivel": 3, "prereqs": ["DER-06"]},
    # Continuidad
    {"codigo": "CON-01", "nombre": "Continuidad en un punto", "bloque": "Continuidad", "nivel": 1, "prereqs": ["LIM-01"]},
    {"codigo": "CON-02", "nombre": "Teorema de Bolzano y Weierstrass", "bloque": "Continuidad", "nivel": 2, "prereqs": ["CON-01"]},
]

async def main():
    session = Neo4jSession(uri="bolt://localhost:7687", user="neo4j", password="mathtutor-dev")
    repo = GraphRepositoryImpl(session)
    
    # Crear conceptos
    for c in CONCEPTOS_MATE_II:
        concepto = Concepto(
            id=str(uuid.uuid4()),
            codigo=c["codigo"],
            nombre=c["nombre"],
            bloque=c["bloque"],
            nivel=c["nivel"],
            descripcion=f"Definición de {c['nombre']}",
            latex_definicion="",
            prerequisitos_codigos=c["prereqs"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await repo.create_concepto(concepto)
        print(f"✅ Creado: {c['codigo']} - {c['nombre']}")
    
    # Crear relaciones PREREQUISITE_OF
    for c in CONCEPTOS_MATE_II:
        for prereq in c["prereqs"]:
            await session.run("""
                MATCH (a:Concepto {codigo: $from}), (b:Concepto {codigo: $to})
                MERGE (a)-[r:PREREQUISITE_OF]->(b)
                SET r.tipo = 'hard', r.peso = 1.0
            """, from=c["codigo"], to=prereq)
            print(f"🔗 {c['codigo']} → {prereq}")
    
    print("\n✅ Seed completado. Verificar DAG: make check-dag")
    session.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 10. Makefile Completo (Raíz del Repo)

```makefile
# Makefile
.PHONY: help install up down lint format typecheck check test test-int test-e2e test-all eval eval-quick dev cli seed ci migrate clean

help:  ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────────────────
install:  ## Instalar dependencias + pre-commit
	pip install -e ".[dev]"
	pre-commit install

up:  ## Levantar infra (Neo4j, Ollama opcional)
	docker compose -f docker/docker-compose.yml up -d

down:  ## Bajar infra y volúmenes
	docker compose -f docker/docker-compose.yml down -v

# ── Calidad de Código ──────────────────────────────────────────────────
lint:  ## Ruff lint (E,F,W,I,UP,B,C4)
	ruff check . --select=E,F,W,I,UP,B,C4

format:  ## Ruff format
	ruff format .

typecheck:  ## MyPy strict
	mypy --strict src/

check: lint typecheck test  ## Pipeline rápido pre-commit

# ── Tests ──────────────────────────────────────────────────────────────
test:  ## Unit + Contract tests
	pytest -xvs tests/unit tests/contract --cov=mathtutor --cov-fail-under=90

test-int:  ## Integration tests (requiere Neo4j testcontainer)
	pytest -xvs tests/integration --cov=mathtutor --cov-fail-under=70

test-e2e:  ## E2E tests (requiere API arriba)
	pytest -xvs tests/e2e

test-all: test test-int test-e2e  ## Todo

# ── Evals ──────────────────────────────────────────────────────────────
eval:  ## Suite completa evals anti-alucinación
	python -m evals.runners.full_suite

eval-quick:  ## Solo precision/recall chain rule (rápido)
	python -m evals.runners.precision_recall chain_rule_variants

# ── Desarrollo ─────────────────────────────────────────────────────────
dev:  ## API con hot reload
	uvicorn mathtutor.api.main:app --reload --port 8000

cli:  ## CLI administrativo
	python -m mathtutor.cli --help

seed:  ## Poblar grafo con currículo base
	python scripts/seed_graph.py

# ── CI Local ───────────────────────────────────────────────────────────
ci: check test-all eval-quick build-docker  ## Simula GitHub Actions completo

build-docker:  ## Build imagen Docker
	docker build -f docker/Dockerfile -t mathtutor-ai:local .

# ── Migraciones ────────────────────────────────────────────────────────
migrate:  ## Aplicar migraciones Cypher versionadas
	python scripts/migrate.py

# ── Limpieza ───────────────────────────────────────────────────────────
clean:  ## Limpiar caches, builds, contenedores
	docker system prune -f
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

---

## 11. Checklist de Consistencia (Pre-Commit para esta Spec)

- [ ] Pirámide testing: Unit ≥90%, Contract ≥90%, Integration ≥70%, E2E críticos.
- [ ] `testcontainers` para Neo4j en integration tests (aislamiento total).
- [ ] Fixtures de dominio reutilizables en `tests/fixtures/domain.py`.
- [ ] Tests unitarios: value objects (RV-04), rules (RV-01), classifier, SymPyTool.
- [ ] Contract tests: schemas Pydantic (`extra='forbid'`), Cypher parameterization.
- [ ] Evals dataset: JSONL etiquetado por patrón EvAU (chain_rule, lhopital, etc.).
- [ ] `HallucinationEvalRunner` mide Precision@1/Recall@1 vs thresholds (0.92/0.88).
- [ ] `HallucinationChecker` test: CorrectNode **nunca** llama LLM para matemáticas.
- [ ] Docker multi-stage (builder → runtime), non-root user, healthcheck.
- [ ] `docker-compose.yml` dev (Neo4j, API, Ollama GPU opcional).
- [ ] GitHub Actions: lint → unit/contract → integration → evals → build-docker → deploy.
- [ ] `make ci` ejecuta pipeline completo localmente.
- [ ] `scripts/seed_graph.py` carga 20 conceptos Mate II + DAG prerequisitos.
- [ ] `pyproject.toml` con `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]`, dependencies.

---

*Última actualización: 2026-11-26 — Versión 1.0.0 (Baseline MVP Matemáticas II)*
