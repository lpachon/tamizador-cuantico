"""La herramienta del otro reloj. Lo que se puede probar sin red."""
import pytest

import inventario_cripto as inv


def test_mosca_avisa_cuando_la_suma_supera_el_horizonte(capsys):
    inv.mosca(15, 7)
    salida = capsys.readouterr().out
    assert "YA LLEGÓ TARDE" in salida
    assert "22 años" in salida


def test_mosca_no_alarma_cuando_hay_margen(capsys):
    inv.mosca(1, 1)
    assert "margen" in capsys.readouterr().out


def test_importar_no_mata_el_proceso_sin_dependencias():
    """Importar el módulo nunca debe llamar a sys.exit: rompería a quien solo
    quiera la calculadora de Mosca, y revienta la recolección de tests."""
    assert hasattr(inv, "HAY_TLS")
    assert callable(inv.mosca)


@pytest.mark.skipif(not inv.HAY_TLS, reason="requiere cryptography y certifi")
def test_un_dominio_inexistente_no_revienta(capsys):
    assert inv.main(["no-existe-esto-98765.invalid"]) == 0
    assert "no se pudo analizar" in capsys.readouterr().out


# ── C9 · el intercambio de claves se mide, no se supone ───────────────
def test_c9_el_veredicto_del_intercambio_no_esta_cableado():
    """Antes la fila del intercambio de claves llevaba «CAE con Shor» escrito a
    mano, sin medir nada. Daba el veredicto equivocado incluso en el sitio de
    demostración post-cuántica de Cloudflare."""
    import inspect
    src = inspect.getsource(inv.informe)
    assert "fila_kex" in src, "la fila debe construirse a partir de lo medido"
    assert "d.get(\"grupo\")" in src, "debe leer el grupo negociado"


def test_c9_un_grupo_hibrido_no_se_marca_como_caido():
    """Si el grupo negociado lleva ML-KEM, el veredicto no puede ser CAE."""
    assert any("MLKEM" in k or "ML-KEM" in k for k in inv._PQ)
    assert inv.YA_MIGRADO != inv.CAE


def test_c9_sin_openssl_capaz_se_declara_no_medido():
    """Sin un openssl con ML-KEM no se puede medir el grupo — y entonces hay
    que decirlo, no asumir el peor caso ni el mejor."""
    assert inv.SIN_MEDIR == "NO MEDIDO"
    assert inv._grupo_negociado("no-existe-esto-98765.invalid") is None


# ── C10 · los veredictos del certificado también se derivan ────────────
def test_c10_una_firma_post_cuantica_no_se_marca_como_caida():
    """Los veredictos del certificado estaban cableados a CAE. Hoy ninguna
    autoridad pública emite firmas post-cuánticas, pero el día que lo haga la
    herramienta no puede seguir diciendo que caen."""
    for nombre in ("ML-DSA-65", "SLH-DSA-SHA2-128s", "sphincs-sha2-128s", "Falcon-512"):
        v, _ = inv._clasificar(nombre, "cae", "protegido")
        assert v == inv.YA_MIGRADO, f"{nombre} → {v}"


def test_c10_lo_clasico_sigue_cayendo():
    for nombre in ("RSA", "curva elíptica (secp256r1)", "ecdsa-with-SHA384", "Ed25519"):
        v, _ = inv._clasificar(nombre, "cae", "protegido")
        assert v == inv.CAE, f"{nombre} → {v}"


def test_c10_lo_desconocido_no_se_da_por_supuesto():
    """Ni caído ni salvado: no medido. Es la lección de C9."""
    v, motivo = inv._clasificar("algoritmo-del-futuro-2040", "cae", "protegido")
    assert v == inv.SIN_MEDIR
    assert "compruébelo a mano" in motivo
