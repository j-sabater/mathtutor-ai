"""Gestión de sesión y driver Neo4j."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from dataclasses import dataclass

from neo4j import AsyncDriver, AsyncSession, AsyncTransaction, GraphDatabase
from neo4j.exceptions import Neo4jError

from mathtutor.core.config import settings
from mathtutor.core.exceptions import GraphTransactionError
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Neo4jConfig:
    """Configuración de conexión Neo4j."""
    uri: str = settings.neo4j_uri
    user: str = settings.neo4j_user
    password: str = settings.neo4j_password
    database: str = settings.neo4j_database
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0
    max_transaction_retry_time: float = 30.0


class Neo4jSessionManager:
    """Gestor de driver y sesiones Neo4j (singleton pattern via module-level instance)."""

    def __init__(self, config: Neo4jConfig | None = None):
        self._config = config or Neo4jConfig()
        self._driver: AsyncDriver | None = None

    async def initialize(self) -> None:
        """Inicializa el driver asíncrono."""
        if self._driver is not None:
            return

        self._driver = GraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password),
            database=self._config.database,
            max_connection_pool_size=self._config.max_connection_pool_size,
            connection_timeout=self._config.connection_timeout,
        )
        # Verify connectivity
        await self._driver.verify_connectivity()
        logger.info("neo4j_driver_initialized", uri=self._config.uri, database=self._config.database)

    async def close(self) -> None:
        """Cierra el driver."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("neo4j_driver_closed")

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise RuntimeError("Neo4j driver not initialized. Call initialize() first.")
        return self._driver

    @asynccontextmanager
    async def session(self, **kwargs: Any) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para sesión simple (auto-commit)."""
        if self._driver is None:
            await self.initialize()

        async with self._driver.session(**kwargs) as session:
            try:
                yield session
            except Neo4jError as e:
                logger.error("neo4j_session_error", error=str(e))
                raise GraphTransactionError(
                    code="SESSION_ERROR",
                    message=f"Error en sesión Neo4j: {e}",
                    context={"operation": "session"},
                ) from e

    @asynccontextmanager
    async def transaction(self, **kwargs: Any) -> AsyncGenerator[AsyncTransaction, None]:
        """Context manager para transacción explícita con retry automático."""
        if self._driver is None:
            await self.initialize()

        async with self._driver.session(**kwargs) as session:
            async with session.begin_transaction() as tx:
                try:
                    yield tx
                    await tx.commit()
                except Neo4jError as e:
                    await tx.rollback()
                    logger.error("neo4j_transaction_error", error=str(e))
                    raise GraphTransactionError(
                        code="TRANSACTION_ERROR",
                        message=f"Error en transacción Neo4j: {e}",
                        context={"operation": "transaction"},
                    ) from e

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Ejecuta query de lectura simple y retorna lista de records como dicts."""
        async with self.session(**kwargs) as session:
            result = await session.run(query, parameters or {})
            return [record.data() for record in result]

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Ejecuta query de escritura en transacción y retorna resultado."""
        async with self.transaction(**kwargs) as tx:
            result = await tx.run(query, parameters or {})
            return [record.data() for record in result]


# Module-level singleton instance
_session_manager: Neo4jSessionManager | None = None


def get_session_manager() -> Neo4jSessionManager:
    """Obtiene la instancia singleton del session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = Neo4jSessionManager()
    return _session_manager


async def init_neo4j() -> None:
    """Inicializa la conexión Neo4j (llamada al startup de la app)."""
    manager = get_session_manager()
    await manager.initialize()


async def close_neo4j() -> None:
    """Cierra la conexión Neo4j (llamada al shutdown de la app)."""
    global _session_manager
    if _session_manager is not None:
        await _session_manager.close()
        _session_manager = None


# Dependency para FastAPI
async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency para inyectar sesión Neo4j."""
    manager = get_session_manager()
    async with manager.session() as session:
        yield session


async def get_neo4j_transaction() -> AsyncGenerator[AsyncTransaction, None]:
    """FastAPI dependency para inyectar transacción Neo4j."""
    manager = get_session_manager()
    async with manager.transaction() as tx:
        yield tx
