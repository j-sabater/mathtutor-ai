"""Queries Cypher organizadas por entidad/operación.

Este módulo carga las queries desde archivos .cypher y las expone como diccionarios
para uso en los repositorios. Las queries usan parámetros ($param) exclusivamente,
nunca interpolación de strings.
"""

from pathlib import Path

_QUERIES_DIR = Path(__file__).parent

# Cargar todos los archivos .cypher
_QUERY_FILES = {
    "conceptos": "conceptos.cypher",
    "ejercicios": "ejercicios.cypher",
    "intentos": "intentos.cypher",
    "mastery": "mastery.cypher",
    "patrones": "patrones.cypher",
    "recommendations": "recommendations.cypher",
    "sesiones": "sesiones.cypher",
    "schema": "schema.cypher",
}


def _load_queries(filename: str) -> dict[str, str]:
    """Parsea un archivo .cypher y retorna dict {nombre_query: query_string}.

    Convención: cada query va precedida de un comentario '-- name: nombre_query'
    o se usa el primer comentario '--' como nombre si no hay tag explícito.
    """
    filepath = _QUERIES_DIR / filename
    content = filepath.read_text(encoding="utf-8")

    queries = {}
    current_name = None
    current_lines = []

    for line in content.splitlines():
        stripped = line.strip()

        # Detectar marcador de nombre de query
        if stripped.startswith("-- name:"):
            # Guardar query anterior si existe
            if current_name and current_lines:
                queries[current_name] = "\n".join(current_lines).strip()
            current_name = stripped.replace("-- name:", "").strip()
            current_lines = []
        elif stripped.startswith("--") and current_name is None:
            # Primer comentario del archivo o entre queries sin nombre explícito
            # Usar como nombre si parece un título
            if any(kw in stripped.lower() for kw in ["create", "read", "update", "delete", "link", "get", "seed", "verify", "top", "reset"]):
                if current_name and current_lines:
                    queries[current_name] = "\n".join(current_lines).strip()
                current_name = stripped.lstrip("- ").strip()
                current_lines = []
            else:
                current_lines.append(line)
        else:
            current_lines.append(line)

    # Guardar última query
    if current_name and current_lines:
        queries[current_name] = "\n".join(current_lines).strip()

    return queries


# Cargar todas las queries al importar el módulo
CYPHER_QUERIES: dict[str, dict[str, str]] = {}
for category, filename in _QUERY_FILES.items():
    CYPHER_QUERIES[category] = _load_queries(filename)

# También exponer flat dict para acceso directo: "conceptos.create", "ejercicios.read_by_id", etc.
ALL_QUERIES: dict[str, str] = {}
for category, queries in CYPHER_QUERIES.items():
    for name, query in queries.items():
        key = f"{category}.{name.lower().replace(' ', '_').replace('-', '_')}"
        ALL_QUERIES[key] = query


def get_query(category: str, name: str) -> str:
    """Obtiene una query por categoría y nombre."""
    return CYPHER_QUERIES[category][name]


def get_query_flat(key: str) -> str:
    """Obtiene una query por clave plana (ej. 'conceptos.create')."""
    return ALL_QUERIES[key]


# Validación en import: verificar que no hay interpolación de strings
def _validate_no_interpolation():
    """Verifica que las queries usan solo parámetros $param."""
    import re

    forbidden_patterns = [
        (r'f".*\{', "f-string interpolation"),
        (r"'.*\{.*\}'", "string format with braces"),
        (r'".*\{.*\}"', "string format with braces"),
        (r'\.format\(', ".format() call"),
        (r'%\{', "% formatting"),
    ]

    for category, queries in CYPHER_QUERIES.items():
        for name, query in queries.items():
            for pattern, desc in forbidden_patterns:
                matches = re.findall(pattern, query)
                if matches:
                    # Permitir en comentarios
                    code_lines = [l for l in query.splitlines() if not l.strip().startswith("--")]
                    code = "\n".join(code_lines)
                    if re.search(pattern, code):
                        raise ValueError(
                            f"Query '{category}.{name}' usa interpolación prohibida ({desc}): {matches}"
                        )


# Ejecutar validación al importar (solo en debug)
import os
if os.getenv("MATHTUTOR_VALIDATE_QUERIES", "0") == "1":
    _validate_no_interpolation()