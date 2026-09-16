"""Los cuatro ejemplos incluidos, cada uno fallando por un motivo distinto.

Son los que se enseñan en el taller y los que cita el README: si cambian de
veredicto sin querer, esto salta.
"""
import pytest

from tamizador import (ejemplo_ascenso_restringido, ejemplo_asignacion_grande,
                       ejemplo_mezcla_de_produccion, ejemplo_secuencia_labs,
                       tamizar)


def _fallan(v):
    return [i for i, m in enumerate(v.medidas, 1) if m.pasa is False]


def test_el_ascenso_falla_por_rareza_y_por_planitud():
    v = tamizar(ejemplo_ascenso_restringido(), imprimir=False)
    assert not v.go
    assert _fallan(v) == [3, 4]


def test_la_mezcla_de_produccion_supera_el_filtro():
    v = tamizar(ejemplo_mezcla_de_produccion(), imprimir=False)
    assert v.go, f"falla en {_fallan(v)}"


def test_labs_falla_solo_en_la_traduccion_a_qubo():
    """Tiene estructura de sobra —por eso QAOA le gana— pero su objetivo es
    cuártico y no cabe en un QUBO sin variables auxiliares."""
    v = tamizar(ejemplo_secuencia_labs(), imprimir=False)
    assert _fallan(v) == [2]


def test_labs_encuentra_el_optimo_conocido():
    """Para N=16 el óptimo de LABS es E = 24 (factor de mérito 5,33). Si la
    línea base clásica deja de encontrarlo, algo se rompió en el muestreo."""
    v = tamizar(ejemplo_secuencia_labs(), imprimir=False)
    mejor = float(v.medidas[4].valor.split(" en ")[0].replace(",", ""))
    assert mejor == pytest.approx(24.0, abs=1e-6), mejor


def test_la_asignacion_grande_falla_solo_por_tamano():
    """Bien planteado en todo lo demás: se va a 90 qubits y ahí se acaba."""
    v = tamizar(ejemplo_asignacion_grande(), imprimir=False)
    assert _fallan(v) == [1]
    assert "90 qubits" in v.medidas[0].valor


def test_la_linea_base_clasica_nunca_aprueba_ni_suspende():
    """Es informativa por diseño: un filtro que siempre dice NO-GO es inútil."""
    for hacer in (ejemplo_ascenso_restringido, ejemplo_mezcla_de_produccion,
                  ejemplo_secuencia_labs, ejemplo_asignacion_grande):
        v = tamizar(hacer(), imprimir=False)
        assert v.medidas[4].pasa is None
        assert v.medidas[4] not in v.decisivas


# ── los ejemplos se explican al ejecutarse ────────────────────────────
@pytest.mark.parametrize("hacer", [ejemplo_ascenso_restringido, ejemplo_mezcla_de_produccion,
                                   ejemplo_secuencia_labs, ejemplo_asignacion_grande])
def test_cada_ejemplo_describe_su_tarea_y_etiqueta_sus_variables(hacer):
    p = hacer()
    assert len(p.descripcion) > 80, "la descripción debe explicar qué se decide"
    assert p.variables is not None and len(p.variables) == p.n_variables


def test_el_informe_imprime_los_parametros(capsys):
    """Lo que la herramienta da por supuesto tiene que decirse en voz alta:
    ahí se cazan las cotas mal puestas y la resolución absurda."""
    tamizar(ejemplo_mezcla_de_produccion())
    salida = capsys.readouterr().out
    for esperado in ("QUÉ SE DECIDE", "VARIABLES DE DECISIÓN", "CODIFICACIÓN",
                     "RUIDO DEL MODELO", "MUESTREO", "línea A"):
        assert esperado in salida, esperado


def test_los_numeros_van_en_castellano(capsys):
    """Punto de millar y coma decimal: «262,144» se lee mal en español."""
    tamizar(ejemplo_ascenso_restringido())
    assert "262.144 puntos" in capsys.readouterr().out
