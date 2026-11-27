"""Builder del grafo principal LangGraph (CorrectionWorkflow)."""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

from mathtutor.agent.nodes import (
    IngestNode,
    ReviewOCRNode,
    CorrectNode,
    ClassifyErrorsNode,
    UpdateGraphNode,
    GenerateRecommendationNode,
)
from mathtutor.agent.state import AgentState
from mathtutor.core.config import settings
from mathtutor.agent.tools.sympy_tool import Latex2SymPyTool
from mathtutor.agent.tools.error_classifier import create_error_classifier
from mathtutor.graph.repositories_impl import Neo4jRepositories
from mathtutor.llm.protocol import LLMProtocol
from mathtutor.ingestion.pipeline import OCRPipeline


# Global checkpointer instance (created lazily on first graph build)
_checkpointer = None
_checkpointer_ctx = None


async def _get_async_checkpointer():
    """Obtiene o crea el AsyncSqliteSaver global."""
    global _checkpointer, _checkpointer_ctx
    if _checkpointer is not None:
        return _checkpointer
    
    import re
    db_path = settings.langgraph_checkpoint_path
    # Handle both sqlite:///path and direct path formats
    match = re.match(r"sqlite:///(.+)", db_path)
    if match:
        db_path = match.group(1)
    
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # AsyncSqliteSaver.from_conn_string returns an async context manager
    # We need to enter it and keep the context alive
    _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
    _checkpointer = await _checkpointer_ctx.__aenter__()
    
    return _checkpointer


def build_main_graph(
    *,
    exercise_repo: Neo4jRepositories | None = None,
    graph_repo: Neo4jRepositories | None = None,
    error_repo: Neo4jRepositories | None = None,
    llm: LLMProtocol | None = None,
    sympy_tool: Latex2SymPyTool | None = None,
    error_classifier = None,
    ocr_pipeline: OCRPipeline | None = None,
) -> StateGraph:
    """
    Construye el workflow principal de corrección:
    Ingest → ReviewOCR(interrupt) → Correct → ClassifyErrors → UpdateGraph → GenerateRecommendation
    
    Returns:
        StateGraph compilado con AsyncSqliteSaver e interrupt_before=["review_ocr"]
    """
    workflow = StateGraph(AgentState)
    
    # Nodos (instanciados con dependencias inyectadas)
    workflow.add_node("ingest", IngestNode(
        ocr_pipeline=ocr_pipeline,
        exercise_repo=exercise_repo,
    ))
    workflow.add_node("review_ocr", ReviewOCRNode())
    workflow.add_node("correct", CorrectNode(
        sympy_tool=sympy_tool,
        exercise_repo=exercise_repo,
    ))
    workflow.add_node("classify_errors", ClassifyErrorsNode(
        error_classifier=error_classifier or create_error_classifier(),
        exercise_repo=exercise_repo,
    ))
    workflow.add_node("update_graph", UpdateGraphNode(
        graph_repo=graph_repo,
        error_repo=error_repo,
    ))
    workflow.add_node("generate_recommendation", GenerateRecommendationNode(
        llm=llm,
        sympy_tool=sympy_tool,
        graph_repo=graph_repo,
    ))
    
    # Edges - Flujo lineal
    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "review_ocr")
    workflow.add_edge("review_ocr", "correct")
    workflow.add_edge("correct", "classify_errors")
    workflow.add_edge("classify_errors", "update_graph")
    workflow.add_edge("update_graph", "generate_recommendation")
    workflow.add_edge("generate_recommendation", "__end__")
    
    # Nota: El checkpointer se inyecta en get_compiled_graph() que es async
    return workflow


async def build_main_graph_with_deps(
    repos: Neo4jRepositories,
    llm: LLMProtocol | None = None,
    ocr_pipeline: OCRPipeline | None = None,
) -> StateGraph:
    """
    Construye el workflow principal con dependencias reales inyectadas.
    """
    sympy_tool = Latex2SymPyTool(timeout_seconds=settings.sympy_timeout_seconds)
    error_classifier = create_error_classifier()
    
    return build_main_graph(
        exercise_repo=repos,
        graph_repo=repos,
        error_repo=repos,
        llm=llm,
        sympy_tool=sympy_tool,
        error_classifier=error_classifier,
        ocr_pipeline=ocr_pipeline,
    )


# Instancia global compilada (lazy, async)
_compiled_graph = None


async def get_compiled_graph() -> StateGraph:
    """Obtiene grafo compilado (singleton lazy, async por checkpointer)."""
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await _get_async_checkpointer()
        workflow = build_main_graph()
        _compiled_graph = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["review_ocr"]
        )
    return _compiled_graph


async def get_compiled_graph_with_deps(
    repos: Neo4jRepositories,
    llm: LLMProtocol | None = None,
    ocr_pipeline: OCRPipeline | None = None,
) -> StateGraph:
    """Obtiene grafo compilado con dependencias reales inyectadas."""
    workflow = await build_main_graph_with_deps(repos, llm, ocr_pipeline)
    checkpointer = await _get_async_checkpointer()
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["review_ocr"]
    )