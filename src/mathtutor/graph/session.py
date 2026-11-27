"""Gestión de sesión y driver Neo4j (Neo4j 6.x async API)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Callable, TypeVar
from dataclasses import dataclass

from neo4j import AsyncDriver, AsyncSession, AsyncTransaction, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from mathtutor.core.config import settings
from mathtutor.core.exceptions import GraphTransactionError
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


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

        self._driver = AsyncGraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password),
            database=self._config.database,
            max_connection_pool_size=self._config.max_connection_pool_size,
            connection_timeout=self._config.connection_timeout,
        )
        # Verify connectivity (async in neo4j 6.x)
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

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Ejecuta query de lectura simple (auto-commit) y retorna lista de records como dicts."""
        if self._driver is None:
            await self.initialize()

        session = self._driver.session(**kwargs)
        try:
            result = await session.run(query, parameters or {})
            return await result.data()
        finally:
            await session.close()

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Ejecuta query de escritura en transacción explícita y retorna resultado."""
        if self._driver is None:
            await self.initialize()

        session = self._driver.session(**kwargs)
        try:
            tx = await session.begin_transaction()
            try:
                result = await tx.run(query, parameters or {})
                records = await result.data()
                await tx.commit()
                return records
            except Exception:
                await tx.rollback()
                raise
        finally:
            await session.close()

    async def execute_write_tx(
        self,
        work: Callable[[AsyncTransaction], Any],
        **kwargs: Any,
    ) -> Any:
        """Ejecuta trabajo personalizado en transacción de escritura explícita."""
        if self._driver is None:
            await self.initialize()

        session = self._driver.session(**kwargs)
        try:
            tx = await session.begin_transaction()
            try:
                result = await work(tx)
                await tx.commit()
                return result
            except Exception:
                await tx.rollback()
                raise
        finally:
            await session.close()

    async def execute_read_tx(
        self,
        work: Callable[[AsyncTransaction], Any],
        **kwargs: Any,
    ) -> Any:
        """Ejecuta trabajo personalizado en transacción de lectura explícita."""
        if self._driver is None:
            await self.initialize()

        session = self._driver.session(**kwargs)
        try:
            tx = await session.begin_transaction()
            try:
                result = await work(tx)
                await tx.commit()
                return result
            except Exception:
                await tx.rollback()
                raise
        finally:
            await session.close()


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
    if manager._driver is None:
        await manager.initialize()
    session = manager._driver.session()
    try:
        yield session
    finally:
        await session.close()


async def get_neo4j_transaction() -> AsyncGenerator[AsyncTransaction, None]:
    """FastAPI dependency para inyectar transacción Neo4j."""
    manager = get_session_manager()
    if manager._driver is None:
        await manager.initialize()
    session = manager._driver.session()
    try:
        tx = await session.begin_transaction()
        try:
            yield tx
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise
    finally:
        await session.close()