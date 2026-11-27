"""Clase base para nodos LangGraph con streaming y logging."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import structlog
from langgraph.types import Command

from mathtutor.agent.state import AgentState, StreamChunk

logger = structlog.get_logger(__name__)


class BaseNode(ABC):
    """Base para todos los nodos del workflow con capacidades de streaming y logging."""
    
    node_name: str = "base"
    
    def __init__(self):
        self._logger = logger.bind(node=self.node_name)
    
    @abstractmethod
    async def __call__(self, state: AgentState) -> AgentState | Command:
        """Ejecuta la lógica del nodo. Debe ser implementado por subclases."""
        pass
    
    def _emit_stream(
        self,
        state: AgentState,
        chunk_type: str,
        message: str,
        data: dict[str, Any] | None = None
    ) -> None:
        """Añade chunk a la cola de streaming del estado."""
        chunk = StreamChunk(
            type=chunk_type,  # type: ignore[arg-type]
            node=self.node_name,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
            trace_id=state.trace_id,
        )
        state.stream_queue.append(chunk)
        self._logger.debug("stream_emit", trace_id=state.trace_id, type=chunk_type, message=message)
    
    def _emit_node_start(self, state: AgentState, message: str | None = None) -> None:
        """Emite evento de inicio de nodo."""
        self._emit_stream(
            state, 
            "node_start", 
            message or f"Iniciando nodo {self.node_name}",
            {"node": self.node_name}
        )
    
    def _emit_node_end(self, state: AgentState, message: str | None = None, data: dict | None = None) -> None:
        """Emite evento de fin de nodo."""
        self._emit_stream(
            state,
            "node_end",
            message or f"Nodo {self.node_name} completado",
            data
        )
    
    def _emit_progress(self, state: AgentState, message: str, data: dict | None = None) -> None:
        """Emite evento de progreso."""
        self._emit_stream(state, "progress", message, data)
    
    def _emit_error(self, state: AgentState, message: str, error: Exception | None = None) -> None:
        """Emite evento de error."""
        data = {"error": str(error)} if error else None
        self._emit_stream(state, "error", message, data)
        self._logger.error("node_error", trace_id=state.trace_id, message=message, error=str(error) if error else None)
    
    def _log_start(self, state: AgentState, **extra: Any) -> None:
        """Log estructurado de inicio."""
        self._logger.info("node_start", trace_id=state.trace_id, alumna_id=state.alumna_id, ejercicio_id=state.ejercicio_id, **extra)
    
    def _log_complete(self, state: AgentState, duration_ms: float, **extra: Any) -> None:
        """Log estructurado de completación."""
        self._logger.info("node_complete", trace_id=state.trace_id, duration_ms=duration_ms, **extra)
    
    def _log_error(self, state: AgentState, error: Exception, **extra: Any) -> None:
        """Log estructurado de error."""
        self._logger.error("node_error", trace_id=state.trace_id, error=str(error), error_type=type(error).__name__, **extra)