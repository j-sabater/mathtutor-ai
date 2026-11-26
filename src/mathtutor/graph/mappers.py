"""Mappers entre entidades de dominio y nodos/relaciones Neo4j."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import json

from neo4j import Record

from mathtutor.domain.entities import (
    Concepto,
    Ejercicio,
    Intento,
    PatronDeError,
    User,
    SesionEstudio,
    TestRelation,
    MasteryLevel,
    HasErrorRelation,
    RecommendsRelation,
    BloqueConcepto,
    TipoEjercicio,
    EstadoIntento,
    FuenteEjercicio,
    TipoPrerequisito,
    RolUsuario,
    RazonRecomendacion,
)


# ── Concepto Mappers ──────────────────────────────────────────────────

def map_concepto_to_node(concepto: Concepto) -> dict[str, Any]:
    """Convierte entidad Concepto a propiedades de nodo Neo4j."""
    return {
        "id": concepto.id,
        "codigo": concepto.codigo,
        "nombre": concepto.nombre,
        "bloque": concepto.bloque.value,
        "nivel": concepto.nivel,
        "descripcion": concepto.descripcion,
        "latex_definicion": concepto.latex_definicion,
        "prerequisitos_codigos": concepto.prerequisitos_codigos,
        "created_at": concepto.created_at.isoformat() if isinstance(concepto.created_at, datetime) else concepto.created_at,
        "updated_at": concepto.updated_at.isoformat() if isinstance(concepto.updated_at, datetime) else concepto.updated_at,
    }


def map_node_to_concepto(record: Record | dict) -> Concepto:
    """Convierte registro Neo4j a entidad Concepto."""
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("c", data)  # Handle both (c) and c.property patterns

    return Concepto(
        id=props["id"],
        codigo=props["codigo"],
        nombre=props["nombre"],
        bloque=BloqueConcepto(props["bloque"]),
        nivel=props["nivel"],
        descripcion=props["descripcion"],
        latex_definicion=props["latex_definicion"],
        prerequisitos_codigos=props.get("prerequisitos_codigos", []),
        created_at=_parse_datetime(props["created_at"]),
        updated_at=_parse_datetime(props["updated_at"]),
    )


# ── Ejercicio Mappers ─────────────────────────────────────────────────

def map_ejercicio_to_node(ejercicio: Ejercicio) -> dict[str, Any]:
    return {
        "id": ejercicio.id,
        "enunciado_latex": ejercicio.enunciado_latex,
        "enunciado_texto": ejercicio.enunciado_texto,
        "tipo": ejercicio.tipo.value,
        "dificultad": ejercicio.dificultad,
        "tiempo_estimado": ejercicio.tiempo_estimado,
        "fuente": ejercicio.fuente.value,
        "metadata_json": ejercicio.metadata_json,
        "solucion_canonica_latex": ejercicio.solucion_canonica_latex,
        "pasos_solucion": json.dumps(ejercicio.pasos_solucion, ensure_ascii=False),
        "created_at": ejercicio.created_at.isoformat() if isinstance(ejercicio.created_at, datetime) else ejercicio.created_at,
        "updated_at": ejercicio.updated_at.isoformat() if isinstance(ejercicio.updated_at, datetime) else ejercicio.updated_at,
    }


def map_node_to_ejercicio(record: Record | dict) -> Ejercicio:
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("e", data)

    return Ejercicio(
        id=props["id"],
        enunciado_latex=props["enunciado_latex"],
        enunciado_texto=props["enunciado_texto"],
        tipo=TipoEjercicio(props["tipo"]),
        dificultad=props["dificultad"],
        tiempo_estimado=props["tiempo_estimado"],
        fuente=FuenteEjercicio(props["fuente"]),
        metadata_json=props.get("metadata_json", "{}"),
        solucion_canonica_latex=props.get("solucion_canonica_latex"),
        pasos_solucion=json.loads(props.get("pasos_solucion", "[]")),
        created_at=_parse_datetime(props["created_at"]),
        updated_at=_parse_datetime(props["updated_at"]),
    )


# ── Intento Mappers ───────────────────────────────────────────────────

def map_intento_to_node(intento: Intento) -> dict[str, Any]:
    return {
        "id": intento.id,
        "ejercicio_id": intento.ejercicio_id,
        "alumna_id": intento.alumna_id,
        "imagenes": intento.imagenes,
        "latex_extraido": intento.latex_extraido,
        "pasos_structurados": intento.pasos_structurados,
        "estado": intento.estado.value,
        "puntuacion": intento.puntuacion,
        "metadatos_ocr": intento.metadatos_ocr,
        "created_at": intento.created_at.isoformat() if isinstance(intento.created_at, datetime) else intento.created_at,
        "corregido_at": intento.corregido_at.isoformat() if intento.corregido_at and isinstance(intento.corregido_at, datetime) else intento.corregido_at,
    }


def map_node_to_intento(record: Record | dict) -> Intento:
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("i", data)

    return Intento(
        id=props["id"],
        ejercicio_id=props["ejercicio_id"],
        alumna_id=props["alumna_id"],
        imagenes=props.get("imagenes", []),
        latex_extraido=props["latex_extraido"],
        pasos_structurados=props["pasos_structurados"],
        estado=EstadoIntento(props["estado"]),
        puntuacion=props.get("puntuacion", 0.0),
        metadatos_ocr=props.get("metadatos_ocr", "{}"),
        created_at=_parse_datetime(props["created_at"]),
        corregido_at=_parse_datetime(props["corregido_at"]) if props.get("corregido_at") else None,
    )


# ── PatronDeError Mappers ─────────────────────────────────────────────

def map_patron_to_node(patron: PatronDeError) -> dict[str, Any]:
    return {
        "id": patron.id,
        "codigo": patron.codigo,
        "nombre": patron.nombre,
        "descripcion": patron.descripcion,
        "concepto_codigo": patron.concepto_codigo,
        "severidad": patron.severidad,
        "frecuencia_global": patron.frecuencia_global,
        "ejemplo_latex": patron.ejemplo_latex,
        "correccion_latex": patron.correccion_latex,
        "created_at": patron.created_at.isoformat() if isinstance(patron.created_at, datetime) else patron.created_at,
        "updated_at": patron.updated_at.isoformat() if isinstance(patron.updated_at, datetime) else patron.updated_at,
    }


def map_node_to_patron(record: Record | dict) -> PatronDeError:
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("p", data)

    return PatronDeError(
        id=props["id"],
        codigo=props["codigo"],
        nombre=props["nombre"],
        descripcion=props["descripcion"],
        concepto_codigo=props["concepto_codigo"],
        severidad=props["severidad"],
        frecuencia_global=props.get("frecuencia_global", 0),
        ejemplo_latex=props["ejemplo_latex"],
        correccion_latex=props["correccion_latex"],
        created_at=_parse_datetime(props["created_at"]),
        updated_at=_parse_datetime(props["updated_at"]),
    )


# ── User Mappers ──────────────────────────────────────────────────────

def map_user_to_node(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "nombre": user.nombre,
        "email": user.email,
        "rol": user.rol.value,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at,
    }


def map_node_to_user(record: Record | dict) -> User:
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("u", data)

    return User(
        id=props["id"],
        nombre=props["nombre"],
        email=props.get("email"),
        rol=RolUsuario(props["rol"]),
        created_at=_parse_datetime(props["created_at"]),
    )


# ── SesionEstudio Mappers ─────────────────────────────────────────────

def map_sesion_to_node(sesion: SesionEstudio) -> dict[str, Any]:
    return {
        "id": sesion.id,
        "alumna_id": sesion.alumna_id,
        "inicio": sesion.inicio.isoformat() if isinstance(sesion.inicio, datetime) else sesion.inicio,
        "fin": sesion.fin.isoformat() if sesion.fin and isinstance(sesion.fin, datetime) else sesion.fin,
        "ejercicios_count": sesion.ejercicios_count,
        "score_promedio": sesion.score_promedio,
        "created_at": sesion.created_at.isoformat() if isinstance(sesion.created_at, datetime) else sesion.created_at,
    }


def map_node_to_sesion(record: Record | dict) -> SesionEstudio:
    data = dict(record) if isinstance(record, Record) else record
    props = data.get("s", data)

    return SesionEstudio(
        id=props["id"],
        alumna_id=props["alumna_id"],
        inicio=_parse_datetime(props["inicio"]),
        fin=_parse_datetime(props["fin"]) if props.get("fin") else None,
        ejercicios_count=props.get("ejercicios_count", 0),
        score_promedio=props.get("score_promedio", 0.0),
        created_at=_parse_datetime(props["created_at"]),
    )


# ── Relationship Mappers ──────────────────────────────────────────────

def map_test_relation(record: Record | dict) -> TestRelation:
    data = dict(record) if isinstance(record, Record) else record
    # Asume que el record tiene r.peso, r.es_principal y nodo c
    rel = data.get("r", data)
    concepto_data = data.get("c", {})
    return TestRelation(
        concepto_codigo=concepto_data.get("codigo", ""),
        peso=rel.get("peso", 0.0),
        es_principal=rel.get("es_principal", False),
    )


def map_mastery_relation(record: Record | dict) -> MasteryLevel:
    data = dict(record) if isinstance(record, Record) else record
    rel = data.get("r", data)
    concepto_data = data.get("c", {})
    return MasteryLevel(
        alumna_id=data.get("u", {}).get("id", ""),
        concepto_codigo=concepto_data.get("codigo", ""),
        nivel=rel.get("nivel", 0.0),
        ultima_actualizacion=_parse_datetime(rel.get("ultima_actualizacion")),
        intentos_totales=rel.get("intentos_totales", 0),
        aciertos_consecutivos=rel.get("aciertos_consecutivos", 0),
    )


def map_has_error_relation(record: Record | dict) -> HasErrorRelation:
    data = dict(record) if isinstance(record, Record) else record
    rel = data.get("r", data)
    return HasErrorRelation(
        intento_id=data.get("i", {}).get("id", ""),
        patron_codigo=data.get("p", {}).get("codigo", ""),
        paso=rel.get("paso", 0),
        confianza=rel.get("confianza", 0.0),
    )


def map_recommends_relation(record: Record | dict) -> RecommendsRelation:
    data = dict(record) if isinstance(record, Record) else record
    rel = data.get("r", data)
    return RecommendsRelation(
        concepto_codigo=data.get("c", {}).get("codigo", ""),
        ejercicio_id=data.get("e", {}).get("id", ""),
        razon=RazonRecomendacion(rel.get("razon", "refuerzo")),
        prioridad=rel.get("prioridad", 1),
    )


# ── Helper ────────────────────────────────────────────────────────────

def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Handle both ISO format and Neo4j DateTime format
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Neo4j returns datetime as string with 'T' separator
            return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    return None
