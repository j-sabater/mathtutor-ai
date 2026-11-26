"""Dominio puro: entidades, value objects, eventos y reglas de negocio."""

from mathtutor.domain.entities import (
    Concepto,
    Ejercicio,
    Intento,
    PatronDeError,
    User,
    SesionEstudio,
)
from mathtutor.domain.value_objects import (
    PasoMatematico,
    PatronErrorRef,
    MasterySnapshot,
    LatexString,
)
from mathtutor.domain.events import (
    DomainEvent,
    IntentoCreado,
    IntentoCorregido,
    MasteryActualizado,
    PatronErrorDetectado,
    EjercicioRecomendado,
    ApunteGenerado,
)
from mathtutor.domain.rules import (
    validate_prerequisite_dag,
    validate_test_weights_sum,
    validate_mastery_bounds,
    validate_latex_parseable,
    validate_ocr_confidence,
    validate_paso_sequencial,
    CycleError,
    WeightError,
    BoundError,
    ParseError,
    ConfidenceError,
    SequenceError,
)

__all__ = [
    # Entidades
    "Concepto",
    "Ejercicio",
    "Intento",
    "PatronDeError",
    "User",
    "SesionEstudio",
    # Value Objects
    "PasoMatematico",
    "PatronErrorRef",
    "MasterySnapshot",
    "LatexString",
    # Eventos
    "DomainEvent",
    "IntentoCreado",
    "IntentoCorregido",
    "MasteryActualizado",
    "PatronErrorDetectado",
    "EjercicioRecomendado",
    "ApunteGenerado",
    # Reglas y Errores
    "validate_prerequisite_dag",
    "validate_test_weights_sum",
    "validate_mastery_bounds",
    "validate_latex_parseable",
    "validate_ocr_confidence",
    "validate_paso_sequencial",
    "CycleError",
    "WeightError",
    "BoundError",
    "ParseError",
    "ConfidenceError",
    "SequenceError",
]
