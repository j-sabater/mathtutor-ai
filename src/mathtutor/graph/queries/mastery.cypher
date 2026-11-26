-- ============================================================================
-- MASTERY LEVEL: Queries EWMA y perfil de alumna
-- ============================================================================

-- ── Get Mastery for Concepto ───────────────────────────────────────────
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto {codigo: $concepto_codigo})
RETURN m.nivel AS nivel,
       m.ultima_actualizacion AS ultima_actualizacion,
       m.intentos_totales AS intentos_totales,
       m.aciertos_consecutivos AS aciertos_consecutivos

-- ── Get All Mastery for Alumna ─────────────────────────────────────────
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto)
RETURN c.codigo AS concepto_codigo,
       c.nombre AS concepto_nombre,
       c.bloque AS bloque,
       m.nivel AS nivel,
       m.intentos_totales AS intentos_totales,
       m.aciertos_consecutivos AS aciertos_consecutivos,
       m.ultima_actualizacion AS ultima_actualizacion
ORDER BY m.nivel ASC

-- ── Update Mastery EWMA (Upsert) ───────────────────────────────────────
-- alpha = 0.3 por defecto
MATCH (u:User {id: $alumna_id}), (c:Concepto {codigo: $concepto_codigo})
MERGE (u)-[m:MASTERY_LEVEL]->(c)
ON CREATE SET m.nivel = $nuevo_nivel,
              m.intentos_totales = 1,
              m.aciertos_consecutivos = CASE WHEN $es_correcto THEN 1 ELSE 0 END,
              m.ultima_actualizacion = datetime()
ON MATCH SET m.nivel = ( (1 - $alpha) * m.nivel + $alpha * $nuevo_nivel ),
              m.intentos_totales = m.intentos_totales + 1,
              m.aciertos_consecutivos = CASE WHEN $es_correcto THEN m.aciertos_consecutivos + 1 ELSE 0 END,
              m.ultima_actualizacion = datetime()
RETURN m.nivel AS nuevo_nivel

-- ── Update Mastery Fields Directamente ────────────────────────────────
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto {codigo: $concepto_codigo})
SET m.nivel = $nivel,
    m.intentos_totales = $intentos_totales,
    m.aciertos_consecutivos = $aciertos_consecutivos,
    m.ultima_actualizacion = datetime()
RETURN m

-- ── Conceptos Débiles (mastery < threshold) con Prerequisitos ─────────
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto)
WHERE m.nivel < $threshold
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF]-(pre:Concepto)
OPTIONAL MATCH (u)-[m2:MASTERY_LEVEL]->(pre)
WHERE m2 IS NULL OR m2.nivel < $prereq_threshold
RETURN c.codigo AS concepto_debil,
       c.nombre AS concepto_nombre,
       m.nivel AS mastery_actual,
       collect({
           prereq: pre.codigo,
           prereq_nombre: pre.nombre,
           mastery: m2.nivel
       }) AS prerequisitos_faltantes
ORDER BY m.nivel ASC
LIMIT $limit

-- ── Reset Mastery (para testing/admin) ────────────────────────────────
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto)
WHERE $concepto_codigo IS NULL OR c.codigo = $concepto_codigo
DELETE m
RETURN count(m) AS deleted_count
