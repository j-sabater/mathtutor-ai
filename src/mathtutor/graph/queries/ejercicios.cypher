-- ============================================================================
-- EJERCICIOS: Queries CRUD y relación con conceptos
-- ============================================================================

-- name: create
CREATE (e:Ejercicio {
    id: $id,
    enunciado_latex: $enunciado_latex,
    enunciado_texto: $enunciado_texto,
    tipo: $tipo,
    dificultad: $dificultad,
    tiempo_estimado: $tiempo_estimado,
    fuente: $fuente,
    metadata_json: $metadata_json,
    solucion_canonica_latex: $solucion_canonica_latex,
    pasos_solucion: $pasos_solucion,
    created_at: datetime(),
    updated_at: datetime()
})
RETURN e

-- name: read_by_id
MATCH (e:Ejercicio {id: $id})
RETURN e

-- name: read_with_conceptos
MATCH (e:Ejercicio {id: $id})
OPTIONAL MATCH (e)-[t:TESTS]->(c:Concepto)
RETURN e,
       collect({
           concepto: c,
           peso: t.peso,
           es_principal: t.es_principal
       }) AS tests

-- name: read_by_tipo_dificultad
MATCH (e:Ejercicio {tipo: $tipo})
WHERE $dificultad IS NULL OR e.dificultad = $dificultad
RETURN e
ORDER BY e.dificultad, e.created_at
LIMIT $limit

-- name: update
MATCH (e:Ejercicio {id: $id})
SET e += $props,
    e.updated_at = datetime()
RETURN e

-- name: delete
MATCH (e:Ejercicio {id: $id})
DETACH DELETE e

-- name: link_concepto
MATCH (e:Ejercicio {id: $ejercicio_id}), (c:Concepto {codigo: $concepto_codigo})
MERGE (e)-[t:TESTS]->(c)
SET t.peso = $peso, t.es_principal = $es_principal
RETURN t

-- name: unlink_concepto
MATCH (e:Ejercicio {id: $ejercicio_id})-[t:TESTS]->(c:Concepto {codigo: $concepto_codigo})
DELETE t

-- name: verify_test_weights
MATCH (e:Ejercicio {id: $ejercicio_id})-[t:TESTS]->()
WITH sum(t.peso) AS total
RETURN total, abs(total - 1.0) <= 0.001 AS is_valid

-- name: get_with_prereqs_for_validation
MATCH (e:Ejercicio {id: $ejercicio_id})
OPTIONAL MATCH (e)-[:TESTS]->(c:Concepto)
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF*]-(pre:Concepto)
RETURN e,
       collect(DISTINCT {concepto: c, peso: 0.0, es_principal: false}) AS conceptos,
       collect(DISTINCT pre.codigo) AS prerequisitos_codigos

-- name: get_context_for_correction
MATCH (e:Ejercicio {id: $ejercicio_id})
OPTIONAL MATCH (e)-[t:TESTS]->(c:Concepto)
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF*]-(pre:Concepto)
RETURN e,
       collect(DISTINCT {concepto: c, peso: t.peso, es_principal: t.es_principal}) AS conceptos,
       collect(DISTINCT pre.codigo) AS prerequisitos_codigos