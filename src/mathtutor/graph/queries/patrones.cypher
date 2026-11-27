-- ============================================================================
-- PATRONES DE ERROR: Queries CRUD y vinculación
-- ============================================================================

-- name: create
CREATE (p:PatronDeError {
    id: $id,
    codigo: $codigo,
    nombre: $nombre,
    descripcion: $descripcion,
    concepto_codigo: $concepto_codigo,
    severidad: $severidad,
    frecuencia_global: 0,
    ejemplo_latex: $ejemplo_latex,
    correccion_latex: $correccion_latex,
    created_at: datetime(),
    updated_at: datetime()
})
RETURN p

-- name: read_by_codigo
MATCH (p:PatronDeError {codigo: $codigo})
RETURN p

-- name: read_by_concepto
MATCH (p:PatronDeError {concepto_codigo: $concepto_codigo})
RETURN p
ORDER BY p.severidad DESC, p.frecuencia_global DESC

-- name: read_all
MATCH (p:PatronDeError)
RETURN p
ORDER BY p.frecuencia_global DESC, p.severidad DESC

-- name: update_frequency
MATCH (p:PatronDeError {codigo: $codigo})
SET p.frecuencia_global = p.frecuencia_global + 1,
    p.updated_at = datetime()
RETURN p.frecuencia_global AS nueva_frecuencia

-- name: link_intento_error
MATCH (i:Intento {id: $intento_id}), (p:PatronDeError {codigo: $patron_codigo})
MERGE (i)-[he:HAS_ERROR]->(p)
SET he.paso = $paso,
    he.confianza = $confianza,
    he.validado_por = 'sympy',
    he.detectado_en = datetime()
RETURN he

-- name: get_errores_intento
MATCH (i:Intento {id: $intento_id})-[he:HAS_ERROR]->(p:PatronDeError)
RETURN p.codigo AS patron_codigo,
       p.nombre AS patron_nombre,
       p.severidad AS severidad,
       he.paso AS paso,
       he.confianza AS confianza,
       he.validado_por AS validado_por

-- name: top_recurrent_patterns
MATCH (u:User {id: $alumna_id})<-[:MADE_BY]-(i:Intento)-[he:HAS_ERROR]->(p:PatronDeError)
WHERE i.created_at >= datetime() - duration({days: $days})
RETURN p.codigo, p.nombre, p.severidad, count(*) AS frecuencia,
       collect(DISTINCT i.id) AS intentos_afectados
ORDER BY frecuencia DESC, p.severidad DESC
LIMIT $limit

-- name: unlink_intento_error
MATCH (i:Intento {id: $intento_id})-[he:HAS_ERROR]->(p:PatronDeError {codigo: $patron_codigo})
DELETE he