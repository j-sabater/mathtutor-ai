-- ============================================================================
-- INTENTOS: Queries CRUD y relaciones
-- ============================================================================

-- ── Create ─────────────────────────────────────────────────────────────
CREATE (i:Intento {
    id: $id,
    ejercicio_id: $ejercicio_id,
    alumna_id: $alumna_id,
    imagenes: $imagenes,
    latex_extraido: $latex_extraido,
    pasos_structurados: $pasos_structurados,
    estado: $estado,
    puntuacion: $puntuacion,
    metadatos_ocr: $metadatos_ocr,
    created_at: datetime(),
    corregido_at: null
})
RETURN i

-- ── Read by ID ─────────────────────────────────────────────────────────
MATCH (i:Intento {id: $id})
RETURN i

-- ── Read by Ejercicio ─────────────────────────────────────────────────
MATCH (i:Intento {ejercicio_id: $ejercicio_id})
RETURN i
ORDER BY i.created_at DESC

-- ── Read by Alumna y Estado ───────────────────────────────────────────
MATCH (i:Intento {alumna_id: $alumna_id})
WHERE $estado IS NULL OR i.estado = $estado
RETURN i
ORDER BY i.created_at DESC
LIMIT $limit

-- ── Update Estado ─────────────────────────────────────────────────────
MATCH (i:Intento {id: $id})
SET i.estado = $estado,
    i.updated_at = datetime()
RETURN i

-- ── Update Corrección ─────────────────────────────────────────────────
MATCH (i:Intento {id: $id})
SET i.estado = 'corregido',
    i.puntuacion = $puntuacion,
    i.corregido_at = datetime()
RETURN i

-- ── Link to Session ───────────────────────────────────────────────────
MATCH (i:Intento {id: $intento_id}), (s:SesionEstudio {id: $sesion_id})
MERGE (i)-[:BELONGS_TO_SESSION {orden: $orden}]->(s)
RETURN i, s

-- ── Link to User (MADE_BY) ────────────────────────────────────────────
MATCH (i:Intento {id: $intento_id}), (u:User {id: $alumna_id})
MERGE (i)-[:MADE_BY]->(u)
RETURN i, u

-- ── Link to Exercise (HAS_ATTEMPT) ────────────────────────────────────
MATCH (e:Ejercicio {id: $ejercicio_id}), (i:Intento {id: $intento_id})
MERGE (e)-[:HAS_ATTEMPT {orden: $orden}]->(i)
RETURN e, i

-- ── Get Intento with Errors ───────────────────────────────────────────
MATCH (i:Intento {id: $id})
OPTIONAL MATCH (i)-[he:HAS_ERROR]->(p:PatronDeError)
RETURN i,
       collect({
           patron: p,
           paso: he.paso,
           confianza: he.confianza,
           validado_por: he.validado_por
       }) AS errores

-- ── Get Recent Intentos for Profile ───────────────────────────────────
MATCH (u:User {id: $alumna_id})<-[:MADE_BY]-(i:Intento)
WHERE i.created_at >= datetime() - duration({days: $days})
RETURN i
ORDER BY i.created_at DESC
LIMIT $limit
