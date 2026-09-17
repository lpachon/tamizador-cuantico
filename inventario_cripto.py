#!/usr/bin/env python3
"""
inventario_cripto.py — ¿Qué criptografía usa su sitio, y qué le pasa con Shor?

El paso 1 de cualquier migración post-cuántica es saber qué algoritmo usa cada
sistema. Nadie lo sabe de memoria. Esto lo averigua para un dominio.

    python3 inventario_cripto.py www.suempresa.com
    python3 inventario_cripto.py www.suempresa.com correo.suempresa.com

Y la cuenta que decide si usted ya llegó tarde:

    python3 inventario_cripto.py --mosca 15 7

    (15 = años que debe durar el secreto · 7 = años que tarda su migración)

Requiere: pip install cryptography certifi

Cámara de Comercio de Bogotá · Clúster TEC · Taller de computación cuántica.
Licencia MIT.
"""
from __future__ import annotations

import os
import shutil
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache

# El chequeo de dependencias NO va aquí arriba: salir del proceso al importar
# rompe a quien solo quiera usar `mosca()`, y revienta la recolección de tests.
try:
    import certifi
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
    HAY_TLS = True
except ImportError:                                        # pragma: no cover
    HAY_TLS = False

_FALTA = "Falta una dependencia para analizar dominios. Instale:  pip install cryptography certifi"

A = "═" * 74

# Lo que cae y lo que se salva. La regla es la misma de Bitcoin: lo asimétrico
# tiene estructura que Shor explota; lo simétrico solo cede la raíz a Grover.
CAE = "CAE con Shor"
SALVA = "SE SALVA (doblando el tamaño basta)"
YA_MIGRADO = "YA PROTEGIDO (post-cuántico)"
SIN_MEDIR = "NO MEDIDO"

# Nombres de grupo híbrido que ya incluyen un mecanismo post-cuántico.
_PQ = ("MLKEM", "KYBER", "ML-KEM")

# Firmas post-cuánticas ya normalizadas o en camino. Hoy ninguna autoridad
# pública emite certificados así, pero el día que lo haga esta herramienta no
# puede seguir diciendo que caen.
_PQ_FIRMA = ("MLDSA", "ML-DSA", "DILITHIUM", "SLHDSA", "SLH-DSA", "SPHINCS",
             "FNDSA", "FN-DSA", "FALCON")
_CLASICA = ("RSA", "EC", "ELLIPTIC", "CURVA", "ED25519", "ED448", "DSA", "ECDSA")


def _clasificar(nombre: str, motivo_cae: str, motivo_pq: str):
    """Veredicto a partir de lo medido, no de lo supuesto."""
    n = (nombre or "").upper().replace("_", "")
    if any(k in n for k in _PQ_FIRMA):
        return YA_MIGRADO, motivo_pq
    if any(k in n for k in _CLASICA):
        return CAE, motivo_cae
    return SIN_MEDIR, (f"No reconozco «{nombre}». No lo doy por caído ni por "
                       f"salvado: compruébelo a mano.")


@lru_cache(maxsize=1)
def _openssl_capaz() -> str | None:
    """Un openssl que entienda los grupos híbridos. LibreSSL —el de macOS— no.

    Sin él, el grupo de intercambio de claves NO SE PUEDE MEDIR desde Python:
    el módulo ssl de la biblioteca estándar no expone el grupo negociado.
    """
    candidatos = [shutil.which("openssl"), "/opt/homebrew/bin/openssl",
                  "/usr/local/bin/openssl", "/usr/bin/openssl"]
    for c in candidatos:
        if not c or not os.path.exists(c):
            continue
        try:
            r = subprocess.run([c, "list", "-kem-algorithms"], capture_output=True,
                               text=True, timeout=10)
            if "MLKEM" in r.stdout.upper():
                return c
        except Exception:
            continue
    return None


def _grupo_negociado(host: str, puerto: int = 443) -> str | None:
    """El grupo de intercambio de claves que el servidor acuerda de verdad."""
    ossl = _openssl_capaz()
    if not ossl:
        return None
    try:
        r = subprocess.run(
            [ossl, "s_client", "-connect", f"{host}:{puerto}", "-servername", host],
            input="", capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    for ln in r.stdout.splitlines():
        if "Negotiated TLS1.3 group" in ln:
            return ln.split(":", 1)[1].strip()
    return None


def _año_estimado_qpu() -> str:
    return "década de 2030 (estimaciones serias; nadie tiene una fecha)"


def analizar(host: str, puerto: int = 443, timeout: float = 10.0) -> dict:
    if not HAY_TLS:
        raise RuntimeError(_FALTA)
    ctx = ssl.create_default_context(cafile=certifi.where())
    with socket.create_connection((host, puerto), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as s:
            cifrado, version, _bits = s.cipher()
            der = s.getpeercert(binary_form=True)
    cert = x509.load_der_x509_certificate(der)
    pk = cert.public_key()

    if isinstance(pk, rsa.RSAPublicKey):
        tipo, tam = "RSA", pk.key_size
    elif isinstance(pk, ec.EllipticCurvePublicKey):
        tipo, tam = f"curva elíptica ({pk.curve.name})", pk.curve.key_size
    elif isinstance(pk, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
        tipo, tam = type(pk).__name__.replace("PublicKey", ""), 256
    elif isinstance(pk, dsa.DSAPublicKey):
        tipo, tam = "DSA", pk.key_size
    else:
        tipo, tam = type(pk).__name__, 0

    caduca = cert.not_valid_after_utc
    return {
        "host": host,
        "tls": version,
        "cifrado": cifrado,
        "firma_cert": (cert.signature_algorithm_oid._name or "desconocido"),
        "clave_tipo": tipo,
        "clave_bits": tam,
        "emisor": next((a.value for a in cert.issuer
                        if a.oid == x509.NameOID.COMMON_NAME), "—"),
        "caduca": caduca,
        "dias": (caduca - datetime.now(timezone.utc)).days,
        "grupo": _grupo_negociado(host, puerto),
    }


# `_envolver` vive en tamizador.py: tenerlo duplicado aquí, con una
# implementación ligeramente distinta, era una divergencia esperando a ocurrir.
from tamizador import _envolver as _envolver_base


def _envolver(t: str, n: int = 62) -> list[str]:
    return _envolver_base(t, n)


def informe(d: dict) -> None:
    print(f"\n{A}\nINVENTARIO CRIPTOGRÁFICO — {d['host']}\n{A}")
    print(f"  TLS          : {d['tls']}")
    print(f"  emisor       : {d['emisor']}")
    print(f"  caduca       : {d['caduca']:%Y-%m-%d}  (en {d['dias']} días)\n")

    grupo = d.get("grupo")
    if grupo is None:
        fila_kex = ("Intercambio de claves", "no se pudo medir", SIN_MEDIR,
                    "El módulo ssl de Python no expone el grupo negociado, y no "
                    "hay un openssl con ML-KEM en este equipo. Compruébelo en "
                    "https://pq.cloudflareresearch.com o instale OpenSSL 3.5 o superior.")
    elif any(k in grupo.upper() for k in _PQ):
        fila_kex = ("Intercambio de claves", grupo, YA_MIGRADO,
                    "Grupo híbrido: su proveedor o CDN ya lo migró, probablemente "
                    "sin que usted hiciera nada. Es la parte fácil, y está hecha.")
    else:
        fila_kex = ("Intercambio de claves", grupo, CAE,
                    "Es lo primero que hay que migrar: el tráfico que le copien "
                    "hoy se descifra el día que exista la máquina.")

    filas = [
        fila_kex,
        ("Clave del certificado",
         f"{d['clave_tipo']}, {d['clave_bits']} bits",
         *_clasificar(d["clave_tipo"],
                      "Con la clave privada reconstruida, cualquiera puede "
                      "hacerse pasar por su sitio.",
                      "Certificado con clave post-cuántica: su identidad ya "
                      "está protegida.")),
        ("Firma del certificado",
         d["firma_cert"],
         *_clasificar(d["firma_cert"],
                      "La cadena de confianza completa depende de esto.",
                      "Firma post-cuántica: la cadena de confianza ya resiste.")),
        ("Cifrado simétrico",
         d["cifrado"],
         SALVA,
         "Grover solo quita la raíz cuadrada, y encima no paraleliza. "
         "Doblar el tamaño de la clave sale gratis."),
    ]
    for nombre, valor, veredicto, por_que in filas:
        marca = {CAE: "✗", SIN_MEDIR: "?"}.get(veredicto, "✓")
        print(f"  {marca} {nombre}")
        print(f"      usa      : {valor}")
        print(f"      veredicto: {veredicto}")
        for ln in _envolver(por_que):
            print(f"      {ln}")
        print()
    caen = sum(1 for _, _, v, _ in filas if v == CAE)
    medidas = sum(1 for _, _, v, _ in filas if v != SIN_MEDIR)
    print(A)
    print(f"  Caen {caen} de {medidas} elementos medidos, y son los que dan identidad.")
    if any(v == YA_MIGRADO for _, _, v, _ in filas):
        print("  El intercambio de claves ya está protegido — eso lo hizo su")
        print("  proveedor. Las firmas siguen siendo cosa suya.")
    print("  Es el mismo reparto que en Bitcoin: lo simétrico se salva, lo")
    print("  asimétrico no.")
    print(f"{A}\n")


def mosca(x_años: float, y_años: float) -> None:
    print(f"\n{A}\nLA DESIGUALDAD DE MOSCA\n{A}")
    print(f"  X · el secreto debe durar      : {x_años:g} años")
    print(f"  Y · su migración tardará       : {y_años:g} años")
    print(f"  Z · la máquina llegaría en     : {_año_estimado_qpu()}\n")
    ahora = datetime.now(timezone.utc).year
    suma = x_años + y_años
    horizonte = max(2030 - ahora, 1)          # la fecha más temprana razonable para Z
    print(f"  X + Y = {suma:g} años")
    print(f"  El último dato que cifre sin protección post-cuántica seguirá")
    print(f"  siendo sensible hasta  {ahora + suma:.0f}.")
    print(f"  La máquina podría existir ya en  {ahora + horizonte}.\n")
    if suma > horizonte:
        print("  VEREDICTO: YA LLEGÓ TARDE.")
        print(f"             Hay una ventana de {suma - horizonte:.0f} años en la que sus datos")
        print("             quedan expuestos y usted ya no puede hacer nada al respecto,")
        print("             porque se cifraron antes de terminar la migración.")
        print("             Empezar no es una decisión de 2030: es de este año.")
    else:
        print("  VEREDICTO: margen, pero estrecho.")
        print("             Rehaga la cuenta con el dato de vida útil MÁS LARGA que")
        print("             tenga, no con el promedio. Basta un secreto que dure de más.")
    print(f"{A}\n")


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "--mosca":
        mosca(float(argv[1]), float(argv[2]))
        return 0
    if not argv:
        print(__doc__)
        return 1
    for host in argv:
        try:
            informe(analizar(host))
        except Exception as e:
            print(f"\n  {host}: no se pudo analizar — {type(e).__name__}: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
