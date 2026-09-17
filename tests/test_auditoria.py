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
    assert "1,000" in m2.valor or "0,99" in m2.valor, m2.valor


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


def test_c11_la_medida_1_declara_que_es_de_compuertas():
    """C11: el título prometía «el hardware de hoy» y solo mide el de compuertas.

    Con 5.760 qubits físicos en un D-Wave Pegasus, un umbral de 30 qubits sin
    calificar invita a la objeción obvia. El alcance tiene que estar en el
    título, no solo en un comentario del código.
    """
    from tamizador import ejemplo_mezcla_de_produccion

    v = tamizar(ejemplo_mezcla_de_produccion())
    m1 = v.medidas[0]
    assert "compuertas" in m1.pregunta, f"la medida 1 no declara su alcance: {m1.pregunta!r}"
    assert "annealing" in m1.comentario, "el comentario no remite al caso del annealing"


def test_c12_la_linea_base_no_se_sale_de_las_cotas():
    """C12: COBYLA sin cotas proponía puntos que el usuario no puede alcanzar.

    En la plantilla del taller llegaba a sugerir una producción NEGATIVA, y
    anunciaba su costo como «la cifra a batir». Aquí el óptimo está fuera de la
    caja a propósito: la línea base tiene que quedarse en el borde.
    """
    pytest.importorskip("scipy", reason="el refinamiento clásico usa COBYLA de scipy")
    p = Problema(
        nombre="óptimo fuera de la caja",
        cotas=[(0.0, 10.0)] * 4,
        objetivo=lambda x: float(np.sum((x - 11.0) ** 2)),
        ruido_absoluto=0.5,
    )
    v = tamizar(p, imprimir=False)
    crudo = v.medidas[4].valor.split(" en ")[0]
    mejor = float(crudo.replace(".", "").replace(",", "."))
    alcanzable = float(np.sum((np.full(4, 10.0) - 11.0) ** 2))   # la esquina (10,10,10,10)
    assert mejor == pytest.approx(alcanzable, rel=1e-6), (
        f"la cifra a batir ({mejor}) no es alcanzable dentro de las cotas "
        f"(lo mejor posible es {alcanzable})")


def test_c13_todos_los_numeros_se_escriben_igual():
    """C13: el eco de parámetros escribía 32.768 y la medida 3, 32,768.

    El mismo número con dos grafías en una sola ejecución. Peor: la medida 4
    imprimía «dispersión = 151.5 · umbral > 5.229», que en castellano se lee
    como un suspenso y sin embargo marcaba PASA.
    """
    from tamizador import _ent, _fij, _num, _pct
    assert _ent(32768) == "32.768"
    assert _num(1500.0) == "1.500"          # no «1,500», que se leería 1,5
    assert _fij(-292.65462, 4) == "-292,6546"
    assert _pct(0.001, 1) == "0,1 %"
    assert _pct(0.574310, 4) == "57,4310 %"


def test_c15_el_spearman_de_repuesto_promedia_empates():
    """C15: `argsort(argsort(z))` le inventa un orden a un vector constante.

    Sobre bits hay muchísimos empates, así que la rama sin scipy y la rama con
    scipy daban números distintos para los mismos datos.
    """
    from tamizador import _spearman
    rng = np.random.default_rng(0)
    y = rng.normal(size=400)
    pred = np.round(rng.normal(size=400) * 0.4)        # solo 4 valores: puros empates
    esperado = pytest.importorskip("scipy.stats").spearmanr(pred, y).statistic
    assert _spearman(pred, y) == pytest.approx(float(esperado), abs=1e-12)
    assert np.isnan(_spearman(np.ones(400), y)), "un vector constante no tiene orden"


@pytest.mark.filterwarnings("ignore:.*input array is constant.*")
def test_c15b_la_medida_2_da_lo_mismo_con_y_sin_scipy(monkeypatch):
    """No basta con que el repuesto sea correcto: la medida tiene que usarlo.

    Se fuerza la rama sin scipy y se compara el ρ contra el de la rama con
    scipy sobre el mismo problema. Si divergen, dos usuarios con instalaciones
    distintas leen números distintos del mismo caso.
    """
    pytest.importorskip("scipy")
    import tamizador as T

    # Objetivo constante sobre la región factible: el ajuste es degenerado y
    # `pred` sale constante. scipy devuelve NaN y la medida se declara NO
    # CONCLUYENTE; el repuesto viejo le inventaba un orden y la marcaba FALLA.
    p = T.Problema(nombre="objetivo constante", cotas=[(0.0, 1.0)] * 4,
                   objetivo=lambda x: 5.0, ruido_absoluto=0.1)

    con = T.tamizar(p, imprimir=False).medidas[1]
    monkeypatch.setattr(T, "HAY_SCIPY", False)
    sin = T.tamizar(p, imprimir=False).medidas[1]

    assert con.pasa is None, "con scipy debería ser no concluyente"
    assert sin.pasa is con.pasa, (
        f"el veredicto de la medida 2 diverge: con scipy pasa={con.pasa}, "
        f"sin scipy pasa={sin.pasa} ({sin.valor!r})")


def test_la_medida_1_cuenta_los_qubits_y_la_medida_3_el_rendimiento():
    """Las medidas 1 y 3 no tenían prueba propia: se daban por buenas porque
    los ejemplos salían bien. Aquí se comprueban contra aritmética a mano."""
    from tamizador import _m1_cabe, _m3_rareza

    p = Problema(nombre="x", cotas=[(0.0, 1.0)] * 7, objetivo=lambda v: 0.0,
                 bits_por_variable=3)
    m1 = _m1_cabe(p)
    assert "21 qubits" in m1.valor, m1.valor          # 7 variables × 3 bits
    assert m1.pasa is True                            # 21 ≤ 30
    assert _m1_cabe(Problema(nombre="x", cotas=[(0.0, 1.0)] * 11,
                             objetivo=lambda v: 0.0, bits_por_variable=3)).pasa is False

    m3 = _m3_rareza(p, 10_000, 5)                     # 0,05 % < 0,1 %
    assert m3.pasa is False, m3.valor
    assert "0,0500 %" in m3.valor, m3.valor
    assert "(5 de 10.000)" in m3.valor, m3.valor
    assert _m3_rareza(p, 10_000, 500).pasa is True    # 5 % ≥ 0,1 %
