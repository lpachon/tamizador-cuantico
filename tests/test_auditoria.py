"""Regresión de la auditoría — un test por hallazgo.

Cada uno de estos falla si vuelve el defecto que documenta `AUDITORIA.md`.
Sin ellos, ese registro sería una promesa en vez de una garantía.
"""
import numpy as np
import pytest

from tamizador import (Medida, Problema, _m2_estructura, _m4_planitud,
                       _m5_clasico, _muestrear, _evaluar, tamizar)


def _ising(n=14, semilla=3):
    """Un modelo de Ising exacto: el objeto más cuadrático que existe."""
    rng = np.random.default_rng(semilla)
    J = rng.normal(size=(n, n))
    J = (J + J.T) / 2
    np.fill_diagonal(J, 0.0)
    h = rng.normal(size=n)

    def costo(x):
        s = np.where(np.asarray(x) >= 0.5, 1.0, -1.0)
        return float(s @ J @ s + h @ s)

    return costo


# ── C1 (crítico) ──────────────────────────────────────────────────────
def test_c1_un_ising_genuino_sobrevive_la_traduccion():
    """Antes ajustaba el sustituto sobre la x continua y un Ising exacto
    puntuaba 0,751 y quedaba DESCARTADO. Debe dar ρ = 1."""
    v = tamizar(Problema("Ising exacto", [(0.0, 1.0)] * 14, _ising(),
                         bits_por_variable=1, n_muestras=60_000,
                         ruido_absoluto=1.0), imprimir=False)
    m2 = v.medidas[1]
    assert m2.pasa is True, f"un QUBO genuino no debería fallar: {m2.valor}"
    assert "1.000" in m2.valor or "0.99" in m2.valor, m2.valor


def test_c1_el_ajuste_usa_los_bits_y_no_la_x_continua():
    """La codificación debe reproducir los bits que vería el QUBO."""
    from tamizador import _codificar_bits
    p = Problema("x", [(0.0, 10.0)], lambda z: 0.0, bits_por_variable=3)
    # 8 niveles entre 0 y 10: el nivel k está en 10·k/7
    X = np.array([[10.0 * k / 7] for k in range(8)])
    Q = _codificar_bits(p, X)
    assert Q.shape == (8, 3)
    esperado = np.array([[(k >> b) & 1 for b in range(3)] for k in range(8)], dtype=float)
    np.testing.assert_array_equal(Q, esperado)


# ── C2 (crítico) ──────────────────────────────────────────────────────
@pytest.mark.parametrize("centro", [1000.0, 10.0, 0.1, 0.0, -500.0])
def test_c2_la_planitud_no_depende_de_donde_este_el_cero(centro):
    """Con el ruido declarado en unidades del objetivo, mover el problema por
    el eje no puede cambiar el veredicto. Antes iba de 0,18 % a 1,8e14 %."""
    vf = np.linspace(-1.0, 1.0, 5000) + centro
    m = _m4_planitud(Problema("x", [(0, 1)], lambda z: 0.0, ruido_absoluto=0.1), vf)
    assert m.pasa is True, f"centro={centro}: {m.valor}"


def test_c2_el_ruido_relativo_se_declara_no_concluyente_cerca_del_cero():
    """Un objetivo que cruza el cero hace que un ruido RELATIVO no signifique
    nada. La herramienta debe decirlo, no inventarse un porcentaje."""
    vf = np.linspace(-1.0, 1.0, 5000)          # mediana ≈ 0
    m = _m4_planitud(Problema("x", [(0, 1)], lambda z: 0.0, ruido_del_modelo=0.01), vf)
    assert m.pasa is None
    assert "ruido_absoluto" in m.comentario


# ── C3 (alto) ─────────────────────────────────────────────────────────
@pytest.mark.skipif(not __import__("tamizador").HAY_SCIPY,
                    reason="el refinamiento clásico usa COBYLA de scipy")
def test_c3_el_refinamiento_clasico_mejora_de_verdad():
    """COBYLA corría con un paso fijo de 0,05 sin mirar el rango de las
    variables: sobre [0,60] mejoraba 0,086 en vez de 1,4. Subestimar la línea
    base clásica sesga el filtro A FAVOR de la cuántica."""
    from tamizador import ejemplo_mezcla_de_produccion
    p = ejemplo_mezcla_de_produccion()
    Xf, vf = _evaluar(p, _muestrear(p))
    mejor_sobol = float(vf.min())
    m = _m5_clasico(p, Xf, vf, 0.0)
    reportado = float(m.valor.split(" en ")[0].replace(",", ""))
    mejora = mejor_sobol - reportado
    assert mejora > 0.5, f"el refinamiento apenas mejoró {mejora:.3f} sobre Sobol"


# ── C4 (alto) ─────────────────────────────────────────────────────────
def test_c4_ruido_puro_con_pocos_puntos_no_da_correlacion_perfecta():
    """Con 40 puntos y cientos de términos, el ajuste es memoria, no
    estructura. Antes devolvía ρ = 1,000 sobre ruido puro."""
    rng = np.random.default_rng(1)
    p = Problema("x", [(0, 1)] * 10, lambda z: 0.0, bits_por_variable=3)
    m = _m2_estructura(p, rng.random((40, 10)), rng.random(40))
    assert m.pasa is None, f"debería no concluir, y dijo: {m.valor}"


def test_c4_con_muestras_de_sobra_si_concluye():
    """Y el contrapunto: con datos suficientes la medida sí debe pronunciarse."""
    rng = np.random.default_rng(2)
    X = rng.random((6000, 3))
    p = Problema("x", [(0, 1)] * 3, lambda z: 0.0, bits_por_variable=2)
    m = _m2_estructura(p, X, X[:, 0] + 2 * X[:, 1])
    assert m.pasa is not None


# ── C5 (medio) ────────────────────────────────────────────────────────
def test_c5_el_ejemplo_de_ascenso_es_dimensionalmente_plausible():
    """El ejemplo restaba una velocidad a una distancia. Ahora se integra en
    metros y segundos: las magnitudes tienen que salir de un avión real."""
    from tamizador import ejemplo_ascenso_restringido
    p = ejemplo_ascenso_restringido()
    Xf, vf = _evaluar(p, _muestrear(p))
    assert len(vf) > 0, "el ejemplo debe tener alguna solución factible"
    # El costo es una masa en kg: un A320 ronda las 58-60 toneladas.
    assert -61_000 < float(np.median(vf)) < -55_000, float(np.median(vf))
