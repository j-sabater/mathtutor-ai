#!/usr/bin/env python3
"""Runner de migraciones Cypher para Neo4j.

Aplica migraciones versionadas en orden desde scripts/migrations/
Convención: V{version}__{description}.cypher
"""

import asyncio
import sys
import re
from pathlib import Path
from typing import Optional

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mathtutor.core.config import settings
from mathtutor.core.logging import setup_logging, get_logger
from mathtutor.graph.session import init_neo4j, close_neo4j, get_session_manager

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_PATTERN = re.compile(r"^V(\d+\.\d+\.\d+)__(.+)\.cypher$")


def discover_migrations() -> list[tuple[str, Path]]:
    """Descubre y ordena archivos de migración (excluye archivos _DOWN)."""
    migrations = []
    for filepath in sorted(MIGRATIONS_DIR.glob("V*.cypher")):
        # Excluir archivos de rollback
        if filepath.name.endswith("_DOWN.cypher"):
            continue
        match = MIGRATION_PATTERN.match(filepath.name)
        if match:
            version = match.group(1)
            # Validar formato semver básico
            if re.match(r"^\d+\.\d+\.\d+$", version):
                migrations.append((version, filepath))
            else:
                logger.warning("invalid_migration_version", file=filepath.name, version=version)
    return migrations


async def get_applied_migrations(manager) -> set[str]:
    """Obtiene versiones ya aplicadas desde la BD."""
    try:
        result = await manager.execute_query(
            "MATCH (m:Migration) RETURN m.version AS version ORDER BY m.version"
        )
        return {row["version"] for row in result}
    except Exception:
        # Tabla Migration no existe aún
        return set()


async def apply_migration(manager, version: str, filepath: Path) -> bool:
    """Aplica una migración individual."""
    content = filepath.read_text(encoding="utf-8")

    # Dividir en statements (separados por ; al final de línea)
    statements = []
    current = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            current.append(line)
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            current = []

    # Ejecutar cada statement
    for i, stmt in enumerate(statements):
        try:
            await manager.execute_write(stmt)
        except Exception as e:
            logger.error("migration_statement_failed", version=version, statement=i, error=str(e))
            return False

    # Registrar migración aplicada
    try:
        await manager.execute_write(
            "MERGE (m:Migration {version: $version}) SET m.applied_at = datetime(), m.file = $file",
            {"version": version, "file": filepath.name}
        )
    except Exception as e:
        logger.error("migration_record_failed", version=version, error=str(e))
        return False

    return True


async def main():
    setup_logging()
    logger.info("migrations_starting")

    await init_neo4j()
    manager = get_session_manager()

    try:
        # Crear nodo Migration si no existe (para tracking)
        # Neo4j 6.x usa REQUIRE en lugar de ASSERT
        await manager.execute_write("""
            CREATE CONSTRAINT migration_version_unique IF NOT EXISTS
            FOR (m:Migration) REQUIRE m.version IS UNIQUE
        """)

        migrations = discover_migrations()
        if not migrations:
            logger.info("no_migrations_found")
            return

        applied = await get_applied_migrations(manager)
        logger.info("migrations_discovered", count=len(migrations), applied=len(applied))

        pending = [(v, p) for v, p in migrations if v not in applied]
        if not pending:
            logger.info("all_migrations_applied")
            return

        logger.info("applying_pending", count=len(pending))
        for version, filepath in pending:
            logger.info("applying_migration", version=version, file=filepath.name)
            success = await apply_migration(manager, version, filepath)
            if not success:
                logger.error("migration_failed", version=version)
                sys.exit(1)
            logger.info("migration_applied", version=version)

        logger.info("all_migrations_completed")

    except Exception as e:
        logger.error("migrations_failed", error=str(e))
        raise
    finally:
        await close_neo4j()


if __name__ == "__main__":
    asyncio.run(main())