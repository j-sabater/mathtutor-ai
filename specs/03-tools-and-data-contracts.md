# specs/03-tools-and-data-contracts.md — Contratos de Datos, Herramientas y Capa Agnóstica LLM

> **Single Source of Truth** para todos los contratos de entrada/salida (Pydantic v2), firmas de herramientas deterministas, interfaces de proveedores y parsers.
> **Versión**: 1.0.0 — Baseline MVP (Matemáticas II: Cálculo)

---

## 1. Principios de Contratos

| Principio | Regla |
|-----------|-------|
| **Schema-First** | Todo contrato (API, Tool, Evento, Graph DTO) es `BaseModel` con `model_config = ConfigDict(extra='forbid', frozen=True)`. |
| **Validación en Frontera** | Parsing + validación ocurren **una sola vez** en la capa de entrada (API/Ingest/Tool). Interior del sistema usa objetos tipados. |
| **Versionado Explícito** | Schemas versionados en `schemas/v1/`, `schemas/v2/`. Migración via adapters. |
| **Tipos Compartidos** | Value Objects de `domain/value_objects.py` reutilizados en API, Tools, Events, Graph mappers. |
| **Documentación Viva** | Docstrings Google-style en cada modelo + ejemplos JSON en `model_config.json_schema_extra`. |

---

## 2. Esquemas Pydantic v2 (API Contracts)

### 2.1 Request/Response Schemas (`src/mathtutor/api/schemas/v1/`)

#### 2.1.1 Ingesta de Intento
```python
# src/mathtutor/api/schemas/v1/ingest.py
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Annotated, Literal
import uuid

class IngestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    ejercicio_id: Annotated[str, Field(min_length=1)]
    alumna_id: str = "alumna_principal"
    imagenes: Annotated[list[HttpUrl], Field(min_length=1, max_length=5)]

class IngestResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    trace_id: str
    intento_id: str
    estado: Literal["pendiente_revision", "error_ocr"]
    latex_extraido: str
    pasos_detectados: int
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    strategy_used: str
    fallback_used: bool
    requiere_revision: bool  # True si confidence < 0.7
```

#### 2.1.2 Revisión OCR (Human-in-the-loop)
```python
# src/mathtutor/api/schemas/v1/review.py
class OCRReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    action: Literal["approve", "correct"]
    corrected_latex: str | None = None  # Requerido si action="correct"

class OCRReviewResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    status: Literal["accepted", "rejected", "correction_invalid"]
    trace_id: str
    mensaje: str
```

#### 2.1.3 Corrección y Resultado
```python
# src/mathtutor/api/schemas/v1/correction.py
from src.mathtutor.domain.value_objects import PasoMatematico, PatronErrorRef, MasterySnapshot

class StepFeedback(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    paso: int
    latex_original: str
    latex_normalizado: str
    es_correcto: bool
    feedback: str
    sugerencia: str | None
    patron_error_codigo: str | None

class CorrectionResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    trace_id: str
    intento_id: str
    puntuacion: Annotated[float, Field(ge=0.0, le=10.0)]
    pasos_feedback: list[StepFeedback]
    errores_detectados: list[PatronErrorRef]
    mastery_actualizado: list[MasterySnapshot]
    ejercicio_recomendado_id: str | None
    apunte_generado_url: str | None
    duracion_ms: int
```

#### 2.1.4 Consulta de Progreso (Dashboard)
```python
# src/mathtutor/api/schemas/v1/progress.py
class ConceptoProgress(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    codigo: str
    nombre: str
    bloque: str
    mastery: Annotated[float, Field(ge=0.0, le=1.0)]
    nivel: Literal["básico", "intermedio", "avanzado"]
    aciertos_consecutivos: int
    intentos_totales: int
    prerequisitos_faltantes: list[str]

class PatronErrorFrequency(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    codigo: str
    nombre: str
    severidad: int
    frecuencia_30d: int
    ultima_ocurrencia: str  # ISO datetime

class ProgressResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    alumna_id: str
    conceptos: list[ConceptoProgress]
    patrones_error_top: list[PatronErrorFrequency]
    racha_actual: int
    siguiente_recomendacion: dict | None  # {ejercicio_id, concepto, razon}
```

#### 2.1.5 Generación de Apunte (Admin/Async)
```python
# src/mathtutor/api/schemas/v1/notes.py
class GenerateNoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    alumna_id: str = "alumna_principal"
    conceptos_codigos: Annotated[list[str], Field(min_length=1)]
    patrones_objetivo: list[str] = []  # Códigos PatronDeError a abordar

class NoteResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    note_id: str
    url_pdf: str
    conceptos_cubiertos: list[str]
    patrones_abordados: list[str]
    generated_at: str
```

---

## 3. Esquemas de Herramientas (Tool Contracts)

> Contratos estrictos para `SymPyTool`, `OCRStrategy`, `GraphRepository`, `ErrorClassifierEngine`.
> Ubicación: `src/mathtutor/agent/tools/schemas.py`

### 3.1 `SymPyTool` — Oráculo Matemático Determinista

```python
# src/mathtutor/agent/tools/schemas.py
from returns.result import Result, Success, Failure
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Literal
import sympy as sp

# ── Tipos de Error SymPy ──────────────────────────────────────────────
class SymPyError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: Literal[
        "PARSE_ERROR", "SIMPLIFY_ERROR", "EQUALS_ERROR", 
        "DIFF_ERROR", "INTEGRATE_ERROR", "LIMIT_ERROR", 
        "SOLVE_ERROR", "NSIMPLIFY_ERROR", "TIMEOUT"
    ]
    message: str
    latex_input: str | None = None
    details: dict = {}

# ── Contratos de Operaciones Atómicas ─────────────────────────────────
class ParseLatexRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    latex: Annotated[str, Field(min_length=1)]
    variables: dict[str, sp.Symbol] = {}  # Símbolos predefinidos (x, y, t...)

class ParseLatexResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_repr: str  # repr(expr) para logging/debug
    expr_serialized: str  # JSON-serializable (sympy.srepr o custom)
    free_symbols: list[str]

class SimplifyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    target_form: Literal["expanded", "factored", "cancelled", "auto"] = "auto"

class EqualsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr1_serialized: str
    expr2_serialized: str
    method: Literal["symbolic", "numeric", "both"] = "symbolic"
    numeric_samples: int = 10  # Para validación numérica

class EqualsResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    are_equal: bool
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    method_used: str
    difference_simplified: str | None = None

class DiffRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    variable: str
    order: Annotated[int, Field(ge=1, le=3)] = 1

class IntegrateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    variable: str
    limits: tuple[str | float | None, str | float | None] | None = None  # (lower, upper) o None para indefinida

class LimitRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    variable: str
    point: str | float  # "0", "oo", "-oo", "pi/2", etc.
    dir: Literal["+", "-", "+-"] = "+-"

class SolveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    variable: str
    domain: Literal["real", "complex", "integer"] = "real"

class NsimplifyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    expr_serialized: str
    tolerance: float = 1e-10
    rational: bool = True
    radicals: bool = True
```

### 3.2 Protocolo `SymPyTool` (Interface)

```python
# src/mathtutor/agent/tools/protocols.py
from typing import Protocol
from returns.result import Result
from .schemas import (
    ParseLatexRequest, ParseLatexResponse, SymPyError,
    SimplifyRequest, EqualsRequest, EqualsResponse,
    DiffRequest, IntegrateRequest, LimitRequest, SolveRequest, NsimplifyRequest
)

class SymPyToolProtocol(Protocol):
    """Interfaz del oráculo matemático. Implementación usa latex2sympy2 + SymPy."""
    
    async def parse_latex(self, req: ParseLatexRequest) -> Result[ParseLatexResponse, SymPyError]: ...
    
    async def simplify(self, req: SimplifyRequest) -> Result[ParseLatexResponse, SymPyError]: ...
    
    async def equals(self, req: EqualsRequest) -> Result[EqualsResponse, SymPyError]: ...
    
    async def diff(self, req: DiffRequest) -> Result[ParseLatexResponse, SymPyError]: ...
    
    async def integrate(self, req: IntegrateRequest) -> Result[ParseLatexResponse, SymPyError]: ...
    
    async def limit(self, req: LimitRequest) -> Result[ParseLatexResponse, SymPyError]: ...
    
    async def solve(self, req: SolveRequest) -> Result[list[ParseLatexResponse], SymPyError]: ...
    
    async def nsimplify(self, req: NsimplifyRequest) -> Result[ParseLatexResponse, SymPyError]: ...
```

### 3.3 Implementación `Latex2SymPyTool` (Wrapper `latex2sympy2`)

```python
# src/mathtutor/agent/tools/sympy_tool.py
import latex2sympy2 as l2s
import sympy as sp
from returns.result import Result, Success, Failure
from .protocols import SymPyToolProtocol
from .schemas import *

class Latex2SymPyTool(SymPyToolProtocol):
    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout = timeout_seconds
        self._parser = l2s.Latex2Sympy()
    
    def _to_sympy(self, serialized: str) -> sp.Expr:
        return sp.sympify(serialized)  # O custom deserializer
    
    def _serialize(self, expr: sp.Expr) -> str:
        return sp.srepr(expr)  # Serialización canónica lossless
    
    async def parse_latex(self, req: ParseLatexRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            # Preprocesamiento LaTeX OCR común
            latex_clean = self._preprocess_latex(req.latex)
            expr = self._parser.latex2sympy(latex_clean)
            
            # Aplicar símbolos predefinidos
            for name, sym in req.variables.items():
                expr = expr.xreplace({sp.Symbol(name): sym})
            
            return Success(ParseLatexResponse(
                expr_repr=repr(expr),
                expr_serialized=self._serialize(expr),
                free_symbols=[str(s) for s in expr.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(
                code="PARSE_ERROR",
                message=str(e),
                latex_input=req.latex
            ))
    
    async def equals(self, req: EqualsRequest) -> Result[EqualsResponse, SymPyError]:
        try:
            e1 = self._to_sympy(req.expr1_serialized)
            e2 = self._to_sympy(req.expr2_serialized)
            
            if req.method in ("symbolic", "both"):
                diff = sp.simplify(e1 - e2)
                symbolic_equal = diff == 0
            else:
                symbolic_equal = False
            
            if req.method in ("numeric", "both"):
                # Muestreo numérico en dominio real
                vars = list(e1.free_symbols | e2.free_symbols)
                numeric_equal = True
                for _ in range(req.numeric_samples):
                    subs = {v: sp.nsimplify(sp.randprime(-10, 10)) for v in vars}
                    try:
                        v1 = complex(e1.subs(subs).evalf())
                        v2 = complex(e2.subs(subs).evalf())
                        if abs(v1 - v2) > 1e-10:
                            numeric_equal = False
                            break
                    except Exception:
                        numeric_equal = False
                        break
            else:
                numeric_equal = True
            
            are_equal = symbolic_equal and numeric_equal
            confidence = 1.0 if symbolic_equal else (0.9 if numeric_equal else 0.0)
            
            return Success(EqualsResponse(
                are_equal=are_equal,
                confidence=confidence,
                method_used=req.method,
                difference_simplified=self._serialize(sp.simplify(e1 - e2)) if not are_equal else None
            ))
        except Exception as e:
            return Failure(SymPyError(code="EQUALS_ERROR", message=str(e)))
    
    # ... diff, integrate, limit, solve, nsimplify análogos ...
    
    def _preprocess_latex(self, latex: str) -> str:
        """Normalización robusta para LaTeX de OCR manuscrito."""
        replacements = {
            r'\\times': '*', r'\\cdot': '*', r'\\div': '/',
            r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}': r'(\1)/(\2)',  # Simplificado
            r'\\sqrt\s*\{([^}]+)\}': r'sqrt(\1)',
            r'\\lim_\s*\{([^}]+)\}\s*': r'limit(\1, ',  # Requiere parsing contextual
            r'\\int': 'integrate',
            r'\\sum': 'sum',
            r'\\infty': 'oo',
            r'\\pi': 'pi',
            r'\\e': 'E',
        }
        import re
        for pattern, repl in replacements.items():
            latex = re.sub(pattern, repl, latex)
        return latex
```

---

### 3.4 `OCRStrategy` — Interface Pipeline Híbrido

```python
# src/mathtutor/ingestion/strategies/protocol.py
from typing import Protocol
from returns.result import Result
from pydantic import BaseModel, ConfigDict

class OCRRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    images: list[bytes]  # Bytes de imagen/PDF
    context: dict = {}   # tipo_ejercicio, conceptos_esperados, etc.

class OCRResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    latex_raw: str
    confidence: float
    strategy_name: str
    metadata: dict = {}

class OCRError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: str
    message: str
    strategy: str
    recoverable: bool

class OCRStrategy(Protocol):
    """Estrategia de OCR (Local o API). Strategy Pattern."""
    
    @property
    def name(self) -> str: ...
    
    @property
    def requires_gpu(self) -> bool: ...
    
    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]: ...
```

### 3.5 Implementaciones Concretas

```python
# src/mathtutor/ingestion/strategies/local_pix2text.py
class Pix2TextStrategy(OCRStrategy):
    name = "pix2text"
    requires_gpu = True
    
    def __init__(self, model_path: str, device: str = "cuda"):
        from pix2text import Pix2Text
        self.model = Pix2Text(model_path=model_path, device=device)
    
    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]:
        try:
            # Pix2Text espera rutas de archivo
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                paths = []
                for i, img_bytes in enumerate(request.images):
                    path = f"{tmpdir}/img_{i}.png"
                    with open(path, "wb") as f:
                        f.write(img_bytes)
                    paths.append(path)
                
                results = self.model.recognize(paths)
                latex = "\n".join(r["text"] for r in results)
                confidence = sum(r.get("confidence", 0.9) for r in results) / len(results)
            
            return Success(OCRResponse(
                latex_raw=latex,
                confidence=confidence,
                strategy_name=self.name,
                metadata={"pages": len(request.images)}
            ))
        except Exception as e:
            return Failure(OCRError(
                code="LOCAL_OCR_FAILED",
                message=str(e),
                strategy=self.name,
                recoverable=True  # Trigger fallback
            ))

# src/mathtutor/ingestion/strategies/api_mathpix.py
class MathpixStrategy(OCRStrategy):
    name = "mathpix"
    requires_gpu = False
    
    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]:
        try:
            # Subir imágenes a Mathpix
            files = [("file", (f"img_{i}.png", img, "image/png")) 
                     for i, img in enumerate(request.images)]
            
            resp = await self.client.post(
                "https://api.mathpix.com/v3/latex",
                files=files,
                headers={"app_id": self.app_id, "app_key": self.app_key},
                data={"options_json": '{"math_inline_delimiters": ["$", "$"]}'}
            )
            resp.raise_for_status()
            data = resp.json()
            
            return Success(OCRResponse(
                latex_raw=data.get("latex", ""),
                confidence=data.get("confidence", 0.95),
                strategy_name=self.name,
                metadata={"mathpix_id": data.get("latex_id")}
            ))
        except httpx.HTTPStatusError as e:
            return Failure(OCRError(
                code="API_OCR_FAILED",
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                strategy=self.name,
                recoverable=False
            ))
```

### 3.6 `OCRPipeline` — Orquestador Híbrido (Local → Fallback API)

```python
# src/mathtutor/ingestion/pipeline.py
class OCRPipeline:
    def __init__(
        self, 
        local_strategy: OCRStrategy | None,
        fallback_strategy: OCRStrategy | None,
        confidence_threshold: float = 0.7
    ):
        self.local = local_strategy
        self.fallback = fallback_strategy
        self.threshold = confidence_threshold
    
    async def process(self, images: list[bytes], context: dict) -> OCRResult:
        request = OCRRequest(images=images, context=context)
        
        # 1. Intentar local si disponible
        if self.local:
            result = await self.local.process(request)
            if result.is_success():
                resp = result.unwrap()
                if resp.confidence >= self.threshold:
                    return OCRResult(
                        latex_raw=resp.latex_raw,
                        strategy=resp.strategy_name,
                        confidence=resp.confidence,
                        fallback_used=False,
                        paths=[]
                    )
                # Confianza baja → log y continuar a fallback
                logger.warning("low_confidence_local_ocr", 
                              strategy=resp.strategy_name, 
                              confidence=resp.confidence)
        
        # 2. Fallback API
        if self.fallback:
            result = await self.fallback.process(request)
            if result.is_success():
                resp = result.unwrap()
                return OCRResult(
                    latex_raw=resp.latex_raw,
                    strategy=resp.strategy_name,
                    confidence=resp.confidence,
                    fallback_used=True,
                    paths=[]
                )
        
        # 3. Fallo total
        raise OCRPipelineError("Todas las estrategias OCR fallaron")
```

---

## 4. Capa Agnóstica LLM (`LLMProtocol` + `ToolCallingLLM`)

### 4.1 Protocolos Base

```python
# src/mathtutor/llm/protocol.py
from typing import Protocol, AsyncIterator
from pydantic import BaseModel, ConfigDict
from returns.result import Result

class LLMRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None
    stop_sequences: list[str] = []

class LLMResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    text: str
    usage: dict = {}  # input_tokens, output_tokens, total_tokens
    model: str
    provider: str

class LLMError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: str
    message: str
    provider: str
    recoverable: bool

class LLMProtocol(Protocol):
    """Capa base: solo generación de texto (sin tool-calling)."""
    
    @property
    def provider_name(self) -> str: ...
    
    @property
    def model_name(self) -> str: ...
    
    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]: ...
    
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...

class ToolCallingLLM(LLMProtocol, Protocol):
    """Extensión para proveedores con tool-calling (Claude, GPT-4o, etc.)."""
    
    class Tool(BaseModel):
        model_config = ConfigDict(extra='forbid', frozen=True)
        name: str
        description: str
        parameters: dict  # JSON Schema
    
    async def chat_with_tools(
        self,
        messages: list[dict],  # [{"role": "user", "content": "..."}]
        tools: list[Tool],
        tool_choice: Literal["auto", "required", "none"] = "auto",
        response_format: dict | None = None  # {"type": "json_object"} o schema
    ) -> Result[LLMResponse, LLMError]: ...
```

### 4.2 Adapters Concretos

```python
# src/mathtutor/llm/adapters/anthropic_adapter.py
import anthropic
from ..protocol import LLMProtocol, ToolCallingLLM, LLMRequest, LLMResponse, LLMError, LLMProtocol
from returns.result import Result, Success, Failure

class AnthropicAdapter(ToolCallingLLM):
    provider_name = "anthropic"
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model_name = model
    
    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]:
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            
            resp = await self.client.messages.create(
                model=self.model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 4096,
                stop_sequences=request.stop_sequences or None
            )
            
            return Success(LLMResponse(
                text=resp.content[0].text,
                usage={"input_tokens": resp.usage.input_tokens, 
                       "output_tokens": resp.usage.output_tokens},
                model=self.model_name,
                provider=self.provider_name
            ))
        except anthropic.APIError as e:
            return Failure(LLMError(
                code="ANTHROPIC_API_ERROR",
                message=str(e),
                provider=self.provider_name,
                recoverable=e.status_code in (429, 500, 503)
            ))
    
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        # Implementación streaming...
        pass
    
    async def chat_with_tools(self, messages, tools, tool_choice, response_format):
        # Conversión tools → anthropic format
        # response_format → tools si structured output
        pass

# src/mathtutor/llm/adapters/ollama_adapter.py
class OllamaAdapter(LLMProtocol):  # NO implementa ToolCallingLLM
    provider_name = "ollama"
    
    def __init__(self, base_url: str, model: str = "llama3.1:70b"):
        self.base_url = base_url
        self.model_name = model
        self.client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
    
    async def generate(self, request: LLMRequest) -> Result[LLMResponse, LLMError]:
        # Ollama /api/generate
        pass
    
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        # Ollama /api/generate con stream=true
        pass
```

### 4.3 Factory y Configuración

```python
# src/mathtutor/llm/factory.py
from ..protocol import LLMProtocol, ToolCallingLLM
from ..adapters.anthropic_adapter import AnthropicAdapter
from ..adapters.openai_adapter import OpenAIAdapter
from ..adapters.ollama_adapter import OllamaAdapter
from returns.result import Result, Success, Failure

class LLMFactory:
    @staticmethod
    def create(provider: str, **kwargs) -> Result[LLMProtocol, LLMError]:
        if provider == "anthropic":
            return Success(AnthropicAdapter(
                api_key=kwargs["api_key"],
                model=kwargs.get("model", "claude-3-5-sonnet-20241022")
            ))
        elif provider == "openai":
            return Success(OpenAIAdapter(
                api_key=kwargs["api_key"],
                model=kwargs.get("model", "gpt-4o-2024-08-06")
            ))
        elif provider == "ollama":
            return Success(OllamaAdapter(
                base_url=kwargs.get("base_url", "http://localhost:11434"),
                model=kwargs.get("model", "llama3.1:70b")
            ))
        else:
            return Failure(LLMError(
                code="UNKNOWN_PROVIDER",
                message=f"Proveedor no soportado: {provider}",
                provider="factory",
                recoverable=False
            ))
```

---

## 5. `GraphRepository` Interface (Domain-Driven)

```python
# src/mathtutor/graph/repositories.py
from typing import Protocol
from returns.result import Result
from pydantic import BaseModel, ConfigDict
from src.mathtutor.domain.entities import Concepto, Ejercicio, Intento, PatronDeError, User

class GraphError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: str
    message: str
    operation: str

# ── DTOs para Repositorio (separados de entidades de dominio) ─────────
class EjercicioWithConceptos(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    ejercicio: Ejercicio
    tests: list[TestRelation]  # {concepto: Concepto, peso: float, es_principal: bool}

class StudentProfile(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    alumna_id: str
    mastery: dict[str, float]  # concepto_codigo -> nivel
    errores_recientes: list[PatronErrorRef]
    racha_aciertos: int
    prerequisitos_faltantes: dict[str, list[str]]  # concepto -> [prereq_codigos]

class GraphRepository(Protocol):
    """Interface pura. Implementación en graph/repositories_impl.py con Cypher."""
    
    # Conceptos
    async def get_concepto_by_codigo(self, codigo: str) -> Result[Concepto, GraphError]: ...
    async def get_all_conceptos(self) -> Result[list[Concepto], GraphError]: ...
    async def create_concepto(self, concepto: Concepto) -> Result[Concepto, GraphError]: ...
    
    # Ejercicios
    async def get_ejercicio_by_id(self, id: str) -> Result[Ejercicio, GraphError]: ...
    async def get_ejercicio_with_conceptos(self, id: str) -> Result[EjercicioWithConceptos, GraphError]: ...
    async def create_exercise(self, enunciado: str, tipo: str, dificultad: int, 
                              fuente: str, conceptos: list[str]) -> Result[str, GraphError]: ...
    
    # Intentos
    async def create_intento(self, ejercicio_id: str, alumna_id: str, 
                             latex_final: str, pasos: list, puntuacion: float, estado: str) -> Result[str, GraphError]: ...
    async def get_intento_by_id(self, id: str) -> Result[Intento, GraphError]: ...
    
    # Patrones de Error
    async def get_patron_by_codigo(self, codigo: str) -> Result[PatronDeError, GraphError]: ...
    async def create_patron(self, codigo: str, nombre: str, concepto_codigo: str) -> Result[PatronDeError, GraphError]: ...
    async def link_intento_error(self, intento_id: str, patron_codigo: str, paso: int, confianza: float) -> Result[None, GraphError]: ...
    
    # Mastery
    async def update_mastery_ewma(self, alumna_id: str, concepto_codigo: str, score: float) -> Result[float, GraphError]: ...
    async def get_mastery(self, alumna_id: str, concepto_codigo: str) -> Result[float | None, GraphError]: ...
    
    # Recomendaciones / Perfil
    async def get_student_profile(self, alumna_id: str) -> Result[StudentProfile, GraphError]: ...
    async def generate_recommendations(self, alumna_id: str, limit: int) -> Result[list[Ejercicio], GraphError]: ...
    async def link_recommendation(self, concepto_codigo: str, ejercicio_id: str, razon: str, prioridad: int) -> Result[None, GraphError]: ...
```

---

## 6. `ErrorClassifierEngine` Contrato (Motor Determinista)

```python
# src/mathtutor/agent/tools/error_classifier.py
from typing import Protocol
from returns.result import Result
from src.mathtutor.domain.value_objects import StepValidation, ErrorClassification
import sympy as sp

class ClassificationError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    code: str
    message: str

class ErrorClassifierEngine(Protocol):
    """Motor de reglas puro. Sin I/O, sin LLM. 100% testeable."""
    
    def classify(self, validation: StepValidation, expected_expr: sp.Expr) -> Result[ErrorClassification, ClassificationError]: ...
    
    def register_rule(self, condition: callable, patron_codigo: str, priority: int = 0) -> None: ...
    
    def get_all_patterns(self) -> list[str]: ...
```

**Implementación**: Lista ordenada de `(callable, patron_codigo)` evaluada secuencialmente (ver specs/02 sección 3.4).

---

## 7. Eventos de Dominio (Serialización JSON)

```python
# src/mathtutor/domain/events.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Literal, Annotated
import uuid

class DomainEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str
    payload: dict

# Eventos concretos (ejemplos)
class IntentoCreado(DomainEvent):
    event_type = "IntentoCreado"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "ejercicio_id": "str",
        "alumna_id": "str",
        "estado": "str"
    })]

class IntentoCorregido(DomainEvent):
    event_type = "IntentoCorregido"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "puntuacion": "float",
        "errores": "list[PatronErrorRef]",
        "duracion_ms": "int"
    })]

class MasteryActualizado(DomainEvent):
    event_type = "MasteryActualizado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "concepto_codigo": "str",
        "nivel_anterior": "float",
        "nivel_nuevo": "float",
        "delta": "float"
    })]

class PatronErrorDetectado(DomainEvent):
    event_type = "PatronErrorDetectado"
    payload: Annotated[dict, Field(..., description={
        "intento_id": "str",
        "patron_codigo": "str",
        "paso": "int",
        "confianza": "float",
        "nueva_instancia": "bool"
    })]

class EjercicioRecomendado(DomainEvent):
    event_type = "EjercicioRecomendado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "ejercicio_id": "str",
        "concepto_objetivo": "str",
        "razon": "str",
        "prioridad": "int"
    })]

class ApunteGenerado(DomainEvent):
    event_type = "ApunteGenerado"
    payload: Annotated[dict, Field(..., description={
        "alumna_id": "str",
        "conceptos_cubiertos": "list[str]",
        "patrones_abordados": "list[str]",
        "url_pdf": "str"
    })]
```

---

## 8. Configuración Tipada (Pydantic Settings)

```python
# src/mathtutor/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "mathtutor-dev"
    neo4j_database: str = "neo4j"
    
    # LLM
    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-2024-08-06"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:70b"
    
    # OCR
    ocr_local_enabled: bool = True
    ocr_local_model: Literal["pix2text", "nougat", "surya"] = "pix2text"
    ocr_local_device: Literal["cuda", "cpu"] = "cuda"
    ocr_fallback_enabled: bool = True
    ocr_fallback_provider: Literal["mathpix", "anthropic", "openai"] = "mathpix"
    mathpix_app_id: str = ""
    mathpix_app_key: str = ""
    
    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    secret_key: str = "dev-secret-change-in-prod"
    
    # SymPy
    sympy_timeout_seconds: float = 10.0
    
    # LangGraph
    langgraph_checkpoint_path: str = "sqlite:///checkpoints.db"

settings = Settings()
```

---

## 9. Excepciones de Dominio (Error Types)

```python
# src/mathtutor/core/exceptions.py
class MathTutorError(Exception):
    """Base exception con código y contexto estructurado."""
    def __init__(self, code: str, message: str, context: dict | None = None):
        self.code = code
        self.context = context or {}
        super().__init__(message)

class OCRPipelineError(MathTutorError): pass
class SymPyValidationError(MathTutorError): pass
class GraphTransactionError(MathTutorError): pass
class LLMProviderError(MathTutorError): pass
class ValidationError(MathTutorError): pass
class NotFoundError(MathTutorError): pass
class ConfigurationError(MathTutorError): pass
```

---

## 10. Checklist de Consistencia (Pre-Commit para esta Spec)

- [ ] Todos los modelos Pydantic usan `ConfigDict(extra='forbid', frozen=True)`.
- [ ] `SymPyToolProtocol` expone **solo** 8 operaciones atómicas + tipos `Result[..., SymPyError]`.
- [ ] `latex2sympy2` wrapper incluye `_preprocess_latex` para normalización OCR.
- [ ] `OCRStrategy` protocol + `Pix2TextStrategy` + `MathpixStrategy` + `OCRPipeline` orquestador híbrido.
- [ ] `LLMProtocol` (base) + `ToolCallingLLM` (extendido) → `AnthropicAdapter`, `OpenAIAdapter`, `OllamaAdapter`.
- [ ] `LLMFactory` crea proveedor por config, devuelve `Result[LLMProtocol, LLMError]`.
- [ ] `GraphRepository` protocol separa DTOs de entidades de dominio.
- [ ] `ErrorClassifierEngine` protocol puro (sin I/O, sin LLM).
- [ ] Eventos `DomainEvent` con `event_id`, `trace_id`, `timestamp`, `payload` tipado.
- [ ] `Settings` (Pydantic Settings) centraliza toda config con validación.
- [ ] Excepciones heredan de `MathTutorError(code, message, context)`.

---

*Última actualización: 2026-11-26 — Versión 1.0.0 (Baseline MVP Matemáticas II)*
