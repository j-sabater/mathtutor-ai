"""Comandos CLI administrativos (Typer)."""

from __future__ import annotations

import asyncio
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

from mathtutor.core.config import settings
from mathtutor.core.logging import setup_logging, get_logger
from mathtutor.graph.session import init_neo4j, close_neo4j, get_session_manager

app = typer.Typer(name="mathtutor", help="MathTutor-AI CLI administrativo")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logging verbose"),
):
    """Configura logging global."""
    setup_logging()
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)


@app.command()
def version():
    """Muestra versión de la aplicación."""
    from mathtutor import __version__
    console.print(f"[bold cyan]MathTutor-AI[/bold cyan] v{__version__}")


@app.command()
def config():
    """Muestra configuración actual (sin secrets)."""
    table = Table(title="Configuración MathTutor-AI")
    table.add_column("Parámetro", style="cyan")
    table.add_column("Valor", style="green")

    config_dict = settings.model_dump()
    # Ocultar secrets
    for key in ["anthropic_api_key", "openai_api_key", "mathpix_app_key", "secret_key", "neo4j_password"]:
        if key in config_dict:
            config_dict[key] = "***"

    for key, value in config_dict.items():
        table.add_row(key, str(value))

    console.print(table)


@app.command()
def check_db():
    """Verifica conectividad con Neo4j."""
    async def _check():
        await init_neo4j()
        manager = get_session_manager()
        try:
            result = await manager.execute_query("RETURN 1 AS test")
            console.print(f"[green]✓ Neo4j conectado:[/green] {result}")
        except Exception as e:
            console.print(f"[red]✗ Error conectando a Neo4j:[/red] {e}")
        finally:
            await close_neo4j()

    asyncio.run(_check())


@app.command()
def seed(
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir datos existentes"),
):
    """Puebla la BD con currículo base Matemáticas II (Conceptos, Prerequisitos, Ejercicios seed)."""
    async def _seed():
        await init_neo4j()
        manager = get_session_manager()

        try:
            # Seed conceptos (desde specs/01)
            conceptos = [
                {"codigo": "LIM-01", "nombre": "Límite en un punto (definición épsilon-delta)", "bloque": "Límites", "nivel": 1,
                 "descripcion": "Definición formal de límite finito en un punto",
                 "latex_definicion": r"\forall \epsilon > 0, \exists \delta > 0 : 0 < |x-a| < \delta \implies |f(x)-L| < \epsilon",
                 "prerequisitos_codigos": []},
                {"codigo": "LIM-02", "nombre": "Límites laterales", "bloque": "Límites", "nivel": 1,
                 "descripcion": "Límite por la derecha e izquierda",
                 "latex_definicion": r"\lim_{x \to a^+} f(x)",
                 "prerequisitos_codigos": ["LIM-01"]},
                {"codigo": "LIM-03", "nombre": "Indeterminaciones 0/0 e ∞/∞ (Regla de L'Hôpital)", "bloque": "Límites", "nivel": 2,
                 "descripcion": "Resolución de indeterminaciones aplicando derivada",
                 "latex_definicion": r"\lim \frac{f}{g} = \lim \frac{f'}{g'}",
                 "prerequisitos_codigos": ["LIM-01", "DER-01"]},
                {"codigo": "LIM-04", "nombre": "Límites en el infinito y asíntotas", "bloque": "Límites", "nivel": 2,
                 "descripcion": "Comportamiento asintótico",
                 "latex_definicion": r"\lim_{x \to \pm\infty} f(x)",
                 "prerequisitos_codigos": ["LIM-01"]},
                {"codigo": "DER-01", "nombre": "Definición de derivada", "bloque": "Derivadas", "nivel": 1,
                 "descripcion": "Derivada como límite del cociente incremental",
                 "latex_definicion": r"f'(x) = \lim_{h \to 0} \frac{f(x+h)-f(x)}{h}",
                 "prerequisitos_codigos": ["LIM-01"]},
                {"codigo": "DER-02", "nombre": "Reglas de derivación (suma, producto, cociente)", "bloque": "Derivadas", "nivel": 1,
                 "descripcion": "Reglas algebraicas básicas",
                 "latex_definicion": r"(f \pm g)' = f' \pm g',\quad (fg)' = f'g + fg',\quad (f/g)' = \frac{f'g - fg'}{g^2}",
                 "prerequisitos_codigos": ["DER-01"]},
                {"codigo": "DER-03", "nombre": "Regla de la cadena", "bloque": "Derivadas", "nivel": 2,
                 "descripcion": "Derivada de función compuesta",
                 "latex_definicion": r"(f \circ g)'(x) = f'(g(x)) \cdot g'(x)",
                 "prerequisitos_codigos": ["DER-01", "DER-02"]},
                {"codigo": "DER-04", "nombre": "Derivación implícita", "bloque": "Derivadas", "nivel": 2,
                 "descripcion": "Derivada de funciones definidas implícitamente",
                 "latex_definicion": r"\frac{dy}{dx} = -\frac{\partial F/\partial x}{\partial F/\partial y}",
                 "prerequisitos_codigos": ["DER-03"]},
                {"codigo": "INT-01", "nombre": "Integral indefinida y antiderivadas", "bloque": "Integrales", "nivel": 1,
                 "descripcion": "Concepto de antiderivada y constante de integración",
                 "latex_definicion": r"\int f(x) dx = F(x) + C \text{ donde } F' = f",
                 "prerequisitos_codigos": ["DER-01"]},
                {"codigo": "INT-02", "nombre": "Integración por partes", "bloque": "Integrales", "nivel": 2,
                 "descripcion": "Método para integrar productos",
                 "latex_definicion": r"\int u dv = uv - \int v du",
                 "prerequisitos_codigos": ["INT-01", "DER-02"]},
                {"codigo": "INT-03", "nombre": "Cambio de variable (sustitución)", "bloque": "Integrales", "nivel": 2,
                 "descripcion": "Método de sustitución en integrales",
                 "latex_definicion": r"\int f(g(x))g'(x) dx = \int f(u) du",
                 "prerequisitos_codigos": ["INT-01", "DER-03"]},
                {"codigo": "INT-04", "nombre": "Integral definida y Teorema Fundamental", "bloque": "Integrales", "nivel": 2,
                 "descripcion": "Cálculo de áreas y TFC",
                 "latex_definicion": r"\int_a^b f(x) dx = F(b) - F(a)",
                 "prerequisitos_codigos": ["INT-01"]},
            ]

            # Insertar conceptos
            for c in conceptos:
                query = """
                MERGE (c:Concepto {codigo: $codigo})
                SET c += $props, c.id = coalesce(c.id, apoc.create.uuid()), c.updated_at = datetime()
                """
                await manager.execute_write(query, {"codigo": c["codigo"], "props": c})
                console.print(f"[green]✓ Concepto creado/actualizado:[/green] {c['codigo']} - {c['nombre']}")

            # Prerequisitos
            prereqs = [
                {"from": "LIM-02", "to": "LIM-01", "tipo": "hard", "peso": 1.0},
                {"from": "LIM-03", "to": "LIM-01", "tipo": "hard", "peso": 0.7},
                {"from": "LIM-03", "to": "DER-01", "tipo": "hard", "peso": 0.9},
                {"from": "LIM-04", "to": "LIM-01", "tipo": "soft", "peso": 0.5},
                {"from": "DER-02", "to": "DER-01", "tipo": "hard", "peso": 1.0},
                {"from": "DER-03", "to": "DER-01", "tipo": "hard", "peso": 0.8},
                {"from": "DER-03", "to": "DER-02", "tipo": "hard", "peso": 0.6},
                {"from": "DER-04", "to": "DER-03", "tipo": "hard", "peso": 0.9},
                {"from": "INT-02", "to": "INT-01", "tipo": "hard", "peso": 1.0},
                {"from": "INT-02", "to": "DER-02", "tipo": "hard", "peso": 0.8},
                {"from": "INT-03", "to": "INT-01", "tipo": "hard", "peso": 1.0},
                {"from": "INT-03", "to": "DER-03", "tipo": "hard", "peso": 0.7},
                {"from": "INT-04", "to": "INT-01", "tipo": "hard", "peso": 1.0},
            ]

            for rel in prereqs:
                query = """
                MATCH (a:Concepto {codigo: $from}), (b:Concepto {codigo: $to})
                MERGE (a)-[r:PREREQUISITE_OF]->(b)
                SET r.tipo = $tipo, r.peso = $peso
                """
                await manager.execute_write(query, rel)
                console.print(f"[green]✓ Prerequisito:[/green] {rel['from']} -> {rel['to']} ({rel['tipo']})")

            console.print("[bold green]✓ Seed completado exitosamente[/bold green]")

        except Exception as e:
            console.print(f"[red]✗ Error en seed:[/red] {e}")
            raise
        finally:
            await close_neo4j()

    asyncio.run(_seed())


@app.command()
def migrate(
    version: Optional[str] = typer.Argument(None, help="Versión target (omitir para todas)"),
):
    """Ejecuta migraciones de esquema Neo4j (Cypher versionado)."""
    console.print("[yellow]Migraciones no implementadas aún[/yellow]")


if __name__ == "__main__":
    app()
