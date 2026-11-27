-- ============================================================================
-- ROLLBACK MIGRACIÓN V1.0.0: Esquema Inicial MathTutor-AI
-- ============================================================================
-- Ejecutar manualmente si se necesita rollback
-- ============================================================================

-- ── Drop Indexes ───────────────────────────────────────────────────────
DROP INDEX concepto_bloque_nivel_idx       IF EXISTS;
DROP INDEX ejercicio_tipo_dificultad_idx   IF EXISTS;
DROP INDEX intento_alumna_estado_idx       IF EXISTS;
DROP INDEX intento_ejercicio_idx           IF EXISTS;
DROP INDEX patron_concepto_idx             IF EXISTS;
DROP INDEX mastery_user_concepto_idx       IF EXISTS;
DROP INDEX recommends_prioridad_idx        IF EXISTS;

-- ── Drop Constraints ───────────────────────────────────────────────────
DROP CONSTRAINT concepto_id_unique     IF EXISTS;
DROP CONSTRAINT concepto_codigo_unique IF EXISTS;
DROP CONSTRAINT ejercicio_id_unique    IF EXISTS;
DROP CONSTRAINT intento_id_unique      IF EXISTS;
DROP CONSTRAINT patron_id_unique       IF EXISTS;
DROP CONSTRAINT patron_codigo_unique   IF EXISTS;
DROP CONSTRAINT user_id_unique         IF EXISTS;
DROP CONSTRAINT sesion_id_unique       IF EXISTS;

-- ── Optional: Drop all data (use with caution!) ────────────────────────
-- MATCH (n) DETACH DELETE n;