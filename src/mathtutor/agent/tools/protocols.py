"""Protocolos e interfaces para herramientas deterministas (SymPyTool, etc.)."""

from __future__ import annotations

from typing import Protocol, Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field
from returns.result import Result
import sympy as sp


# ── SymPy Error Types ──────────────────────────────────────────────────

class SymPyError(BaseModel):
    """Error estructurado de operaciones SymPy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Literal[
        "PARSE_ERROR", "SIMPLIFY_ERROR", "EQUALS_ERROR",
        "DIFF_ERROR", "INTEGRATE_ERROR", "LIMIT_ERROR",
        "SOLVE_ERROR", "NSIMPLIFY_ERROR", "TIMEOUT"
    ]
    message: str
    latex_input: str | None = None
    details: dict = Field(default_factory=dict)


# ── Atomic Operation Contracts ─────────────────────────────────────────

class ParseLatexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    latex: Annotated[str, Field(min_length=1)]
    variables: dict[str, str] = Field(default_factory=dict)  # symbol_name -> symbol_str


class ParseLatexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_repr: str  # repr(expr) para logging/debug
    expr_serialized: str  # JSON-serializable (sympy.srepr)
    free_symbols: list[str]


class SimplifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    target_form: Literal["expanded", "factored", "cancelled", "auto"] = "auto"


class EqualsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr1_serialized: str
    expr2_serialized: str
    method: Literal["symbolic", "numeric", "both"] = "symbolic"
    numeric_samples: Annotated[int, Field(ge=1, le=100)] = 10


class EqualsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    are_equal: bool
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    method_used: str
    difference_simplified: str | None = None


class DiffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    variable: str
    order: Annotated[int, Field(ge=1, le=3)] = 1


class IntegrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    variable: str
    limits: tuple[str | float | None, str | float | None] | None = None


class LimitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    variable: str
    point: str | float
    dir: Literal["+", "-", "+-"] = "+-"


class SolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    variable: str
    domain: Literal["real", "complex", "integer"] = "real"


class NsimplifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expr_serialized: str
    tolerance: float = 1e-10
    rational: bool = True
    radicals: bool = True


# ── SymPyTool Protocol ─────────────────────────────────────────────────

class SymPyToolProtocol(Protocol):
    """Interfaz del oráculo matemático determinista."""

    async def parse_latex(self, req: ParseLatexRequest) -> Result[ParseLatexResponse, SymPyError]: ...

    async def simplify(self, req: SimplifyRequest) -> Result[ParseLatexResponse, SymPyError]: ...

    async def equals(self, req: EqualsRequest) -> Result[EqualsResponse, SymPyError]: ...

    async def diff(self, req: DiffRequest) -> Result[ParseLatexResponse, SymPyError]: ...

    async def integrate(self, req: IntegrateRequest) -> Result[ParseLatexResponse, SymPyError]: ...

    async def limit(self, req: LimitRequest) -> Result[ParseLatexResponse, SymPyError]: ...

    async def solve(self, req: SolveRequest) -> Result[list[ParseLatexResponse], SymPyError]: ...

    async def nsimplify(self, req: NsimplifyRequest) -> Result[ParseLatexResponse, SymPyError]: ...
