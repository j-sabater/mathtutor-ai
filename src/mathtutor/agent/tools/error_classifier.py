"""Motor de clasificación de errores determinista (reglas puras, sin LLM)."""

from __future__ import annotations

from typing import Protocol, Callable
from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result, Success, Failure
import sympy as sp

from mathtutor.domain.value_objects import StepValidation, ErrorClassification


class ClassificationError(BaseModel):
    """Error en clasificación de errores."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    message: str


class ErrorClassifierEngine(Protocol):
    """Motor de reglas puro para clasificar errores matemáticos."""

    def classify(self, validation: StepValidation, expected_expr: sp.Expr) -> Result[ErrorClassification, ClassificationError]: ...

    def register_rule(self, condition: Callable[[StepValidation, sp.Expr], bool], patron_codigo: str, priority: int = 0) -> None: ...

    def get_all_patterns(self) -> list[str]: ...


# ── Default Rule Engine Implementation ──────────────────────────────────

class DefaultErrorClassifierEngine:
    """Implementación por defecto con reglas hardcodeadas para MVP."""

    def __init__(self):
        self._rules: list[tuple[int, Callable[[StepValidation, sp.Expr], bool], str]] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        # Prioridad alta = se evalúa primero
        self.register_rule(_detect_missing_chain_rule, "ERR-CHAIN-RULE", priority=10)
        self.register_rule(_detect_sign_error, "ERR-SIGN-ERROR", priority=9)
        self.register_rule(_detect_lhopital_misuse, "ERR-LHOPITAL-MISUSE", priority=8)
        self.register_rule(_detect_limit_indeterminate_not_resolved, "ERR-LIM-INDET", priority=7)
        self.register_rule(_detect_integral_constant_missing, "ERR-INT-CONSTANT", priority=6)
        self.register_rule(_detect_algebraic_simplification_error, "ERR-ALGEBRA-SIMPLIFY", priority=5)
        self.register_rule(_detect_domain_error, "ERR-DOMAIN-VIOLATION", priority=4)
        # Fallback genérico (prioridad más baja)
        self.register_rule(lambda v, e: True, "ERR-UNCATEGORIZED", priority=0)

    def register_rule(
        self,
        condition: Callable[[StepValidation, sp.Expr], bool],
        patron_codigo: str,
        priority: int = 0
    ) -> None:
        self._rules.append((priority, condition, patron_codigo))
        # Ordenar por prioridad descendente
        self._rules.sort(key=lambda x: -x[0])

    def classify(self, validation: StepValidation, expected_expr: sp.Expr) -> Result[ErrorClassification, ClassificationError]:
        if validation.es_correcto:
            return Failure(ClassificationError(
                code="NOT_AN_ERROR",
                message="No se puede clasificar un paso correcto como error"
            ))

        try:
            for _, condition, patron_codigo in self._rules:
                if condition(validation, expected_expr):
                    confianza = 0.95 if patron_codigo != "ERR-UNCATEGORIZED" else 0.5
                    return Success(ErrorClassification(
                        patron_codigo=patron_codigo,
                        paso=validation.paso_numero,
                        confianza=confianza,
                        es_nueva_instancia=False,  # Se resuelve en UpdateGraphNode
                    ))
            # Nunca llega aquí por fallback
            return Failure(ClassificationError(
                code="CLASSIFICATION_FAILED",
                message="No se pudo clasificar el error"
            ))
        except Exception as e:
            return Failure(ClassificationError(
                code="CLASSIFICATION_EXCEPTION",
                message=f"Error en motor de clasificación: {e}"
            ))

    def get_all_patterns(self) -> list[str]:
        return [patron for _, _, patron in self._rules]


# ── Rule Functions (Pure, Testable) ────────────────────────────────────

def _detect_missing_chain_rule(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta si la derivada omite multiplicar por derivada interna (regla de la cadena)."""
    try:
        expr = sp.sympify(validation.expresion_sympy)
        # Heurística: expected tiene más factores que expr (derivada interna faltante)
        expected_factors = sp.factor(expected).as_coeff_mul()
        actual_factors = sp.factor(expr).as_coeff_mul()
        # Si expected tiene factores que expr no tiene
        expected_mul = set(str(f) for f in expected_factors[1])
        actual_mul = set(str(f) for f in actual_factors[1])
        return len(expected_mul - actual_mul) > 0
    except Exception:
        return False


def _detect_sign_error(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta error de signo (expresión correcta pero signo opuesto)."""
    try:
        expr = sp.sympify(validation.expresion_sympy)
        return sp.simplify(expr + expected) == 0
    except Exception:
        return False


def _detect_lhopital_misuse(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta mal uso de L'Hôpital (derivar sin indeterminación 0/0 o ∞/∞)."""
    latex = validation.latex_original.lower()
    return "l'hopital" in latex or "lhopital" in latex or "l'hôpital" in latex


def _detect_limit_indeterminate_not_resolved(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta indeterminación 0/0 o ∞/∞ sin resolver."""
    latex = validation.latex_original
    # Busca patrones de límite con fracción que se evalúa a 0/0
    return "lim" in latex.lower() and ("0/0" in latex or "∞/∞" in latex or "oo/oo" in latex)


def _detect_integral_constant_missing(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta constante de integración faltante (+ C)."""
    latex = validation.latex_original
    expr = sp.sympify(validation.expresion_sympy)
    # Integral indefinida: expected tiene + C que expr no tiene
    if isinstance(expected, sp.Add):
        has_constant = any(arg.free_symbols == set() for arg in expected.args)
        expr_has_constant = any(arg.free_symbols == set() for arg in expr.args if isinstance(expr, sp.Add))
        return has_constant and not expr_has_constant
    return False


def _detect_algebraic_simplification_error(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta error de simplificación algebraica (factorización, expansión)."""
    try:
        expr = sp.sympify(validation.expresion_sympy)
        # Equivalentes simbólicamente pero forma diferente
        return sp.simplify(expr - expected) == 0 and str(expr) != str(expected)
    except Exception:
        return False


def _detect_domain_error(validation: StepValidation, expected: sp.Expr) -> bool:
    """Detecta violación de dominio (raíz de negativo, log de ≤0, división por 0)."""
    latex = validation.latex_original.lower()
    domain_keywords = ["sqrt(-", "log(0", "log(-", "ln(0", "ln(-", "/0", "div(0"]
    return any(kw in latex for kw in domain_keywords)


# Factory function
def create_error_classifier() -> DefaultErrorClassifierEngine:
    return DefaultErrorClassifierEngine()
