-- ============================================================================
-- SESIONES: Queries CRUD
-- ============================================================================

-- name: create
CREATE (s:SesionEstudio {
    id: $id,
    alumna_id: $alumna_id,
    inicio: datetime($inicio),
    fin: null,
    ejercicios_count: 0,
    score_promedio: 0.0,
    created_at: datetime()
})
RETURN s

-- name: read_by_id
MATCH (s:SesionEstudio {id: $id})
RETURN s

-- name: read_by_alumna
MATCH (s:SesionEstudio {alumna_id: $alumna_id})
RETURN s
ORDER BY s.inicio DESC
LIMIT $limit

-- name: close
MATCH (s:SesionEstudio {id: $id})
SET s.fin = datetime($fin),
    s.ejercicios_count = $ejercicios_count,
    s.score_promedio = $score_promedio,
    s.updated_at = datetime()
RETURN s

-- name: link_user
MATCH (s:SesionEstudio {id: $sesion_id}), (u:User {id: $alumna_id})
MERGE (s)-[:BELONGS_TO]->(u)
RETURN s, u

-- name: delete
MATCH (s:SesionEstudio {id: $id})
DETACH DELETE s