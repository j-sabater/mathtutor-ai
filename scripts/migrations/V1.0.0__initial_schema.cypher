-- ============================================================================
-- MIGRACIÓN V1.0.0: Esquema Inicial MathTutor-AI (Matemáticas II: Cálculo)
-- ============================================================================
-- Ejecutar: make migrate
-- Rollback: V1.0.0__initial_schema_DOWN.cypher
-- NOTA: Neo4j 6.x usa REQUIRE en lugar de ASSERT
-- ============================================================================

-- ── Unique Constraints ────────────────────────────────────────────────
CREATE CONSTRAINT concepto_id_unique     IF NOT EXISTS FOR (c:Concepto)      REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT concepto_codigo_unique IF NOT EXISTS FOR (c:Concepto)      REQUIRE c.codigo IS UNIQUE;
CREATE CONSTRAINT ejercicio_id_unique    IF NOT EXISTS FOR (e:Ejercicio)     REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT intento_id_unique      IF NOT EXISTS FOR (i:Intento)       REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT patron_id_unique       IF NOT EXISTS FOR (p:PatronDeError) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT patron_codigo_unique   IF NOT EXISTS FOR (p:PatronDeError) REQUIRE p.codigo IS UNIQUE;
CREATE CONSTRAINT user_id_unique         IF NOT EXISTS FOR (u:User)          REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT sesion_id_unique       IF NOT EXISTS FOR (s:SesionEstudio) REQUIRE s.id IS UNIQUE;

-- ── Indexes para Queries Frecuentes ────────────────────────────────────
CREATE INDEX concepto_bloque_nivel_idx       IF NOT EXISTS FOR (c:Concepto)      ON (c.bloque, c.nivel);
CREATE INDEX ejercicio_tipo_dificultad_idx   IF NOT EXISTS FOR (e:Ejercicio)     ON (e.tipo, e.dificultad);
CREATE INDEX intento_alumna_estado_idx       IF NOT EXISTS FOR (i:Intento)       ON (i.alumna_id, i.estado);
CREATE INDEX intento_ejercicio_idx           IF NOT EXISTS FOR (i:Intento)       ON (i.ejercicio_id);
CREATE INDEX patron_concepto_idx             IF NOT EXISTS FOR (p:PatronDeError) ON (p.concepto_codigo);
CREATE INDEX mastery_user_concepto_idx       IF NOT EXISTS FOR ()-[r:MASTERY_LEVEL]-() ON (r.nivel);
CREATE INDEX recommends_prioridad_idx        IF NOT EXISTS FOR ()-[r:RECOMMENDS]-() ON (r.prioridad);

-- ── Vector Index (Opcional, para RAG futuro) ───────────────────────────
-- CREATE VECTOR INDEX ejercicio_embedding_idx IF NOT EXISTS
-- FOR (e:Ejercicio) ON (e.embedding) OPTIONS {
--   indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}
-- };