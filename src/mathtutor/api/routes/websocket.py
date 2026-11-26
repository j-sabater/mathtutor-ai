"""WebSocket endpoint para streaming en tiempo real (HTMX)."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from mathtutor.api.dependencies import get_db_session
from mathtutor.agent.state import StreamChunk
from mathtutor.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["websocket"])


@router.websocket("/ws/agent/{trace_id}")
async def agent_stream(
    websocket: WebSocket,
    trace_id: str,
    session = Depends(get_db_session),
):
    """
    WebSocket para streaming de eventos del agente en tiempo real.
    Cliente HTMX consume con: hx-ext="ws" ws-connect="/api/ws/agent/{trace_id}"
    """
    await websocket.accept()
    logger.info("ws_connected", trace_id=trace_id)

    try:
        # TODO: Implementar streaming real desde LangGraph
        # await graph.astream_events(None, config={"configurable": {"thread_id": trace_id}})
        # Filtrar StreamChunk del state y enviar por WS

        # Mock: enviar evento de conexión
        chunk = StreamChunk(
            type="node_start",
            node="ingest",
            message="Conexión WebSocket establecida",
            trace_id=trace_id,
        )
        await websocket.send_json(chunk.model_dump())

        # Mantener conexión viva
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info("ws_disconnected", trace_id=trace_id)
    except Exception as e:
        logger.error("ws_error", trace_id=trace_id, error=str(e))
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
