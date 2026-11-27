-- ============================================================================
-- RECOMMENDATIONS: Generación y consulta de ejercicios recomendados
-- ============================================================================

-- name: link_recommendation
MATCH (c:Concepto {codigo: $concepto_codigo}), (e:Ejercicio {id: $ejercicio_id})
MERGE (c)-[r:RECOMMENDS]->(e)
SET r.razon = $razon,
    r.prioridad = $prioridad,
    r.created_at = datetime()
RETURN r

-- name: get_recommendations_for_alumna
MATCH (u:User {id: $alumna_id})
OPTIONAL MATCH (c:Concepto)<-[:PREREQUISITE_OF*]-(weak:Concepto)
WHERE weak.codigo IN $weak_conceptos
OPTIONAL MATCH (c)-[r:RECOMMENDS]->(e:Ejercicio)
WHERE NOT (u)<-[:MADE_BY]-(:Intento)-[:HAS_ATTEMPT]->(e)
RETURN e, r.razon AS razon, r.prioridad AS prioridad, c.codigo AS concepto_origen
ORDER BY r.prioridad ASC, e.dificultad ASC
LIMIT $limit

-- name: get_recommendations_for_concepto
MATCH (c:Concepto {codigo: $concepto_codigo})-[r:RECOMMENDS]->(e:Ejercicio)
RETURN e, r.razon AS razon, r.prioridad AS prioridad
ORDER BY r.prioridad ASC
LIMIT $limit

-- name: get_student_profile
MATCH (u:User {id: $alumna_id})
OPTIONAL MATCH (u)-[m:MASTERY_LEVEL]->(c:Concepto)
OPTIONAL MATCH (u)<-[:MADE_BY]-(i:Intento)-[:HAS_ERROR]->(p:PatronDeError)
WHERE i.created_at >= datetime() - duration({days: 30})
WITH u,
     collect({codigo: c.codigo, nivel: m.nivel, aciertos: m.aciertos_consecutivos}) AS mastery_data,
     collect(DISTINCT {codigo: p.codigo, nombre: p.nombre, severidad: p.severidad, paso: 0}) AS errores_recientes,
     (SELECT count(*) FROM (u)<-[:MADE_BY]-(i2:Intento)
      WHERE i2.puntuacion >= 7.0 AND i2.created_at >= datetime() - duration({days: 7})
      ORDER BY i2.created_at DESC) AS racha_aciertos
RETURN {
    alumna_id: u.id,
    mastery: {item.codigo: item.nivel FOR item IN mastery_data},
    errores_recientes: errores_recientes,
    racha_aciertos: racha_aciertos,
    prerequisitos_faltantes: {}
} AS profile

-- name: delete_recommendation
MATCH (c:Concepto {codigo: $concepto_codigo})-[r:RECOMMENDS]->(e:Ejercicio {id: $ejercicio_id})
DELETE r