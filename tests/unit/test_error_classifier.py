"""Tests unitarios para ErrorClassifierEngine."""

from __future__ import annotations

import pytest
import sympy as sp

from mathtutor.domain.value_objects import StepValidation, ErrorClassification
from mathtutor.agent.tools.error_classifier import (
    DefaultErrorClassifierEngine,
    _detect_missing_chain_rule,
    _detect_sign_error,
    _detect_lhopital_misuse,
    _detect_limit_indeterminate_not_resolved,
    _detect_integral_constant_missing,
    _detect_algebraic_simplification_error,
    _detect_domain_error,
)
from returns.result import Success, Failure


class TestDefaultErrorClassifierEngine:
    """Tests para el motor de clasificación por defecto."""

    @pytest.fixture
    def classifier(self):
        return DefaultErrorClassifierEngine()

    def test_classify_chain_rule_error(self, classifier):
        """Detecta omisión de regla de la cadena."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"\cos(x^2)",
            latex_normalizado=r"cos(x**2)",
            expresion_sympy="cos(x**2)",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.diff(sp.sin(sp.Symbol('x')**2), sp.Symbol('x'))  # 2*x*cos(x**2)

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-CHAIN-RULE"
        assert classification.confianza == 0.95

    def test_classify_sign_error(self, classifier):
        """Detecta error de signo."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"-2x",
            latex_normalizado=r"-2*x",
            expresion_sympy="-2*x",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("2*x")  # Correcto es positivo

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-SIGN-ERROR"

    def test_classify_lhopital_misuse(self, classifier):
        """Detecta mención de L'Hôpital."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"\text{Aplicando L'Hôpital}",
            latex_normalizado=r"Aplicando L'Hôpital",
            expresion_sympy="x",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("x")

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-LHOPITAL-MISUSE"

    def test_classify_indeterminate_not_resolved(self, classifier):
        """Detecta indeterminación 0/0 sin resolver."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"\lim_{x \to 0} \frac{0}{0}",
            latex_normalizado=r"limit(0/0, x, 0)",
            expresion_sympy="0/0",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("1")

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-LIM-INDET"

    def test_classify_integral_constant_missing(self, classifier):
        """Detecta constante de integración faltante."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"x^2",
            latex_normalizado=r"x**2",
            expresion_sympy="x**2",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.Add(sp.Symbol('x')**2, sp.Symbol('C'))  # x^2 + C

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-INT-CONSTANT"

    def test_classify_uncategorized_fallback(self, classifier):
        """Fallback genérico para errores no categorizados."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"algo_raro",
            latex_normalizado=r"algo_raro",
            expresion_sympy="Symbol('algo_raro')",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("x")

        result = classifier.classify(validation, expected)
        assert result.is_success()
        classification = result.unwrap()
        assert classification.patron_codigo == "ERR-UNCATEGORIZED"
        assert classification.confianza == 0.5

    def test_classify_correct_step_raises(self, classifier):
        """No se puede clasificar un paso correcto."""
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"2x",
            latex_normalizado=r"2*x",
            expresion_sympy="2*x",
            es_correcto=True,
            mensaje_feedback="Correcto",
        )
        expected = sp.sympify("2*x")

        result = classifier.classify(validation, expected)
        assert result.is_failure()


class TestRuleFunctions:
    """Tests unitarios para funciones de regla individuales."""

    def test_detect_missing_chain_rule(self):
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"\cos(x^2)",
            latex_normalizado=r"cos(x**2)",
            expresion_sympy="cos(x**2)",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.diff(sp.sin(sp.Symbol('x')**2), sp.Symbol('x'))
        assert _detect_missing_chain_rule(validation, expected) is True

    def test_detect_sign_error(self):
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"-x",
            latex_normalizado=r"-x",
            expresion_sympy="-x",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("x")
        assert _detect_sign_error(validation, expected) is True

        # No es error de signo si no son opuestos
        validation2 = StepValidation(
            paso_numero=1,
            latex_original=r"x^2",
            latex_normalizado=r"x**2",
            expresion_sympy="x**2",
            es_correcto=False,
            mensaje_feedback="",
        )
        assert _detect_sign_error(validation2, expected) is False

    def test_detect_lhopital_misuse(self):
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"L'Hôpital",
            latex_normalizado=r"L'Hôpital",
            expresion_sympy="x",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("x")
        assert _detect_lhopital_misuse(validation, expected) is True

    def test_detect_limit_indeterminate(self):
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"0/0",
            latex_normalizado=r"0/0",
            expresion_sympy="0/0",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("1")
        assert _detect_limit_indeterminate_not_resolved(validation, expected) is True

    def test_detect_domain_error(self):
        validation = StepValidation(
            paso_numero=1,
            latex_original=r"sqrt(-1)",
            latex_normalizado=r"sqrt(-1)",
            expresion_sympy="sqrt(-1)",
            es_correcto=False,
            mensaje_feedback="",
        )
        expected = sp.sympify("x")
        assert _detect_domain_error(validation, expected) is True
