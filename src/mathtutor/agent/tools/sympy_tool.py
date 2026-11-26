"""Implementación de SymPyToolProtocol usando latex2sympy2 + SymPy."""

from __future__ import annotations

import re
import sympy as sp
import latex2sympy2 as l2s
from returns.result import Result, Success, Failure

from mathtutor.agent.tools.protocols import (
    SymPyToolProtocol,
    ParseLatexRequest, ParseLatexResponse,
    SimplifyRequest, EqualsRequest, EqualsResponse,
    DiffRequest, IntegrateRequest, LimitRequest,
    SolveRequest, NsimplifyRequest,
    SymPyError,
)


class Latex2SymPyTool(SymPyToolProtocol):
    """Wrapper de latex2sympy2 + SymPy para operaciones matemáticas deterministas."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout = timeout_seconds
        self._parser = l2s.Latex2Sympy()

    def _to_sympy(self, serialized: str) -> sp.Expr:
        """Deserializa expresión SymPy desde srepr."""
        return sp.sympify(serialized)

    def _serialize(self, expr: sp.Expr) -> str:
        """Serializa expresión SymPy a srepr (canónico, lossless)."""
        return sp.srepr(expr)

    def _preprocess_latex(self, latex: str) -> str:
        """Normalización robusta para LaTeX de OCR manuscrito."""
        replacements = {
            r'\\times': '*',
            r'\\cdot': '*',
            r'\\div': '/',
            r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}': r'(\1)/(\2)',
            r'\\sqrt\s*\{([^}]+)\}': r'sqrt(\1)',
            r'\\lim_\s*\{([^}]+)\}\s*': r'limit(\1, ',
            r'\\int': 'integrate',
            r'\\sum': 'sum',
            r'\\infty': 'oo',
            r'\\pi': 'pi',
            r'\\e': 'E',
            r'\\sin': 'sin',
            r'\\cos': 'cos',
            r'\\tan': 'tan',
            r'\\log': 'log',
            r'\\ln': 'ln',
            r'\\exp': 'exp',
            r'\\frac': 'frac',
            r'\\partial': 'diff',
            r'\\mathrm{d}': '',
            r'\\,': '',
            r'\\!': '',
            r'\\ ': '',
            r'\s+': ' ',
        }
        result = latex
        for pattern, repl in replacements.items():
            result = re.sub(pattern, repl, result)
        return result.strip()

    async def parse_latex(self, req: ParseLatexRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            latex_clean = self._preprocess_latex(req.latex)
            expr = self._parser.latex2sympy(latex_clean)

            # Aplicar símbolos predefinidos
            for name, sym_str in req.variables.items():
                sym = sp.Symbol(sym_str)
                expr = expr.xreplace({sp.Symbol(name): sym})

            return Success(ParseLatexResponse(
                expr_repr=repr(expr),
                expr_serialized=self._serialize(expr),
                free_symbols=[str(s) for s in expr.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(
                code="PARSE_ERROR",
                message=str(e),
                latex_input=req.latex
            ))

    async def simplify(self, req: SimplifyRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)

            if req.target_form == "expanded":
                expr = sp.expand(expr)
            elif req.target_form == "factored":
                expr = sp.factor(expr)
            elif req.target_form == "cancelled":
                expr = sp.cancel(expr)
            else:  # auto
                expr = sp.simplify(expr)

            return Success(ParseLatexResponse(
                expr_repr=repr(expr),
                expr_serialized=self._serialize(expr),
                free_symbols=[str(s) for s in expr.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(code="SIMPLIFY_ERROR", message=str(e)))

    async def equals(self, req: EqualsRequest) -> Result[EqualsResponse, SymPyError]:
        try:
            e1 = self._to_sympy(req.expr1_serialized)
            e2 = self._to_sympy(req.expr2_serialized)

            symbolic_equal = False
            numeric_equal = True

            if req.method in ("symbolic", "both"):
                diff = sp.simplify(e1 - e2)
                symbolic_equal = diff == 0

            if req.method in ("numeric", "both"):
                vars = list(e1.free_symbols | e2.free_symbols)
                for _ in range(req.numeric_samples):
                    # Generar valores aleatorios racionales para test numérico
                    subs = {}
                    for v in vars:
                        # Usar valores simples para evitar overflow
                        subs[v] = sp.Rational(sp.randint(-5, 5), sp.randint(1, 5))
                    try:
                        v1 = complex(e1.subs(subs).evalf())
                        v2 = complex(e2.subs(subs).evalf())
                        if abs(v1 - v2) > 1e-10:
                            numeric_equal = False
                            break
                    except Exception:
                        numeric_equal = False
                        break

            are_equal = symbolic_equal and numeric_equal
            confidence = 1.0 if symbolic_equal else (0.9 if numeric_equal else 0.0)

            return Success(EqualsResponse(
                are_equal=are_equal,
                confidence=confidence,
                method_used=req.method,
                difference_simplified=self._serialize(sp.simplify(e1 - e2)) if not are_equal else None
            ))
        except Exception as e:
            return Failure(SymPyError(code="EQUALS_ERROR", message=str(e)))

    async def diff(self, req: DiffRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)
            var = sp.Symbol(req.variable)
            result = sp.diff(expr, var, req.order)

            return Success(ParseLatexResponse(
                expr_repr=repr(result),
                expr_serialized=self._serialize(result),
                free_symbols=[str(s) for s in result.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(code="DIFF_ERROR", message=str(e)))

    async def integrate(self, req: IntegrateRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)
            var = sp.Symbol(req.variable)

            if req.limits:
                lower, upper = req.limits
                lower_sym = sp.sympify(lower) if lower is not None else None
                upper_sym = sp.sympify(upper) if upper is not None else None
                result = sp.integrate(expr, (var, lower_sym, upper_sym))
            else:
                result = sp.integrate(expr, var)

            return Success(ParseLatexResponse(
                expr_repr=repr(result),
                expr_serialized=self._serialize(result),
                free_symbols=[str(s) for s in result.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(code="INTEGRATE_ERROR", message=str(e)))

    async def limit(self, req: LimitRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)
            var = sp.Symbol(req.variable)

            # Parsear punto (puede ser "oo", "-oo", "pi/2", etc.)
            if isinstance(req.point, str):
                point = sp.sympify(req.point)
            else:
                point = req.point

            dir_map = {"+": "+", "-": "-", "+-": "+-"}
            result = sp.limit(expr, var, point, dir=dir_map.get(req.dir, "+-"))

            return Success(ParseLatexResponse(
                expr_repr=repr(result),
                expr_serialized=self._serialize(result),
                free_symbols=[str(s) for s in result.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(code="LIMIT_ERROR", message=str(e)))

    async def solve(self, req: SolveRequest) -> Result[list[ParseLatexResponse], SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)
            var = sp.Symbol(req.variable)

            solutions = sp.solve(expr, var, domain=getattr(sp, req.domain.capitalize()))

            return Success([
                ParseLatexResponse(
                    expr_repr=repr(sol),
                    expr_serialized=self._serialize(sol),
                    free_symbols=[str(s) for s in sol.free_symbols]
                )
                for sol in solutions
            ])
        except Exception as e:
            return Failure(SymPyError(code="SOLVE_ERROR", message=str(e)))

    async def nsimplify(self, req: NsimplifyRequest) -> Result[ParseLatexResponse, SymPyError]:
        try:
            expr = self._to_sympy(req.expr_serialized)
            result = sp.nsimplify(expr, tolerance=req.tolerance, rational=req.rational, radicals=req.radicals)

            return Success(ParseLatexResponse(
                expr_repr=repr(result),
                expr_serialized=self._serialize(result),
                free_symbols=[str(s) for s in result.free_symbols]
            ))
        except Exception as e:
            return Failure(SymPyError(code="NSIMPLIFY_ERROR", message=str(e)))
