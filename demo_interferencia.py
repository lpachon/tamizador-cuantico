#!/usr/bin/env python3
"""
demo_interferencia.py — La diapositiva 7, en vivo y en 30 segundos.

Demuestra que dos compuertas H NO son dos lanzamientos de moneda: las
amplitudes se cancelan y el resultado «1» nunca sale.

    pip install qiskit
    python3 demo_interferencia.py

Corre en el simulador local. No necesita cuenta de IBM ni hardware.
"""
from collections import Counter
import random

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

TIRADAS = 10_000
A = "─" * 62


def moneda_clasica(n=TIRADAS):
    """Dos lanzamientos independientes de una moneda justa."""
    c = Counter()
    for _ in range(n):
        x = random.randint(0, 1)          # primer lanzamiento
        x = random.randint(0, 1)          # segundo: olvida el anterior
        c[x] += 1
    return c


def dos_hadamard(n=TIRADAS):
    """El mismo «azar» dos veces, pero con amplitudes."""
    qc = QuantumCircuit(1)
    qc.h(0)                               # primera compuerta
    qc.h(0)                               # segunda: deshace la primera
    qc.measure_all()
    return Counter(Statevector.from_label("0").evolve(
        qc.remove_final_measurements(inplace=False)).sample_counts(n))


def una_hadamard(n=TIRADAS):
    """Control: con UNA sola compuerta sí sale 50/50."""
    qc = QuantumCircuit(1)
    qc.h(0)
    return Counter(Statevector.from_label("0").evolve(qc).sample_counts(n))


def amplitudes():
    """Las amplitudes intermedias, para enseñar de dónde sale la cancelación."""
    sv0 = Statevector.from_label("0")
    qc1 = QuantumCircuit(1); qc1.h(0)
    sv1 = sv0.evolve(qc1)
    sv2 = sv1.evolve(qc1)
    return sv1.data, sv2.data


def mostrar(titulo, c, n=TIRADAS):
    p0 = 100 * c.get("0", c.get(0, 0)) / n
    p1 = 100 * c.get("1", c.get(1, 0)) / n
    print(f"  {titulo:<34} 0: {p0:6.2f} %    1: {p1:6.2f} %")


if __name__ == "__main__":
    print(f"\n{A}\n  ¿Dos compuertas H son dos lanzamientos de moneda?\n{A}")
    mostrar("Moneda clásica, 2 lanzamientos", moneda_clasica())
    mostrar("Un qubit, 1 compuerta H", una_hadamard())
    mostrar("Un qubit, 2 compuertas H", dos_hadamard())

    a1, a2 = amplitudes()
    print(f"\n{A}\n  Por qué: las amplitudes se restan\n{A}")
    print(f"  tras la 1.ª H : [{a1[0]:+.3f}, {a1[1]:+.3f}]   ← «moneda»")
    print(f"  tras la 2.ª H : [{a2[0]:+.3f}, {a2[1]:+.3f}]   ← el 1 se canceló")
    print("\n  Al estado 1 llegan dos caminos, +1/2 y −1/2. Suman cero.")
    print("  Una probabilidad nunca podría hacer eso.\n")
