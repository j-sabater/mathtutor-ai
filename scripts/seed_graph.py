#!/usr/bin/env python3
"""Script standalone para poblar BD con currículo base (se ejecuta via `make seed`)."""

import asyncio
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mathtutor.core.config import settings
from mathtutor.core.logging import setup_logging, get_logger
from mathtutor.graph.session import init_neo4j, close_neo4j, get_session_manager

logger = get_logger(__name__)


async def main():
    setup_logging()
    logger.info("seed_starting")

    await init_neo4j()
    manager = get_session_manager()

    try:
        # Conceptos Matemáticas II (Cálculo) - Baseline MVP
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
            {"codigo": "OPT-01", "nombre": "Optimización con derivadas (máx/mín absolutos)", "bloque": "Optimización", "nivel": 2,
             "descripcion": "Búsqueda de extremos absolutos en intervalo cerrado",
             "latex_definicion": r"f'(c)=0 \text{ y } f''(c) \neq 0 \text{ para extremos locales}",
             "prerequisitos_codigos": ["DER-02", "DER-03"]},
            {"codigo": "OPT-02", "nombre": "Problemas de optimización aplicados", "bloque": "Optimización", "nivel": 3,
             "descripcion": "Modelado y resolución de problemas reales",
             "latex_definicion": r"\max/\min f(x) \text{ s.t. } g(x) = 0",
             "prerequisitos_codigos": ["OPT-01"]},
            {"codigo": "CON-01", "nombre": "Continuidad en un punto", "bloque": "Continuidad", "nivel": 1,
             "descripcion": "Definición épsilon-delta de continuidad",
             "latex_definicion": r"\forall \epsilon > 0, \exists \delta > 0 : |x-a| < \delta \implies |f(x)-f(a)| < \epsilon",
             "prerequisitos_codigos": ["LIM-01"]},
            {"codigo": "CON-02", "nombre": "Teorema del valor intermedio", "bloque": "Continuidad", "nivel": 2,
             "descripcion": "Existencia de raíces en intervalos",
             "latex_definicion": r"f \in C[a,b],\ f(a)f(b) < 0 \implies \exists c \in (a,b): f(c)=0",
             "prerequisitos_codigos": ["CON-01"]},
        ]

        print(f"Insertando {len(conceptos)} conceptos...")
        for c in conceptos:
            query = """
            MERGE (c:Concepto {codigo: $codigo})
            SET c += $props, c.id = coalesce(c.id, randomUUID()), c.updated_at = datetime()
            """
            await manager.execute_write(query, {"codigo": c["codigo"], "props": c})
            print(f"  ✓ {c['codigo']} - {c['nombre']}")

        # Prerequisitos (edges :PREREQUISITE_OF)
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
            {"from": "OPT-01", "to": "DER-02", "tipo": "hard", "peso": 1.0},
            {"from": "OPT-01", "to": "DER-03", "tipo": "hard", "peso": 0.9},
            {"from": "OPT-02", "to": "OPT-01", "tipo": "hard", "peso": 1.0},
            {"from": "CON-01", "to": "LIM-01", "tipo": "hard", "peso": 1.0},
            {"from": "CON-02", "to": "CON-01", "tipo": "hard", "peso": 1.0},
        ]

        print(f"Creando {len(prereqs)} relaciones de prerrequisito...")
        for rel in prereqs:
            query = """
            MATCH (a:Concepto {codigo: $from}), (b:Concepto {codigo: $to})
            MERGE (a)-[r:PREREQUISITE_OF]->(b)
            SET r.tipo = $tipo, r.peso = $peso
            """
            await manager.execute_write(query, rel)
            print(f"  ✓ {rel['from']} -> {rel['to']} ({rel['tipo']}, peso={rel['peso']})")

        # Usuario por defecto
        user_query = """
        MERGE (u:User {id: 'alumna_principal'})
        SET u.nombre = 'Alumna Principal', u.rol = 'student', u.created_at = datetime()
        """
        await manager.execute_write(user_query, {})
        print("  ✓ Usuario 'alumna_principal' creado")

        print("\n✅ Seed completado exitosamente")

    except Exception as e:
        logger.error("seed_failed", error=str(e))
        print(f"\n❌ Error: {e}")
        raise
    finally:
        await close_neo4j()


if __name__ == "__main__":
    asyncio.run(main())
