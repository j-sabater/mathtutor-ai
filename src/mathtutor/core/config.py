"""Configuración tipada con Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Neo4j ────────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "mathtutor-dev"
    neo4j_database: str = "neo4j"

    # ── LLM Providers ───────────────────────────────────────────────────
    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-2024-08-06"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:70b"

    # ── OCR Strategies ──────────────────────────────────────────────────
    ocr_local_enabled: bool = True
    ocr_local_model: Literal["pix2text", "nougat", "surya"] = "pix2text"
    ocr_local_device: Literal["cuda", "cpu"] = "cuda"
    ocr_fallback_enabled: bool = True
    ocr_fallback_provider: Literal["mathpix", "anthropic", "openai"] = "mathpix"
    mathpix_app_id: str = ""
    mathpix_app_key: str = ""

    # ── App ─────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    secret_key: str = "dev-secret-change-in-prod"

    # ── SymPy ───────────────────────────────────────────────────────────
    sympy_timeout_seconds: float = 10.0

    # ── LangGraph ───────────────────────────────────────────────────────
    langgraph_checkpoint_path: str = "/app/checkpoints/checkpoints.db"


settings = Settings()
