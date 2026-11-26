"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from mathtutor.core.config import Settings
from mathtutor.domain.entities import Concepto, Ejercicio, User
from mathtutor.domain.value_objects import PasoMatematico


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Configuración para tests."""
    return Settings(
        app_env="test",
        neo4j_uri="bolt://localhost:7688",
        neo4j_password="test-password",
        llm_provider="ollama",
        ollama_base_url="http://localhost:11434",
    )


@pytest.fixture
def sample_concepto() -> Concepto:
    """Concepto de prueba."""
    return Concepto(
        id="test-concepto-1",
        codigo="LIM-01",
        nombre="Límite en un punto",
        bloque="Límites",
        nivel=1,
        descripcion="Definición formal de límite",
        latex_definicion=r"\forall \epsilon > 0, \exists \delta > 0",
        prerequisitos_codigos=[],
    )


@pytest.fixture
def sample_ejercicio() -> Ejercicio:
    """Ejercicio de prueba."""
    return Ejercicio(
        id="test-ejercicio-1",
        enunciado_latex=r"\lim_{x \to 0} \frac{\sin x}{x}",
        enunciado_texto="Límite de sin(x)/x cuando x tiende a 0",
        tipo="calculo_limite",
        dificultad=2,
        tiempo_estimado=10,
        fuente="manual",
        solucion_canonica_latex="1",
        pasos_solucion=["Aplicar límite notable", "Resultado: 1"],
    )


@pytest.fixture
def sample_user() -> User:
    """Usuario de prueba."""
    return User(
        id="alumna_principal",
        nombre="Alumna Test",
        email="test@example.com",
        rol="student",
    )


@pytest.fixture
def sample_pasos() -> list[PasoMatematico]:
    """Pasos matemáticos de prueba."""
    return [
        PasoMatematico(numero=1, latex=r"\lim_{x \to 0} \frac{\sin x}{x}", descripcion="Límite original"),
        PasoMatematico(numero=2, latex=r"1", descripcion="Límite notable"),
    ]


# Mocks para repositorios
@pytest.fixture
def mock_concepto_repo():
    repo = AsyncMock()
    repo.get_by_codigo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_ejercicio_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_with_conceptos = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_llm():
    """Mock de LLMProtocol."""
    from mathtutor.llm.protocol import LLMProtocol, LLMResponse
    mock = AsyncMock(spec=LLMProtocol)
    mock.provider_name = "test"
    mock.model_name = "test-model"
    mock.generate = AsyncMock(return_value=Success(LLMResponse(
        text="{}",
        usage={},
        model="test-model",
        provider="test"
    )))
    return mock


# Import Success/Failure for mocks
from returns.result import Success, Failure
