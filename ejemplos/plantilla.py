#!/usr/bin/env python3
"""Plantilla para tamizar un problema propio.

Copie este archivo, cambie las tres cosas marcadas con  # ← CAMBIE  y córralo:

    python3 ejemplos/plantilla.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tamizador import Problema, tamizar


# ── 1 · Su función objetivo ────────────────────────────────────────────
def objetivo(x):                                    # ← CAMBIE
    """Recibe un vector de numpy. Devuelve el costo (menor es mejor),
    o float("nan") si el punto viola alguna restricción.

    OJO: devolver NaN en las restricciones es imprescindible. Si no lo hace,
    el rendimiento de factibilidad saldrá 100 % y la medida 3 no medirá nada.
    """
    a, b, c = x

    # Restricciones: cada una devuelve NaN cuando se viola.
    if a + b + c > 100.0:
        return float("nan")
    if a + b + c < 40.0:
        return float("nan")

    # Costo. Aquí, un margen con rendimientos decrecientes.
    margen = 4.2 * a + 3.1 * b + 5.6 * c
    saturacion = 38.0 * np.log1p((a + 1.4 * b + 2.2 * c) / 18.0) ** 2
    return -(margen - saturacion)


# ── 2 · Las cotas de cada variable ─────────────────────────────────────
COTAS = [(0, 60), (0, 60), (0, 60)]                 # ← CAMBIE

# ── 3 · Cuánto se fía de su propio modelo ──────────────────────────────
RUIDO = 0.01                                        # ← CAMBIE (0.01 = 1 %)


if __name__ == "__main__":
    tamizar(Problema(
        nombre="Mi problema",                       # ← CAMBIE
        # Describa la decisión en una o dos frases. Se imprime al ejecutar, y
        # obliga a tener claro qué se está optimizando antes de medir nada.
        descripcion="Repartir la producción entre tres líneas para sacar el "  # ← CAMBIE
                    "mayor margen, sin pasarse de la capacidad de planta.",
        # Una etiqueta por variable, en orden. Con unidades: al imprimirse
        # junto al rango, un error de escala salta a la vista.
        variables=["a · línea A [unidades]",                     # ← CAMBIE
                   "b · línea B [unidades]",
                   "c · línea C [unidades]"],
        cotas=COTAS,
        objetivo=objetivo,
        bits_por_variable=4,
        ruido_del_modelo=RUIDO,
    ))
