"""Tests unitarios para reglas de dominio (RV-01 a RV-06)."""

from __future__ import annotations

import pytest
import sympy as sp

from mathtutor.domain.entities import Concepto, BloqueConcepto
from mathtutor.domain.value_objects import PasoMatematico
from mathtutor.domain.rules import (
    validate_prerequisite_dag,
    validate_test_weights_sum,
    validate_mastery_bounds,
    validate_latex_parseable,
    validate_ocr_confidence,
    validate_paso_sequencial,
    CycleError, WeightError, BoundError, ParseError, ConfidenceError, SequenceError,
)


class TestValidatePrerequisiteDAG:
    """Tests para RV-01: Validar DAG de prerrequisitos."""

    def test_valid_dag_no_cycles(self):
        conceptos = [
            Concepto(codigo="LIM-01", nombre="Límite", bloque=BloqueConcepto.LIMITES, nivel=1, descripcion="", latex_definicion="x", prerequisitos_codigos=[]),
            Concepto(codigo="LIM-02", nombre="Límites laterales", bloque=BloqueConcepto.LIMITES, nivel=1, descripcion="", latex_definicion="x", prerequisitos_codigos=["LIM-01"]),
            Concepto(codigo="LIM-03", nombre="L'Hôpital", bloque=BloqueConcepto.LIMITES, nivel=2, descripcion="", latex_definicion="x", prerequisitos_codigos=["LIM-01", "DER-01"]),
        ]
        result = validate_prerequisite_dag(conceptos)
        assert result.is_success()

    def test_cycle_detected(self):
        # Crear ciclo: A -> B -> C -> A
        conceptos = [
            Concepto(codigo="A-01", nombre="A", bloque=BloqueConcepto.LIMITES, nivel=1, descripcion="", latex_definicion="x", prerequisitos_codigos=["C-01"]),
            Concepto(codigo="B-01", nombre="B", bloque=BloqueConcepto.LIMITES, nivel=1, descripcion="", latex_definicion="x", prerequisitos_codigos=["A-01"]),
            Concepto(codigo="C-01", nombre="C", bloque=BloqueConcepto.LIMITES, nivel=1, descripcion="", latex_definicion="x", prerequisitos_codigos=["B-01"]),
        ]
        result = validate_prerequisite_dag(conceptos)
        assert result.is_failure()
        assert isinstance(result.failure(), CycleError)


class TestValidateTestWeightsSum:
    """Tests para RV-02: Suma de pesos = 1.0."""

    def test_valid_weights_sum(self):
        tests = [("LIM-01", 0.6, True), ("LIM-02", 0.4, False)]
        result = validate_test_weights_sum("ej-1", tests)
        assert result.is_success()

    def test_invalid_weights_sum(self):
        tests = [("LIM-01", 0.5, True), ("LIM-02", 0.3, False)]  # Suma = 0.8
        result = validate_test_weights_sum("ej-1", tests)
        assert result.is_failure()
        assert isinstance(result.failure(), WeightError)

    def test_weights_tolerance(self):
        # 1.0 ± 0.001
        tests = [("LIM-01", 0.333, False), ("LIM-02", 0.333, False), ("LIM-03", 0.334, True)]
        result = validate_test_weights_sum("ej-1", tests)
        assert result.is_success()


class TestValidateMasteryBounds:
    """Tests para RV-03: Mastery en [0.0, 1.0]."""

    def test_valid_bounds(self):
        assert validate_mastery_bounds(0.0).is_success()
        assert validate_mastery_bounds(0.5).is_success()
        assert validate_mastery_bounds(1.0).is_success()

    def test_invalid_bounds(self):
        assert validate_mastery_bounds(-0.1).is_failure()
        assert validate_mastery_bounds(1.1).is_failure()
        assert validate_mastery_bounds(-1.0).is_failure()


class TestValidateLatexParseable:
    """Tests para RV-04: LaTeX parseable por SymPy."""

    def test_valid_latex(self):
        result = validate_latex_parseable(r"\frac{d}{dx}x^2")
        assert result.is_success()
        assert isinstance(result.unwrap(), sp.Expr)

    def test_invalid_latex(self):
        result = validate_latex_parseable("invalid{latex")
        assert result.is_failure()
        assert isinstance(result.failure(), ParseError)


class TestValidateOcrConfidence:
    """Tests para RV-05: Confianza OCR >= threshold."""

    def test_high_confidence(self):
        result = validate_ocr_confidence(0.9, threshold=0.7)
        assert result.is_success()

    def test_low_confidence(self):
        result = validate_ocr_confidence(0.5, threshold=0.7)
        assert result.is_failure()
        assert isinstance(result.failure(), ConfidenceError)

    def test_exact_threshold(self):
        result = validate_ocr_confidence(0.7, threshold=0.7)
        assert result.is_success()


class TestValidatePasoSequencial:
    """Tests para RV-06: Pasos numerados 1..N sin saltos."""

    def test_valid_sequence(self):
        pasos = [
            PasoMatematico(numero=1, latex=r"x^2"),
            PasoMatematico(numero=2, latex=r"2x"),
            PasoMatematico(numero=3, latex=r"2"),
        ]
        result = validate_paso_sequencial(pasos)
        assert result.is_success()

    def test_empty_sequence(self):
        result = validate_paso_sequencial([])
        assert result.is_failure()
        assert isinstance(result.failure(), SequenceError)

    def test_gap_in_sequence(self):
        pasos = [
            PasoMatematico(numero=1, latex=r"x^2"),
            PasoMatematico(numero=3, latex=r"2"),  # Falta paso 2
        ]
        result = validate_paso_sequencial(pasos)
        assert result.is_failure()

    def test_duplicate_numbers(self):
        pasos = [
            PasoMatematico(numero=1, latex=r"x^2"),
            PasoMatematico(numero=1, latex=r"2x"),  # Duplicado
        ]
        result = validate_paso_sequencial(pasos)
        assert result.is_failure()

    def test_empty_latex(self):
        pasos = [PasoMatematico(numero=1, latex="")]  # LaTeX vacío
        result = validate_paso_sequencial(pasos)
        assert result.is_failure()
