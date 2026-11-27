"""Prompt Registry - Prompt-as-Code con Jinja2 versionado."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template
from pydantic import BaseModel, ConfigDict, Field


class PromptContext(BaseModel):
    """Contexto base para todos los prompts."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    trace_id: str
    alumna_id: str
    ejercicio_id: str


class GenerateExerciseContext(PromptContext):
    """Contexto para generación de ejercicios."""
    concepto_codigo: str
    concepto_nombre: str
    concepto_bloque: str
    concepto_descripcion: str
    mastery_actual: float
    errores_recientes: list[str]
    racha_aciertos: int
    dificultad_objetivo: int
    intentos_previos: list[dict[str, Any]] = Field(default_factory=list)


class ExplainErrorContext(PromptContext):
    """Contexto para explicación de errores."""
    patron_codigo: str
    patron_nombre: str
    paso_numero: int
    latex_original: str
    latex_esperado: str
    mensaje_feedback: str
    sugerencia_correccion: str | None = None


class CorrectionFeedbackContext(PromptContext):
    """Contexto para feedback de corrección global."""
    puntuacion_global: float
    validaciones: list[dict[str, Any]]
    errores_clasificados: list[dict[str, Any]]


class PromptRegistry:
    """Registro de plantillas Jinja2 versionadas."""
    
    def __init__(self, base_path: Path | str = "src/mathtutor/agent/prompts"):
        self.base_path = Path(base_path)
        self.versions_path = self.base_path / "versions"
        self._env = Environment(
            loader=FileSystemLoader(str(self.versions_path)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._cache: dict[str, Template] = {}
    
    def _get_version_path(self, version: str) -> Path:
        """Resuelve versión (current -> latest)."""
        if version == "current":
            # Seguir symlink o usar la más reciente
            current_link = self.versions_path / "current"
            if current_link.is_symlink():
                return current_link.resolve()
            # Fallback: buscar la versión más alta
            versions = sorted([d.name for d in self.versions_path.iterdir() 
                             if d.is_dir() and d.name.startswith("v")])
            if versions:
                return self.versions_path / versions[-1]
        return self.versions_path / version
    
    def render(
        self, 
        template_name: str, 
        context: dict[str, Any] | BaseModel, 
        version: str = "current"
    ) -> str:
        """Renderiza plantilla con contexto."""
        if isinstance(context, BaseModel):
            context = context.model_dump()
        
        version_path = self._get_version_path(version)
        template_path = version_path / template_name
        
        cache_key = f"{version}/{template_name}"
        if cache_key not in self._cache:
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            self._cache[cache_key] = self._env.from_string(
                template_path.read_text(encoding="utf-8")
            )
        
        template = self._cache[cache_key]
        return template.render(**context)
    
    def list_versions(self) -> list[str]:
        """Lista versiones disponibles."""
        return sorted([
            d.name for d in self.versions_path.iterdir() 
            if d.is_dir() and d.name.startswith("v")
        ])
    
    def list_templates(self, version: str = "current") -> list[str]:
        """Lista plantillas en una versión."""
        version_path = self._get_version_path(version)
        return [f.name for f in version_path.glob("*.j2")]


# Instancia global
_prompt_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    """Obtiene instancia singleton del registry."""
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry