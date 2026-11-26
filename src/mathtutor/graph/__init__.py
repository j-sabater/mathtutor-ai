"""Capa de persistencia: adaptador Neo4j (repositorios, mappers, queries)."""

from mathtutor.graph.repositories import (
    GraphRepository,
    GraphError,
    ConceptoRepository,
    EjercicioRepository,
    IntentoRepository,
    PatronErrorRepository,
    MasteryRepository,
    RecommendationRepository,
)
from mathtutor.graph.mappers import (
    map_concepto_to_node,
    map_node_to_concepto,
    map_ejercicio_to_node,
    map_node_to_ejercicio,
    map_intento_to_node,
    map_node_to_intento,
    map_patron_to_node,
    map_node_to_patron,
    map_user_to_node,
    map_node_to_user,
)

__all__ = [
    # Repositories
    "GraphRepository",
    "GraphError",
    "ConceptoRepository",
    "EjercicioRepository",
    "IntentoRepository",
    "PatronErrorRepository",
    "MasteryRepository",
    "RecommendationRepository",
    # Mappers
    "map_concepto_to_node",
    "map_node_to_concepto",
    "map_ejercicio_to_node",
    "map_node_to_ejercicio",
    "map_intento_to_node",
    "map_node_to_intento",
    "map_patron_to_node",
    "map_node_to_patron",
    "map_user_to_node",
    "map_node_to_user",
]
