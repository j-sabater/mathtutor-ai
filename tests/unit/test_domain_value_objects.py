"""Tests unitarios para Value Objects de dominio."""

from __future__ import annotations

import pytest
import sympy as sp

from mathtutor.domain.value_objects import (
    PasoMatematico, PatronErrorRef, MasterySnapshot, LatexString,
    OCRResult, StepValidation, ErrorClassification, GraphUpdateResult,
)
from datetime import datetime


class TestPasoMatematico:
    """Tests para PasoMatematico."""

    def test_create_valid(self):
        paso = PasoMatematico(numero=1, latex=r"x^2", descripcion="Derivada")
        assert paso.numero == 1
        assert paso.latex == r"x^2"
        assert paso.descripcion == "Derivada"

    def test_latex_validation(self):
        # LatexString valida parseabilidad con SymPy
        paso = PasoMatematico(numero=1, latex=r"\frac{d}{dx}x^2")
        assert isinstance(paso.latex, LatexString)

    def test_invalid_latex_raises(self):
        with pytest.raises(Exception):
            PasoMatematico(numero=1, latex="invalid{latex")


class TestPatronErrorRef:
    """Tests para PatronErrorRef."""

    def test_create_valid(self):
        ref = PatronErrorRef(codigo="ERR-CHAIN-RULE", paso=2, confianza=0.95)
        assert ref.codigo == "ERR-CHAIN-RULE"
        assert ref.paso == 2
        assert ref.confianza == 0.95

    def test_invalid_confianza(self):
        with pytest.raises(Exception):
            PatronErrorRef(codigo="ERR-TEST", paso=1, confianza=1.5)  # > 1.0


class TestMasterySnapshot:
    """Tests para MasterySnapshot."""

    def test_create_valid(self):
        snap = MasterySnapshot(
            concepto_codigo="DER-03",
            nivel=0.75,
            aciertos_consecutivos=3,
            ultima_actualizacion=datetime.utcnow(),
        )
        assert snap.nivel == 0.75
        assert snap.aciertos_consecutivos == 3


class TestOCRResult:
    """Tests para OCRResult."""

    def test_create_valid(self):
        pasos = [PasoMatematico(numero=1, latex=r"x^2")]
        result = OCRResult(
            latex_raw=r"x^2",
            pasos_structurados=pasos,
            strategy_used="pix2text",
            confidence=0.9,
            fallback_used=False,
            imagenes_paths=["/path/img.png"],
        )
        assert result.strategy_used == "pix2text"
        assert result.confidence == 0.9


class TestStepValidation:
    """Tests para StepValidation."""

    def test_create_correct_step(self):
        val = StepValidation(
            paso_numero=1,
            latex_original=r"2x",
            latex_normalizado=r"2*x",
            expresion_sympy="Mul(Integer(2), Symbol('x'))",
            es_correcto=True,
            mensaje_feedback="Correcto",
        )
        assert val.es_correcto is True
        assert val.tipo_error is None

    def test_create_incorrect_step(self):
        val = StepValidation(
            paso_numero=1,
            latex_original=r"x^2",
            latex_normalizado=r"x**2",
            expresion_sympy="Pow(Symbol('x'), Integer(2))",
            es_correcto=False,
            tipo_error="ERR-CHAIN-RULE",
            mensaje_feedback="Falta regla de la cadena",
            sugerencia_correccion="Multiplica por derivada interna",
        )
        assert val.es_correcto is False
        assert val.tipo_error == "ERR-CHAIN-RULE"


class TestErrorClassification:
    """Tests para ErrorClassification."""

    def test_create_valid(self):
        ec = ErrorClassification(
            patron_codigo="ERR-CHAIN-RULE",
            paso=2,
            confianza=0.9,
            es_nueva_instancia=True,
        )
        assert ec.patron_codigo == "ERR-CHAIN-RULE"
        assert ec.es_nueva_instancia is True


class TestGraphUpdateResult:
    """Tests para GraphUpdateResult."""

    def test_create_valid(self):
        from mathtutor.domain.value_objects import ErrorClassification, MasterySnapshot
        from datetime import datetime

        ec = ErrorClassification(patron_codigo="ERR-TEST", paso=1, confianza=0.8, es_nueva_instancia=False)
        snap = MasterySnapshot(concepto_codigo="DER-01", nivel=0.5, aciertos_consecutivos=0, ultima_actualizacion=datetime.utcnow())

        result = GraphUpdateResult(
            mastery_actualizado={"DER-01": 0.55},
            errores_persistidos=[ec],
            recomendaciones_creadas=["ej-123"],
        )
        assert result.mastery_actualizado["DER-01"] == 0.55
        assert len(result.errores_persistidos) == 1
        assert result.recomendaciones_creadas == ["ej-123"]
