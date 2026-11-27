-- ============================================================================
-- CONCEPTOS: Queries CRUD y navegación
-- ============================================================================

-- name: create
CREATE (c:Concepto {
    id: $id,
    codigo: $codigo,
    nombre: $nombre,
    bloque: $bloque,
    nivel: $nivel,
    descripcion: $descripcion,
    latex_definicion: $latex_definicion,
    prerequisitos_codigos: $prerequisitos_codigos,
    created_at: datetime(),
    updated_at: datetime()
})
RETURN c

-- name: read_by_id
MATCH (c:Concepto {id: $id})
RETURN c

-- name: read_by_codigo
MATCH (c:Concepto {codigo: $codigo})
RETURN c

-- name: read_all
MATCH (c:Concepto)
RETURN c
ORDER BY c.bloque, c.nivel, c.codigo

-- name: read_by_bloque
MATCH (c:Concepto {bloque: $bloque})
RETURN c
ORDER BY c.nivel, c.codigo

-- name: read_with_prereqs
MATCH (c:Concepto {codigo: $codigo})
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF*]-(pre:Concepto)
OPTIONAL MATCH (c)-[:PREREQUISITE_OF*]->(dep:Concepto)
RETURN c,
       collect(DISTINCT pre) AS prerequisitos,
       collect(DISTINCT dep) AS dependientes

-- name: update
MATCH (c:Concepto {id: $id})
SET c += $props,
    c.updated_at = datetime()
RETURN c

-- name: delete
MATCH (c:Concepto {codigo: $codigo})
DETACH DELETE c

-- name: add_prerequisite
MATCH (a:Concepto {codigo: $from_codigo}), (b:Concepto {codigo: $to_codigo})
MERGE (a)-[r:PREREQUISITE_OF]->(b)
SET r.tipo = $tipo, r.peso = $peso
RETURN r

-- name: remove_prerequisite
MATCH (a:Concepto {codigo: $from_codigo})-[r:PREREQUISITE_OF]->(b:Concepto {codigo: $to_codigo})
DELETE r

-- name: validate_dag
MATCH (a:Concepto {codigo: $from_codigo}), (b:Concepto {codigo: $to_codigo})
OPTIONAL MATCH path = (b)-[:PREREQUISITE_OF*]->(a)
RETURN path IS NOT NULL AS would_create_cycle

-- name: seed_conceptos
UNWIND $conceptos AS row
MERGE (c:Concepto {codigo: row.codigo})
SET c += row,
    c.id = coalesce(c.id, apoc.create.uuid()),
    c.created_at = coalesce(c.created_at, datetime()),
    c.updated_at = datetime()
RETURN count(c) AS created_count