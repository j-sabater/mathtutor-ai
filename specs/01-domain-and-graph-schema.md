# specs/01-domain-and-graph-schema.md — Ontología, Reglas de Negocio y Esquema del Grafo

> **Single Source of Truth** para el modelo de datos del Knowledge Graph.
> Gobierna: entidades de dominio, nodos/relaciones Neo4j, constraints, índices, queries canónicas y reglas de negocio invariantes.
> **Versión**: 1.0.0 — Baseline MVP (Matemáticas II: Cálculo)

---

## 1. Contexto del Dominio y Casos de Uso

### 1.1 Actores
| Actor | Descripción |
|-------|-------------|
| **Profesor (Tú)** | Crea/selecciona ejercicios, revisa correcciones, genera material adaptado. |
| **Alumna** | Resuelve ejercicios en papel, sube fotos/PDFs, recibe correcciones y nuevos ejercicios. |
| **Sistema (Agente)** | Orquesta ingesta → corrección → actualización grafo → generación. |

### 1.2 Casos de Uso Principales (MVP)
| ID | Caso de Uso | Descripción |
|----|-------------|-------------|
| **UC-01** | **Ingesta de intento** | Alumna sube foto/PDF → OCR → LaTeX estructurado → Persistencia como `Intento` vinculado a `Ejercicio`. |
| **UC-02** | **Corrección paso a paso** | Agente recorre pasos del `Intento`, valida cada uno con `SymPyTool`, detecta errores, clasifica `PatronDeError`. |
| **UC-03** | **Actualización de memoria** | Grafo actualizado: `Intento` → `:HAS_ERROR` → `PatronDeError`; `Concepto` → `:MASTERY_LEVEL` actualizado. |
| **UC-04** | **Generación de ejercicio adaptado** | Agente consulta grafo: conceptos débiles, prerequisitos no dominados → genera ejercicio dirigido. |
| **UC-05** | **Generación de apunte personalizado** | Agente agrega errores recurrentes → redacta apunte con ejemplos contrarios y práctica guiada. |
| **UC-06** | **Consulta de progreso** | Dashboard: dominio por concepto, racha de aciertos, patrones de error frecuentes, siguiente tema recomendado. |

### 1.3 Reglas de Negocio Invariantes (Siempre Verdaderas)
| Regla | Descripción |
|-------|-------------|
| **RN-01** | Todo `Ejercicio` **debe** estar vinculado a ≥1 `Concepto` via `:TESTS`. |
| **RN-02** | Todo `Intento` **debe** referenciar exactamente 1 `Ejercicio` y 1 `Alumna` (User). |
| **RN-03** | Un `PatronDeError` **solo** existe si ha sido detectado en ≥1 `Intento` validado por SymPy. |
| **RN-04** | La relación `:PREREQUISITE_OF` entre `Concepto`s forma un **DAG** (sin ciclos). |
| **RN-05** | `MasteryLevel` de un `Concepto` se recalcula **solo** tras `Intento` corregido (event-driven). |
| **RN-06** | `SymPyTool` es **oráculo único** de corrección matemática; LLM nunca sobrescribe su veredicto. |
| **RN-07** | `OCRStrategy` debe devolver LaTeX **válido comprobable** (parseable por `latex2sympy2` o SymPy `parse_latex`). |

---

## 2. Ontología del Grafo (Neo4j)

### 2.1 Nodos (Labels y Propiedades)

#### 2.1.1 `Concepto` — Nodo curricular atómico
```cypher
(:Concepto {
    id:              String,        // UUID v7, PK natural
    codigo:          String,        // Ej: "LIM-01", "DER-03", "INT-05" (único, legible)
    nombre:          String,        // "Límite en un punto", "Derivada de función compuesta"
    bloque:          String,        // "Límites" | "Derivadas" | "Integrales" | "Optimización" | "Continuidad"
    nivel:           Integer,       // 1..3 (básico, intermedio, avanzado EvAU)
    descripcion:     String,        // Definición matemática canónica
    latex_definicion: String,       // LaTeX de la definición formal (ej. épsilon-delta)
    prerequisitos_codigos: [String],// Códigos de conceptos prerequisito (para seed/validación)
    created_at:      DateTime,
    updated_at:      DateTime
})
```
**Constraints**:
- `CONSTRAINT ON (c:Concepto) ASSERT c.id IS UNIQUE`
- `CONSTRAINT ON (c:Concepto) ASSERT c.codigo IS UNIQUE`
- `INDEX FOR (c:Concepto) ON (c.bloque, c.nivel)`

#### 2.1.2 `Ejercicio` — Instancia de problema asignable
```cypher
(:Ejercicio {
    id:              String,        // UUID v7
    enunciado_latex: String,        // Enunciado completo en LaTeX
    enunciado_texto: String,        // Versión legible (Markdown/texto plano)
    tipo:            String,        // "calculo_limite" | "derivar_funcion" | "calcular_integral" | "optimizacion" | "estudio_funcion"
    dificultad:      Integer,       // 1..5 (EvAU: 1-2 básico, 3-4 medio, 5 difícil)
    tiempo_estimado: Integer,       // Minutos esperados
    fuente:          String,        // "manual" | "generado_ia" | "evau_2023" | "banco_ejercicios"
    metadata_json:   String,        // JSON string: { "parametros": {...}, "tags": [...] }
    created_at:      DateTime,
    updated_at:      DateTime
})
```
**Constraints**:
- `CONSTRAINT ON (e:Ejercicio) ASSERT e.id IS UNIQUE`
- `INDEX FOR (e:Ejercicio) ON (e.tipo, e.dificultad)`

#### 2.1.3 `Intento` — Resolución de la alumna (persistida tras OCR)
```cypher
(:Intento {
    id:                    String,        // UUID v7
    ejercicio_id:          String,        // FK a Ejercicio.id
    alumna_id:             String,        // FK a User.id (simplificado: "alumna_principal")
    imagenes:              [String],      // Rutas/URLs a archivos subidos (max 5)
    latex_extraido:        String,        // LaTeX bruto del OCR (multi-línea)
    pasos_structurados:    String,        // JSON string: [{ "paso": 1, "latex": "...", "descripcion": "..." }, ...]
    estado:                String,        // "pendiente" | "corrigiendo" | "corregido" | "error_ocr"
    puntuacion:            Float,         // 0.0..10.0 (calculado tras corrección)
    metadatos_ocr:         String,        // JSON: { "strategy": "pix2text", "confidence": 0.92, "fallback_used": false }
    created_at:            DateTime,
    corregido_at:          DateTime?      // Null hasta corrección
})
```
**Constraints**:
- `CONSTRAINT ON (i:Intento) ASSERT i.id IS UNIQUE`
- `INDEX FOR (i:Intento) ON (i.alumna_id, i.estado)`
- `INDEX FOR (i:Intento) ON (i.ejercicio_id)`

#### 2.1.4 `PatronDeError` — Error matemático tipificado y recurrente
```cypher
(:PatronDeError {
    id:                 String,        // UUID v7
    codigo:             String,        // Ej: "ERR-CHAIN-RULE", "ERR-LIM-INDET", "ERR-SIGN-INTEGRAL"
    nombre:             String,        // "Olvido de regla de la cadena", "Indeterminación 0/0 sin resolver"
    descripcion:        String,        // Explicación pedagógica del error
    concepto_codigo:    String,        // Concepto al que pertenece (FK lógica a Concepto.codigo)
    severidad:          Integer,       // 1..3 (leve, medio, crítico para EvAU)
    frecuencia_global:  Integer,       // Contador global (actualizado por trigger)
    ejemplo_latex:      String,        // LaTeX de ejemplo canónico del error
    correccion_latex:   String,        // LaTeX de la corrección paso a paso
    created_at:         DateTime,
    updated_at:         DateTime
})
```
**Constraints**:
- `CONSTRAINT ON (p:PatronDeError) ASSERT p.id IS UNIQUE`
- `CONSTRAINT ON (p:PatronDeError) ASSERT p.codigo IS UNIQUE`
- `INDEX FOR (p:PatronDeError) ON (p.concepto_codigo)`

#### 2.1.5 `User` — Alumna (simplificado MVP: single-user)
```cypher
(:User {
    id:              String,        // "alumna_principal"
    nombre:          String,
    email:           String?,       // Opcional
    rol:             String,        // "student" | "teacher"
    created_at:      DateTime
})
```

#### 2.1.6 `SesionEstudio` — Agregado temporal para analytics
```cypher
(:SesionEstudio {
    id:              String,        // UUID v7
    alumna_id:       String,
    inicio:          DateTime,
    fin:             DateTime?,
    ejercicios_count: Integer,
    score_promedio:  Float,
    created_at:      DateTime
})
```

---

### 2.2 Relaciones (Tipos y Propiedades)

| Relación | Origen → Destino | Propiedades | Semántica |
|----------|------------------|-------------|-----------|
| `:TESTS` | `Ejercicio` → `Concepto` | `peso: Float (0.0-1.0)`, `es_principal: Boolean` | Ejercicio evalúa concepto. Suma de pesos = 1.0 por ejercicio. |
| `:PREREQUISITE_OF` | `Concepto` → `Concepto` | `tipo: "hard" | "soft"`, `peso: Float` | Prerrequisito curricular. `hard` = indispensable; `soft` = recomendado. **DAG obligatorio**. |
| `:HAS_ATTEMPT` | `Ejercicio` → `Intento` | `orden: Integer` | Historial de intentos sobre el ejercicio. |
| `:MADE_BY` | `Intento` → `User` | — | Autoría del intento. |
| `:HAS_ERROR` | `Intento` → `PatronDeError` | `paso: Integer`, `confianza: Float (0.0-1.0)`, `validado_por: "sympy" | "llm_review"` | Error detectado en paso específico. `validado_por="sympy"` obligatorio para MVP. |
| `:MASTERY_LEVEL` | `User` → `Concepto` | `nivel: Float (0.0-1.0)`, `ultima_actualizacion: DateTime`, `intentos_totales: Integer`, `aciertos_consecutivos: Integer` | Nivel de dominio dinámico. Se recalcula por evento. |
| `:RECOMMENDS` | `Concepto` → `Ejercicio` | `razon: "prerequisito_faltante" | "refuerzo" | "avance"`, `prioridad: Integer` | Recomendación generada por agente para siguiente ejercicio. |
| `:BELONGS_TO_SESSION` | `Intento` → `SesionEstudio` | `orden: Integer` | Agrupación temporal. |

---

## 3. Constraints e Índices Completos (Cypher DDL)

```cypher
// ── Unique Constraints ────────────────────────────────────────────────
CREATE CONSTRAINT concepto_id_unique    IF NOT EXISTS FOR (c:Concepto)      ASSERT c.id IS UNIQUE;
CREATE CONSTRAINT concepto_codigo_unique IF NOT EXISTS FOR (c:Concepto)      ASSERT c.codigo IS UNIQUE;
CREATE CONSTRAINT ejercicio_id_unique   IF NOT EXISTS FOR (e:Ejercicio)     ASSERT e.id IS UNIQUE;
CREATE CONSTRAINT intento_id_unique     IF NOT EXISTS FOR (i:Intento)       ASSERT i.id IS UNIQUE;
CREATE CONSTRAINT patron_id_unique      IF NOT EXISTS FOR (p:PatronDeError) ASSERT p.id IS UNIQUE;
CREATE CONSTRAINT patron_codigo_unique  IF NOT EXISTS FOR (p:PatronDeError) ASSERT p.codigo IS UNIQUE;
CREATE CONSTRAINT user_id_unique        IF NOT EXISTS FOR (u:User)          ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT sesion_id_unique      IF NOT EXISTS FOR (s:SesionEstudio) ASSERT s.id IS UNIQUE;

// ── Indexes para Queries Frecuentes ────────────────────────────────────
CREATE INDEX concepto_bloque_nivel_idx    IF NOT EXISTS FOR (c:Concepto)      ON (c.bloque, c.nivel);
CREATE INDEX ejercicio_tipo_dificultad_idx IF NOT EXISTS FOR (e:Ejercicio)     ON (e.tipo, e.dificultad);
CREATE INDEX intento_alumna_estado_idx    IF NOT EXISTS FOR (i:Intento)       ON (i.alumna_id, i.estado);
CREATE INDEX intento_ejercicio_idx        IF NOT EXISTS FOR (i:Intento)       ON (i.ejercicio_id);
CREATE INDEX patron_concepto_idx          IF NOT EXISTS FOR (p:PatronDeError) ON (p.concepto_codigo);
CREATE INDEX mastery_user_concepto_idx    IF NOT EXISTS FOR ()-[r:MASTERY_LEVEL]-() ON (r.nivel);
CREATE INDEX recommends_prioridad_idx     IF NOT EXISTS FOR ()-[r:RECOMMENDS]-() ON (r.prioridad);

// ── Vector Index (Opcional, para RAG futuro sobre enunciados) ──────────
// CREATE VECTOR INDEX ejercicio_embedding_idx IF NOT EXISTS
// FOR (e:Ejercicio) ON (e.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};
```

---

## 4. Queries Canónicas (Read/Write Patrones)

> **Regla**: Estas queries son **referencia**. La implementación real vive en `src/mathtutor/graph/queries/*.cypher` y se invoca via `GraphRepository`.

### 4.1 Lectura: Contexto para Corrección (UC-02)
```cypher
// Obtener ejercicio con sus conceptos y prerrequisitos para validar pasos
MATCH (e:Ejercicio {id: $ejercicio_id})
OPTIONAL MATCH (e)-[t:TESTS]->(c:Concepto)
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF*]-(pre:Concepto)
RETURN e, collect(DISTINCT {concepto: c, peso: t.peso, es_principal: t.es_principal}) AS conceptos,
       collect(DISTINCT pre.codigo) AS prerequisitos_codigos
```

### 4.2 Lectura: Perfil de la Alumna para Generación Adaptada (UC-04)
```cypher
// Conceptos débiles (mastery < 0.6) con sus prerequisitos no dominados
MATCH (u:User {id: $alumna_id})-[m:MASTERY_LEVEL]->(c:Concepto)
WHERE m.nivel < 0.6
OPTIONAL MATCH (c)<-[:PREREQUISITE_OF]-(pre:Concepto)
OPTIONAL MATCH (u)-[m2:MASTERY_LEVEL]->(pre)
WHERE m2.nivel < 0.7 OR m2 IS NULL
RETURN c.codigo AS concepto_debil, c.nombre, m.nivel AS mastery_actual,
       collect({prereq: pre.codigo, mastery: m2.nivel}) AS prerequisitos_faltantes
ORDER BY m.nivel ASC
LIMIT 10
```

### 4.3 Lectura: Patrones de Error Recurrentes (UC-03, UC-05)
```cypher
// Top 5 patrones de error más frecuentes en últimos 30 días
MATCH (u:User {id: $alumna_id})<-[:MADE_BY]-(i:Intento)-[:HAS_ERROR]->(p:PatronDeError)
WHERE i.created_at >= datetime() - duration({days: 30})
RETURN p.codigo, p.nombre, p.severidad, count(*) AS frecuencia,
       collect(DISTINCT i.id) AS intentos_afectados
ORDER BY frecuencia DESC, p.severidad DESC
LIMIT 5
```

### 4.4 Escritura: Actualización Mastery Level (Event-Driven, UC-03)
```cypher
// Upsert MASTERY_LEVEL tras corrección de intento
// Lógica: EWMA (Exponentially Weighted Moving Average) con decay por tiempo
MATCH (u:User {id: $alumna_id}), (c:Concepto {codigo: $concepto_codigo})
MERGE (u)-[m:MASTERY_LEVEL]->(c)
ON CREATE SET m.nivel = $nuevo_nivel,
              m.intentos_totales = 1,
              m.aciertos_consecutivos = CASE WHEN $es_correcto THEN 1 ELSE 0 END,
              m.ultima_actualizacion = datetime()
ON MATCH SET m.nivel = (0.7 * m.nivel + 0.3 * $nuevo_nivel),  // alpha=0.3
              m.intentos_totales = m.intentos_totales + 1,
              m.aciertos_consecutivos = CASE WHEN $es_correcto THEN m.aciertos_consecutivos + 1 ELSE 0 END,
              m.ultima_actualizacion = datetime()
RETURN m
```

### 4.5 Escritura: Registro de Error Detectado (UC-02 → UC-03)
```cypher
// Vincular Intento con PatronDeError (crea patrón si no existe)
MATCH (i:Intento {id: $intento_id}), (p:PatronDeError {codigo: $patron_codigo})
MERGE (i)-[e:HAS_ERROR]->(p)
SET e.paso = $paso,
    e.confianza = $confianza,
    e.validado_por = "sympy",
    e.detectado_en = datetime()
RETURN e
```

### 4.6 Seed Inicial: Conceptos Matemáticas II (Cálculo)
```cypher
// Ejemplo de seed para bloque "Límites"
UNWIND [
  {codigo: "LIM-01", nombre: "Límite en un punto (definición épsilon-delta)", bloque: "Límites", nivel: 1,
   descripcion: "Definición formal de límite finito en un punto", latex_definicion: "\\forall \\epsilon > 0, \\exists \\delta > 0 ...",
   prerequisitos_codigos: []},
  {codigo: "LIM-02", nombre: "Límites laterales", bloque: "Límites", nivel: 1,
   descripcion: "Límite por la derecha e izquierda", latex_definicion: "\\lim_{x \\to a^+} f(x)", prerequisitos_codigos: ["LIM-01"]},
  {codigo: "LIM-03", nombre: "Indeterminaciones 0/0 e ∞/∞ (Regla de L'Hôpital)", bloque: "Límites", nivel: 2,
   descripcion: "Resolución de indeterminaciones aplicando derivada", latex_definicion: "\\lim \\frac{f}{g} = \\lim \\frac{f'}{g'}",
   prerequisitos_codigos: ["LIM-01", "DER-01"]},
  {codigo: "LIM-04", nombre: "Límites en el infinito y asíntotas", bloque: "Límites", nivel: 2,
   descripcion: "Comportamiento asintótico", latex_definicion: "\\lim_{x \\to \\pm\\infty} f(x)", prerequisitos_codigos: ["LIM-01"]}
] AS row
MERGE (c:Concepto {codigo: row.codigo})
SET c += row, c.id = apoc.create.uuid(), c.created_at = datetime(), c.updated_at = datetime()

// Crear PREREQUISITE_OF hard edges
UNWIND [
  {from: "LIM-02", to: "LIM-01", tipo: "hard", peso: 1.0},
  {from: "LIM-03", to: "LIM-01", tipo: "hard", peso: 0.7},
  {from: "LIM-03", to: "DER-01", tipo: "hard", peso: 0.9},
  {from: "LIM-04", to: "LIM-01", tipo: "soft", peso: 0.5}
] AS rel
MATCH (a:Concepto {codigo: rel.from}), (b:Concepto {codigo: rel.to})
MERGE (a)-[r:PREREQUISITE_OF]->(b)
SET r.tipo = rel.tipo, r.peso = rel.peso
```

---

## 5. Reglas de Validación de Dominio (Invariantes de Código)

> Implementadas en `src/mathtutor/domain/rules.py` como funciones puras (sin I/O).

| Regla | Función | Descripción |
|-------|---------|-------------|
| **RV-01** | `validate_prerequisite_dag(conceptos: list[Concepto]) -> Result[None, CycleError]` | Verifica que `:PREREQUISITE_OF` no introduce ciclos (Tarjan/Kahn). |
| **RV-02** | `validate_test_weights_sum(ejercicio: Ejercicio) -> Result[None, WeightError]` | Suma de `peso` en `:TESTS` salientes = 1.0 ± 0.001. |
| **RV-03** | `validate_mastery_bounds(nivel: float) -> Result[None, BoundError]` | `0.0 <= nivel <= 1.0`. |
| **RV-04** | `validate_latex_parseable(latex: str) -> Result[Expr, ParseError]` | `sympy.parse_latex(latex)` no lanza excepción. |
| **RV-05** | `validate_ocr_confidence(confidence: float) -> Result[None, ConfidenceError]` | `confidence >= 0.7` para auto-aceptar; sino flag `requiere_revision_humana`. |
| **RV-06** | `validate_paso_sequencial(pasos: list[Paso]) -> Result[None, SequenceError]` | Pasos numerados 1..N sin saltos, cada paso tiene LaTeX no vacío. |

---

## 6. Value Objects de Dominio (Pydantic v2, `frozen=True`)

> Definidos en `src/mathtutor/domain/value_objects.py`. Usados en contratos de tools, API y eventos.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Annotated
import sympy as sp

LatexString = Annotated[str, Field(min_length=1, pattern=r'^.+$')]

class PasoMatematico(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    numero: Annotated[int, Field(ge=1)]
    latex: LatexString
    descripcion: str = ""
    expresion_sympy: sp.Expr | None = Field(default=None, exclude=True)  # Cache interno

    @field_validator('latex')
    @classmethod
    def validar_latex_parseable(cls, v: str) -> str:
        try:
            sp.parse_latex(v)
        except Exception as e:
            raise ValueError(f"LaTeX no parseable por SymPy: {e}")
        return v

class PatronErrorRef(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    codigo: str
    paso: Annotated[int, Field(ge=1)]
    confianza: Annotated[float, Field(ge=0.0, le=1.0)]

class MasterySnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    concepto_codigo: str
    nivel: Annotated[float, Field(ge=0.0, le=1.0)]
    aciertos_consecutivos: int
    ultima_actualizacion: datetime
```

---

## 7. Eventos de Dominio (Para Event Sourcing / Audit Log)

> Emitidos tras comandos exitosos. Serializados a JSON en `outbox` table o Kafka (futuro). Definidos en `src/mathtutor/domain/events.py`.

| Evento | Payload Clave | Cuándo se Emite |
|--------|---------------|-----------------|
| `IntentoCreado` | `intento_id`, `ejercicio_id`, `alumna_id`, `estado="pendiente"` | Tras ingesta OCR exitosa |
| `IntentoCorregido` | `intento_id`, `puntuacion`, `errores: list[PatronErrorRef]`, `duracion_ms` | Tras corrección completa (SymPy + LLM) |
| `MasteryActualizado` | `alumna_id`, `concepto_codigo`, `nivel_anterior`, `nivel_nuevo`, `delta` | Tras recálculo EWMA |
| `PatronErrorDetectado` | `intento_id`, `patron_codigo`, `paso`, `confianza`, `nueva_instancia: bool` | Primera vez o recurrencia |
| `EjercicioRecomendado` | `alumna_id`, `ejercicio_id`, `concepto_objetivo`, `razon`, `prioridad` | Agente genera recomendación |
| `ApunteGenerado` | `alumna_id`, `conceptos_cubiertos`, `patrones_abordados`, `url_pdf` | Agente completa generación |

---

## 8. Diccionario de Datos (Referencia Rápida)

| Entidad | Tabla/Label | PK | FKs Principales | Índices Críticos |
|---------|-------------|----|-----------------|------------------|
| Concepto | `:Concepto` | `id` | — | `(bloque, nivel)`, `codigo` |
| Ejercicio | `:Ejercicio` | `id` | — | `(tipo, dificultad)` |
| Intento | `:Intento` | `id` | `ejercicio_id`, `alumna_id` | `(alumna_id, estado)`, `ejercicio_id` |
| PatronDeError | `:PatronDeError` | `id` | `concepto_codigo` (lógica) | `concepto_codigo`, `codigo` |
| User | `:User` | `id` | — | — |
| SesionEstudio | `:SesionEstudio` | `id` | `alumna_id` | — |

---

## 9. Migraciones y Versionado de Esquema

- **Tool**: `neo4j-migrations` (Java) o scripts Cypher versionados en `scripts/migrations/V{version}__{description}.cypher`.
- **Convención**: `V1.0.0__initial_schema.cypher`, `V1.1.0__add_vector_index.cypher`.
- **Ejecución**: `make migrate` (wrapper en `scripts/migrate.py` que aplica en orden transaccional).
- **Rollback**: Cada migración tiene `DOWN` correspondiente (compensación manual en Neo4j).

---

## 10. Checklist de Consistencia (Pre-Commit para esta Spec)

- [ ] Todos los `codigo` de `Concepto` y `PatronDeError` siguen patrón `BLOQUE-NN` (ej. `DER-03`).
- [ ] `:PREREQUISITE_OF` no forma ciclos (validado por `RV-01` en tests).
- [ ] Pesos `:TESTS` suman 1.0 por ejercicio (validado por `RV-02`).
- [ ] `MasteryLevel.nivel` siempre en `[0.0, 1.0]` (validado por `RV-03`).
- [ ] `LatexString` valida parseo SymPy (validado por `RV-04`).
- [ ] Queries canónicas usan parámetros (`$param`), nunca interpolación de strings.
- [ ] Índices cubren todos los patrones de acceso en UC-01..UC-06.

---

*Última actualización: 2026-11-26 — Versión 1.0.0 (Baseline MVP Matemáticas II)*
