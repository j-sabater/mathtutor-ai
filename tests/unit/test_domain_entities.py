"""Tests unitarios para entidades de dominio."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mathtutor.domain.entities import (
    Concepto, Ejercicio, Intento, PatronDeError, User,
    BloqueConcepto, TipoEjercicio, EstadoIntento, FuenteEjercicio,
    TipoPrerequisito, RolUsuario,
)
from mathtutor.domain.value_objects import PasoMatematico, LatexString


class TestConcepto:
    """Tests para entidad Concepto."""

    def test_create_valid_concepto(self):
        concepto = Concepto(
            codigo="LIM-01",
            nombre="Límite en un punto",
            bloque=BloqueConcepto.LIMITES,
            nivel=1,
            descripcion="Definición formal",
            latex_definicion=r"\forall \epsilon > 0",
        )
        assert concepto.codigo == "LIM-01"
        assert concepto.bloque == BloqueConcepto.LIMITES

    def test_invalid_codigo_format(self):
        with pytest.raises(ValidationError):
            Concepto(
                codigo="INVALID",  # Debe ser BLOQUE-NN
                nombre="Test",
                bloque=BloqueConcepto.LIMITES,
                nivel=1,
                descripcion="Test",
                latex_definicion="x",
            )

    def test_invalid_nivel_range(self):
        with pytest.raises(ValidationError):
            Concepto(
                codigo="LIM-01",
                nombre="Test",
                bloque=BloqueConcepto.LIMITES,
                nivel=5,  # Debe ser 1-3
                descripcion="Test",
                latex_definicion="x",
            )


class TestEjercicio:
    """Tests para entidad Ejercicio."""

    def test_create_valid_ejercicio(self):
        ejercicio = Ejercicio(
            enunciado_latex=r"\lim_{x \to 0} \frac{\sin x}{x}",
            enunciado_texto="Límite de sin(x)/x",
            tipo=TipoEjercicio.CALCULO_LIMITE,
            dificultad=3,
            tiempo_estimado=15,
            fuente=FuenteEjercicio.MANUAL,
        )
        assert ejercicio.tipo == TipoEjercicio.CALCULO_LIMITE
        assert ejercicio.dificultad == 3

    def test_invalid_dificultad(self):
        with pytest.raises(ValidationError):
            Ejercicio(
                enunciado_latex="x",
                enunciado_texto="Test",
                tipo=TipoEjercicio.CALCULO_LIMITE,
                dificultad=10,  # Debe ser 1-5
                tiempo_estimado=10,
                fuente=FuenteEjercicio.MANUAL,
            )


class TestIntento:
    """Tests para entidad Intento."""

    def test_create_valid_intento(self):
        intento = Intento(
            ejercicio_id="ej-1",
            alumna_id="alumna_principal",
            latex_extraido=r"\lim_{x \to 0} \frac{\sin x}{x}",
            pasos_structurados='[{"paso": 1, "latex": "..."}]',
            estado=EstadoIntento.PENDIENTE,
        )
        assert intento.estado == EstadoIntento.PENDIENTE
        assert intento.puntuacion == 0.0


class TestPatronDeError:
    """Tests para entidad PatronDeError."""

    def test_create_valid_patron(self):
        patron = PatronDeError(
            codigo="ERR-CHAIN-RULE",
            nombre="Olvido de regla de la cadena",
            descripcion="No multiplica por derivada interna",
            concepto_codigo="DER-03",
            severidad=2,
            ejemplo_latex=r"\frac{d}{dx}\sin(x^2) = \cos(x^2)",
            correccion_latex=r"\frac{d}{dx}\sin(x^2) = 2x\cos(x^2)",
        )
        assert patron.codigo == "ERR-CHAIN-RULE"
        assert patron.severidad == 2

    def test_invalid_codigo_format(self):
        with pytest.raises(ValidationError):
            PatronDeError(
                codigo="INVALID-CODE",  # Debe empezar con ERR-
                nombre="Test",
                descripcion="Test",
                concepto_codigo="DER-01",
                severidad=1,
                ejemplo_latex="x",
                correccion_latex="x",
            )


class TestUser:
    """Tests para entidad User."""

    def test_create_student(self):
        user = User(id="student_1", nombre="Estudiante", rol=RolUsuario.STUDENT)
        assert user.rol == RolUsuario.STUDENT

    def test_create_teacher(self):
        user = User(id="teacher_1", nombre="Profesor", rol=RolUsuario.TEACHER)
        assert user.rol == RolUsuario.TEACHER


class TestLatexString:
    """Tests para LatexString value object."""

    def test_valid_latex(self):
        latex = LatexString(r"\frac{d}{dx}x^2")
        assert str(latex) == r"\frac{d}{dx}x^2"

    def test_invalid_latex_raises(self):
        with pytest.raises(ValidationError):
            LatexString("invalid\\latex{")  # LaTeX malformed


class TestPasoMatematico:
    """Tests para PasoMatematico value object."""

    def test_valid_paso(self):
        paso = PasoMatematico(numero=1, latex=r"x^2", descripcion="Paso 1")
        assert paso.numero == 1
        assert paso.latex == r"x^2"

    def test_invalid_numero(self):
        with pytest.raises(ValidationError):
            PasoMatematico(numero=0, latex="x")  # Debe ser >= 1
