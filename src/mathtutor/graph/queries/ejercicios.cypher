-- ============================================================================
-- EJERCICIOS: Queries CRUD y relación con conceptos
-- ============================================================================

-- ── Create ─────────────────────────────────────────────────────────────
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

-- ── Read by ID ─────────────────────────────────────────────────────────
MATCH (e:Ejercicio {id: $id})
RETURN e

-- ── Read with Conceptos (con pesos y principal) ───────────────────────
MATCH (e:Ejercicio {id: $id})
OPTIONAL MATCH (e)-[t:TESTS]->(c:Concepto)
RETURN e,
       collect({
           concepto: c,
           peso: t.peso,
           es_principal: t.es_principal
       }) AS tests

-- ── Read by Tipo y Dificultad ─────────────────────────────────────────
MATCH (e:Ejercicio {tipo: $tipo})
WHERE $dificultad IS NULL OR e.dificultad = $dificultad
RETURN e
ORDER BY e.dificultad, e.created_at
LIMIT $limit

-- ── Update ─────────────────────────────────────────────────────────────
MATCH (e:Ejercicio {id: $id})
SET e += $props,
    e.updated_at = datetime()
RETURN e

-- ── Delete ─────────────────────────────────────────────────────────────
MATCH (e:Ejercicio {id: $id})
DETACH DELETE e

-- ── Link Concepto (TESTS) ─────────────────────────────────────────────
MATCH (e:Ejercicio {id: $ejercicio_id}), (c:Concepto {codigo: $concepto_codigo})
MERGE (e)-[t:TESTS]->(c)
SET t.peso = $peso, t.es_principal = $es_principal
RETURN t

-- ── Unlink Concepto ───────────────────────────────────────────────────
MATCH (e:Ejercicio {id: $ejercicio_id})-[t:TESTS]->(c:Concepto {codigo: $concepto_codigo})
DELETE t

-- ── Verify Test Weights Sum = 1.0 ─────────────────────────────────────
MATCH (e:Ejercicio {id: $ejercicio_id})-[t:TESTS]->()
WITH sum(t.peso) AS total
RETURN total, abs(total - 1.0) <= 0.001 AS is_valid

-- ── Get Exercise with Prerequisites for Validation ────────────────────
MATCH (e:Ejercicio {id: $ejercicio_id})
OPTIONAL MATCH (e)-[:TESTS]->(c:Concepto)
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF*]-(pre:Concepto)
RETURN e,
       collect(DISTINCT {concepto: c, peso: 0.0, es_principal: false}) AS conceptos,
       collect(DISTINCT pre.codigo) AS prerequisitos_codigos
