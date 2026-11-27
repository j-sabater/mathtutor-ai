"""Reglas de validación de dominio (funciones puras, sin I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result, Success, Failure
import sympy as sp

from mathtutor.domain.entities import Concepto
from mathtutor.domain.value_objects import PasoMatematico


# ── Error Types ──────────────────────────────────────────────────────────

class DomainRuleError(BaseModel):
    """Error base para reglas de dominio."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    message: str
    context: dict = Field(default_factory=dict)


class CycleError(DomainRuleError):
    code: str = "CYCLE_DETECTED"
    message: str = "Ciclo detectado en grafo de prerrequisitos"


class WeightError(DomainRuleError):
    code: str = "WEIGHT_SUM_INVALID"
    message: str = "Suma de pesos :TESTS debe ser 1.0"


class BoundError(DomainRuleError):
    code: str = "BOUND_VIOLATION"
    message: str = "Valor fuera de rango permitido"


class ParseError(DomainRuleError):
    code: str = "LATEX_PARSE_ERROR"
    message: str = "LaTeX no parseable por SymPy"


class ConfidenceError(DomainRuleError):
    code: str = "LOW_CONFIDENCE"
    message: str = "Confianza OCR por debajo del umbral"


class SequenceError(DomainRuleError):
    code: str = "INVALID_SEQUENCE"
    message: str = "Secuencia de pasos inválida"


# ── Rule Functions ───────────────────────────────────────────────────────

def validate_prerequisite_dag(conceptos: list[Concepto]) -> Result[None, CycleError]:
    """
    RV-01: Verifica que :PREREQUISITE_OF no introduce ciclos (Kahn's algorithm).
    """
    # Construir grafo de adyacencia
    codigo_to_idx = {c.codigo: i for i, c in enumerate(conceptos)}
    n = len(conceptos)
    adj: list[list[int]] = [[] for _ in range(n)]
    indegree = [0] * n

    for concepto in conceptos:
        u = codigo_to_idx[concepto.codigo]
        for prereq_codigo in concepto.prerequisitos_codigos:
            if prereq_codigo in codigo_to_idx:
                v = codigo_to_idx[prereq_codigo]
                adj[v].append(u)  # prereq -> concepto
                indegree[u] += 1

    # Kahn's algorithm
    queue = [i for i in range(n) if indegree[i] == 0]
    visited = 0

    while queue:
        u = queue.pop(0)
        visited += 1
        for v in adj[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    if visited != n:
        # Encontrar ciclo para contexto
        return Failure(CycleError(context={"conceptos_count": n, "visited": visited}))

    return Success(None)


def validate_test_weights_sum(
    ejercicio_id: str,
    tests: list[tuple[str, float, bool]]  # (concepto_codigo, peso, es_principal)
) -> Result[None, WeightError]:
    """
    RV-02: Suma de pesos en :TESTS salientes = 1.0 ± 0.001.
    """
    total = sum(peso for _, peso, _ in tests)
    if abs(total - 1.0) > 0.001:
        return Failure(WeightError(
            context={"ejercicio_id": ejercicio_id, "suma_pesos": total, "tests": tests}
        ))
    return Success(None)


def validate_mastery_bounds(nivel: float) -> Result[None, BoundError]:
    """
    RV-03: MasteryLevel.nivel siempre en [0.0, 1.0].
    """
    if not 0.0 <= nivel <= 1.0:
        return Failure(BoundError(context={"nivel": nivel, "min": 0.0, "max": 1.0}))
    return Success(None)


def validate_latex_parseable(latex: str) -> Result[sp.Expr, ParseError]:
    """
    RV-04: latex2sympy2.latex2sympy(latex) no lanza excepción.
    """
    try:
        import latex2sympy2 as l2s
        expr = l2s.latex2sympy(latex)
        return Success(expr)
    except Exception as e:
        return Failure(ParseError(context={"latex": latex, "error": str(e)}))


def validate_ocr_confidence(confidence: float, threshold: float = 0.7) -> Result[None, ConfidenceError]:
    """
    RV-05: confidence >= threshold para auto-aceptar.
    """
    if confidence < threshold:
        return Failure(ConfidenceError(context={"confidence": confidence, "threshold": threshold}))
    return Success(None)


def validate_paso_sequencial(pasos: list[PasoMatematico]) -> Result[None, SequenceError]:
    """
    RV-06: Pasos numerados 1..N sin saltos, cada paso tiene LaTeX no vacío.
    """
    if not pasos:
        return Failure(SequenceError(context={"error": "Lista de pasos vacía"}))

    expected = 1
    for paso in pasos:
        if paso.numero != expected:
            return Failure(SequenceError(context={
                "expected": expected,
                "got": paso.numero,
                "paso": paso.model_dump(),
            }))
        if not paso.latex or not paso.latex.strip():
            return Failure(SequenceError(context={"error": "LaTeX vacío", "paso": paso.numero}))
        expected += 1

    return Success(None)


# ── Additional Validation Helpers ────────────────────────────────────────

def validate_concepto_codigo_format(codigo: str) -> Result[None, DomainRuleError]:
    """Valida formato BLOQUE-NN (ej. DER-03)."""
    import re
    if not re.match(r"^[A-Z]{3}-\d{2}$", codigo):
        return Failure(DomainRuleError(
            code="INVALID_CODIGO_FORMAT",
            message=f"Código '{codigo}' no sigue patrón BLOQUE-NN",
            context={"codigo": codigo},
        ))
    return Success(None)


def validate_patron_codigo_format(codigo: str) -> Result[None, DomainRuleError]:
    """Valida formato ERR-XXX-XXX."""
    import re
    if not re.match(r"^ERR-[A-Z0-9-]+$", codigo):
        return Failure(DomainRuleError(
            code="INVALID_PATRON_CODIGO",
            message=f"Código de patrón '{codigo}' inválido",
            context={"codigo": codigo},
        ))
    return Success(None)


def validate_dificultad_range(dificultad: int) -> Result[None, BoundError]:
    """Valida dificultad 1..5."""
    if not 1 <= dificultad <= 5:
        return Failure(BoundError(context={"dificultad": dificultad, "min": 1, "max": 5}))
    return Success(None)


def validate_nivel_range(nivel: int) -> Result[None, BoundError]:
    """Valida nivel 1..3."""
    if not 1 <= nivel <= 3:
        return Failure(BoundError(context={"nivel": nivel, "min": 1, "max": 3}))
    return Success(None)
