#!/usr/bin/env python3
"""
tamizador.py — ¿Merece la pena llevar SU problema a un computador cuántico?

Cinco medidas, cinco umbrales, un veredicto. Corre en un portátil, en minutos,
sin cuenta de IBM y sin hardware cuántico.

QUBO, que aparece por todas partes aquí, es la única forma de problema que el
hardware actual acepta: Quadratic Unconstrained Binary Optimization. Variables
que solo valen 0 o 1, términos de a uno y de a dos, y ninguna restricción — las
suyas hay que meterlas dentro del objetivo como penalizaciones.

IMPORTANTE — lo que este filtro es y lo que no: elimina, no selecciona. Sus
medidas son condiciones NECESARIAS para que un algoritmo cuántico pueda aportar
algo. Superarlas no predice una victoria; solo descarta las razones más comunes
por las que no la habría. A septiembre de 2026 no hay ventaja cuántica
demostrada en ningún problema de optimización empresarial. Véase la sección
«Dónde sí hay caso» del README.

Uso rápido
----------
    python3 tamizador.py                 # corre los dos ejemplos incluidos

Uso sobre su propio problema
----------------------------
    from tamizador import Problema, tamizar

    def mi_objetivo(x):
        # x es un vector de numpy con sus variables de decisión.
        # Devuelva el costo (menor es mejor), o float("nan") si x viola
        # alguna restricción. NaN = no factible. Eso es todo.
        ...

    tamizar(Problema(
        nombre="Asignación de flota",
        cotas=[(0, 10), (0, 10), (0, 24)],   # una pareja (min, max) por variable
        objetivo=mi_objetivo,
        bits_por_variable=3,
        ruido_del_modelo=0.01,               # incertidumbre relativa de SU modelo
    ))

Requiere numpy. Usa scipy si está disponible (mejor muestreo y refinamiento
clásico); si no está, funciona igual con muestreo aleatorio uniforme.

Cámara de Comercio de Bogotá · Clúster TEC · Taller de computación cuántica.
Licencia MIT — úselo, cópielo y modifíquelo sin pedir permiso.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

try:
    from scipy.optimize import minimize
    from scipy.stats import qmc, spearmanr
    HAY_SCIPY = True
except ImportError:                                    # pragma: no cover
    HAY_SCIPY = False

# ── Umbrales de descarte ────────────────────────────────────────────────
# Calibrados para el hardware disponible en 2026. Suba QUBITS_MAX a medida
# que el hardware mejore; el resto son propiedades del problema, no de la
# máquina, y no deberían moverse.
QUBITS_MAX = 30          # más allá, no cabe en hardware que usted pueda usar hoy
RHO_MIN = 0.90           # fidelidad mínima del sustituto cuadrático (QUBO)
RENDIMIENTO_MIN = 1e-3   # 0,1 % de muestras factibles
MARGEN_PLANITUD = 3.0    # la dispersión debe superar 3× el ruido de su modelo
FILAS_AJUSTE = 8_000     # tope de filas para el ajuste de la medida 2


@dataclass
class Problema:
    """Su problema de optimización, descrito en lo mínimo indispensable."""
    nombre: str
    cotas: list[tuple[float, float]]
    objetivo: Callable[[np.ndarray], float]
    descripcion: str = ""              # qué decisión se está tomando
    variables: list[str] | None = None  # etiqueta de cada variable, en orden
    bits_por_variable: int = 3
    ruido_del_modelo: float = 0.01     # incertidumbre RELATIVA (1 % por defecto)
    ruido_absoluto: float | None = None  # incertidumbre en unidades del objetivo
    n_muestras: int = 20_000
    semilla: int = 42

    @property
    def n_variables(self) -> int:
        return len(self.cotas)


@dataclass
class Medida:
    """Una de las cinco preguntas, ya respondida con un número."""
    pregunta: str
    valor: str
    umbral: str
    pasa: bool | None          # None = informativa, no cuenta para el veredicto
    comentario: str = ""


@dataclass
class Veredicto:
    problema: str
    medidas: list[Medida] = field(default_factory=list)
    segundos: float = 0.0

    @property
    def decisivas(self) -> list[Medida]:
        return [m for m in self.medidas if m.pasa is not None]

    @property
    def n_pasa(self) -> int:
        return sum(bool(m.pasa) for m in self.decisivas)

    @property
    def go(self) -> bool:
        return all(m.pasa for m in self.decisivas)


def _num(x: float, dec: int = 4) -> str:
    """Número en castellano: punto de millar y coma decimal."""
    t = f"{x:,.{dec}g}"
    return t.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")


# ── Muestreo ────────────────────────────────────────────────────────────
def _muestrear(p: Problema) -> np.ndarray:
    lo = np.array([c[0] for c in p.cotas], dtype=float)
    hi = np.array([c[1] for c in p.cotas], dtype=float)
    if HAY_SCIPY:
        m = int(np.ceil(np.log2(max(2, p.n_muestras))))
        u = qmc.Sobol(d=p.n_variables, scramble=True, seed=p.semilla).random_base2(m)
    else:
        u = np.random.default_rng(p.semilla).random((p.n_muestras, p.n_variables))
    return lo + u * (hi - lo)


def _evaluar(p: Problema, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (X_factible, costo_factible). NaN o inf = no factible."""
    vals = np.array([p.objetivo(x) for x in X], dtype=float)
    ok = np.isfinite(vals)
    return X[ok], vals[ok]


# ── Las cinco medidas ───────────────────────────────────────────────────
def _m1_cabe(p: Problema) -> Medida:
    q = p.n_variables * p.bits_por_variable
    # Profundidad orientativa de un QAOA p=2 sobre topología de anillo,
    # una vez transpilado a conectividad heavy-hex.
    prof = 2 * (3 * q + 8)
    return Medida(
        "¿Cabe en el hardware de hoy?",
        f"{q} qubits · profundidad ≈ {prof}",
        f"≤ {QUBITS_MAX} qubits",
        q <= QUBITS_MAX,
        f"{p.n_variables} variables × {p.bits_por_variable} bits. "
        f"Bajar un bit por variable ahorra {p.n_variables} qubits y pierde resolución.",
    )


def _codificar_bits(p: Problema, X: np.ndarray) -> np.ndarray:
    """Los bits que un QUBO vería de verdad.

    Cada variable continua se discretiza en `bits_por_variable` niveles y se
    escribe en binario. Es exactamente la codificación que exige el hardware:
    la optimización no ocurre sobre x, ocurre sobre estos bits.
    """
    b = p.bits_por_variable
    niveles = 2 ** b - 1
    columnas = []
    for j, (lo, hi) in enumerate(p.cotas):
        u = np.clip((X[:, j] - lo) / max(hi - lo, 1e-12), 0.0, 1.0)
        n = np.rint(u * niveles).astype(np.int64)
        for k in range(b):
            columnas.append(((n >> k) & 1).astype(float))
    return np.column_stack(columnas)


def _m2_estructura(p: Problema, Xf: np.ndarray, vf: np.ndarray) -> Medida:
    """¿Una forma cuadrática sobre los bits conserva el orden de las soluciones?

    Un QUBO es, literalmente, una cuadrática sobre variables binarias. Así que
    el ajuste se hace sobre los bits codificados —no sobre las coordenadas
    continuas—, y sin términos q² porque para un bit q² = q. Si esto no
    reproduce el orden, la traducción a QUBO pierde lo que usted optimiza.

    Ojo con la lectura: un ρ bajo dice «no cabe en un QUBO tal cual», no «no
    tiene estructura». LABS, por ejemplo, es cuártico y da ρ ≈ 0, y aun así es
    de los pocos problemas con evidencia de ventaja para QAOA — traducirlo
    exige variables auxiliares.
    """
    PREGUNTA = "¿Sobrevive la traducción a QUBO?"
    UMBRAL = f"ρ ≥ {RHO_MIN}"
    if len(vf) < 30:
        return Medida(PREGUNTA, "no se pudo medir", UMBRAL, None,
                      "Hubo muy pocas soluciones factibles para ajustar el "
                      "sustituto. No es un suspenso: es que la medida 3 ya "
                      "decidió el caso.")

    Q = _codificar_bits(p, Xf)
    # Submuestreo: el ajuste no necesita millones de filas y sí necesita caber
    # en memoria cuando hay muchos bits.
    if len(Q) > FILAS_AJUSTE:
        idx = np.random.default_rng(p.semilla).choice(len(Q), FILAS_AJUSTE, replace=False)
        Q, y = Q[idx], vf[idx]
    else:
        y = vf

    K = Q.shape[1]
    n_terminos = 1 + K + K * (K - 1) // 2          # sin q², que para un bit es q
    if n_terminos > len(Q) // 3:
        return Medida(PREGUNTA, f"no se pudo medir ({K} bits → {n_terminos:,} términos)",
                      UMBRAL, None,
                      f"Una cuadrática sobre {K} bits tiene {n_terminos:,} términos y "
                      f"solo hay {len(Q):,} muestras: el ajuste sería memoria, no "
                      f"estructura. Reduzca bits por variable o el número de variables.")

    cols = [np.ones(len(Q)), *Q.T]
    for i in range(K):
        for j in range(i + 1, K):
            cols.append(Q[:, i] * Q[:, j])
    A = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    if HAY_SCIPY:
        rho = float(spearmanr(pred, y).statistic)
    else:
        r = lambda z: np.argsort(np.argsort(z))
        rho = float(np.corrcoef(r(pred), r(y))[0, 1])
    if not np.isfinite(rho):
        return Medida(PREGUNTA, "no se pudo medir", UMBRAL, None,
                      "El objetivo no varía entre las soluciones factibles.")
    return Medida(
        PREGUNTA,
        f"ρ de Spearman = {rho:.3f}",
        UMBRAL,
        rho >= RHO_MIN,
        f"Ajustado sobre los {K} bits que vería el QUBO, con {n_terminos:,} "
        f"términos. Un ρ bajo significa «no cabe en un QUBO tal cual», no «no "
        f"tiene estructura».",
    )


def _m3_rareza(p: Problema, n_total: int, n_factible: int) -> Medida:
    r = n_factible / max(1, n_total)
    return Medida(
        "¿Las soluciones válidas son raras?",
        f"{r:.4%}  ({n_factible:,} de {n_total:,})",
        f"≥ {RENDIMIENTO_MIN:.1%}",
        r >= RENDIMIENTO_MIN,
        "Si son una fracción ínfima del espacio, ninguna concentración de "
        "probabilidad alcanzable hoy las encuentra.",
    )


def _m4_planitud(p: Problema, vf: np.ndarray) -> Medida:
    """¿La dispersión del objetivo supera el ruido de su propio modelo?

    Se mide en unidades del objetivo, no en porcentaje de la mediana. Dividir
    por la mediana parece natural hasta que el objetivo cruza el cero: entonces
    el mismo problema pasa o falla según dónde esté el origen. Si usted no
    declara `ruido_absoluto`, se deriva del relativo — y si eso no es
    interpretable, la medida lo dice en vez de inventarse un número.
    """
    PREGUNTA = "¿El costo es plano?"
    if len(vf) < 10:
        return Medida(PREGUNTA, "no se pudo medir", "—", None,
                      "Hubo muy pocas soluciones factibles para medir la "
                      "dispersión de forma fiable.")
    p5, p50, p95 = np.percentile(vf, [5, 50, 95])
    disp = float(abs(p95 - p5))

    if p.ruido_absoluto is not None:
        ruido = float(p.ruido_absoluto)
        origen = "declarado"
    else:
        # El relativo solo tiene sentido si la mediana domina a la dispersión.
        if abs(p50) < disp:
            return Medida(
                PREGUNTA, f"dispersión {disp:,.4g} en unidades del objetivo",
                "—", None,
                "Su objetivo cruza el cero o ronda el cero, así que un ruido "
                "RELATIVO no es interpretable aquí. Declare `ruido_absoluto` "
                "en unidades del objetivo y vuelva a tamizar.")
        ruido = float(p.ruido_del_modelo * abs(p50))
        origen = f"{p.ruido_del_modelo:.1%} de la mediana"

    necesario = MARGEN_PLANITUD * ruido
    return Medida(
        PREGUNTA,
        f"dispersión = {disp:,.4g}  (ruido {ruido:,.4g}, {origen})",
        f"> {necesario:,.4g}  ({MARGEN_PLANITUD:.0f}× su ruido)",
        disp > necesario,
        "Si todas las soluciones válidas valen casi lo mismo, concentrar "
        "probabilidad sobre ellas no mejora el objetivo. Se compara en "
        "unidades del objetivo, no en porcentaje.",
    )


def _m5_clasico(p: Problema, Xf: np.ndarray, vf: np.ndarray, t_muestreo: float) -> Medida:
    """Línea base clásica: lo mejor del muestreo, refinado localmente."""
    if len(vf) == 0:
        return Medida("Línea base clásica", "no encontró nada", "—", None,
                      "Sin soluciones factibles no hay línea base que batir.")
    t0 = time.time()
    mejor = float(vf.min())
    x0 = Xf[int(np.argmin(vf))]
    if HAY_SCIPY:
        # El refinamiento corre en coordenadas normalizadas a [0,1]. Con un
        # rhobeg fijo en unidades del problema, una variable que va de 150 a 250
        # apenas se movería: el paso inicial sería mil veces menor que su rango.
        lo = np.array([c[0] for c in p.cotas], dtype=float)
        ancho = np.array([max(c[1] - c[0], 1e-12) for c in p.cotas], dtype=float)

        def seguro(u):
            v = p.objetivo(lo + np.asarray(u) * ancho)
            return v if np.isfinite(v) else 1e18

        u0 = (x0 - lo) / ancho
        r = minimize(seguro, u0, method="COBYLA",
                     options={"maxiter": 600, "rhobeg": 0.08})
        if np.isfinite(r.fun) and r.fun < 1e17:
            mejor = min(mejor, float(r.fun))
    t = time.time() - t0 + t_muestreo
    return Medida(
        "Línea base clásica",
        f"{mejor:,.4f} en {t:.2f} s",
        "la cifra a batir",
        None,                        # informativa: no aprueba ni suspende
        "Esta es la cifra que cualquier propuesta cuántica tiene que superar. "
        "Si nadie se la muestra batida, no hay caso que discutir.",
    )


# ── Orquestación e informe ──────────────────────────────────────────────
def tamizar(p: Problema, imprimir: bool = True) -> Veredicto:
    t0 = time.time()
    X = _muestrear(p)
    t_muestreo_0 = time.time()
    Xf, vf = _evaluar(p, X)
    t_muestreo = time.time() - t_muestreo_0

    v = Veredicto(p.nombre)
    v.medidas = [
        _m1_cabe(p),
        _m2_estructura(p, Xf, vf),
        _m3_rareza(p, len(X), len(vf)),
        _m4_planitud(p, vf),
        _m5_clasico(p, Xf, vf, t_muestreo),
    ]
    v.segundos = time.time() - t0
    if imprimir:
        _informe(v, p, len(X))
    return v


def _parametros(p: Problema, n_evaluadas: int) -> None:
    """Todo lo que la herramienta va a dar por supuesto, dicho en voz alta.

    Media docena de errores de uso se cazan aquí: unas cotas demasiado
    estrechas, una resolución absurda o un ruido mal declarado saltan a la
    vista antes de leer un solo veredicto.
    """
    if p.descripcion:
        print("  QUÉ SE DECIDE")
        for ln in _envolver(p.descripcion, 70):
            print(f"    {ln}")
        print()

    print("  VARIABLES DE DECISIÓN")
    niveles = 2 ** p.bits_por_variable
    etiquetas = p.variables or [f"variable {i + 1}" for i in range(p.n_variables)]
    if p.n_variables > 8 and len(set(p.cotas)) == 1:
        lo, hi = p.cotas[0]
        paso = (hi - lo) / (niveles - 1) if niveles > 1 else 0.0
        print(f"    {p.n_variables} variables, todas con el mismo rango: "
              f"{_num(lo)} a {_num(hi)}   paso {_num(paso)}")
        if p.variables:
            print(f"    {etiquetas[0]} … {etiquetas[-1]}")
        print()
        _resto_parametros(p, niveles, n_evaluadas)
        return
    for i, ((lo, hi), et) in enumerate(zip(p.cotas, etiquetas, strict=False), 1):
        paso = (hi - lo) / (niveles - 1) if niveles > 1 else 0.0
        rango = f"{_num(lo)} a {_num(hi)}"
        print(f"    {i}. {et[:32]:<32s} {rango:>20s}   paso {_num(paso)}")
    if p.variables and len(p.variables) != p.n_variables:
        print(f"    (ojo: {len(p.variables)} etiquetas para {p.n_variables} variables)")
    print()

    _resto_parametros(p, niveles, n_evaluadas)


def _resto_parametros(p: Problema, niveles: int, n_evaluadas: int) -> None:
    q = p.n_variables * p.bits_por_variable
    b = "bit" if p.bits_por_variable == 1 else "bits"
    print(f"  CODIFICACIÓN      {p.bits_por_variable} {b} por variable → "
          f"{niveles} niveles cada una → {q} qubits")
    if p.ruido_absoluto is not None:
        print(f"  RUIDO DEL MODELO  {_num(p.ruido_absoluto)} en unidades del objetivo (declarado)")
    else:
        print(f"  RUIDO DEL MODELO  {p.ruido_del_modelo:.2%} relativo a la mediana (derivado)")
    fuente = "Sobol" if HAY_SCIPY else "aleatorio uniforme"
    print(f"  MUESTREO          {_num(n_evaluadas, 12)} puntos ({fuente}, semilla {p.semilla})")
    if n_evaluadas != p.n_muestras:
        print(f"                    pidió {_num(p.n_muestras, 12)}; se redondea a la "
              f"potencia de dos siguiente")
    print()


def _informe(v: Veredicto, p: Problema, n_evaluadas: int) -> None:
    A = "═" * 78
    print(f"\n{A}\nTAMIZADOR CUÁNTICO — {v.problema}\n{A}\n")
    _parametros(p, n_evaluadas)
    print(f"{A}\n  LAS CINCO MEDIDAS          "
          f"({'con' if HAY_SCIPY else 'sin'} scipy · {v.segundos:.1f} s)\n{A}\n")
    for i, m in enumerate(v.medidas, 1):
        marca = "INFO " if m.pasa is None else ("PASA " if m.pasa else "FALLA")
        print(f"  {i}. [{marca}] {m.pregunta}")
        print(f"            medido : {m.valor}")
        print(f"            umbral : {m.umbral}")
        for ln in _envolver(m.comentario, 62):
            print(f"            {ln}")
        print()
    print(A)
    if v.go:
        print("VEREDICTO: NO DESCARTADO. Supera el filtro — que es una condición\n"
              "           NECESARIA, no suficiente. No significa que la cuántica\n"
              "           vaya a ganar: significa que todavía no se puede afirmar\n"
              "           que no. El siguiente paso es formular el QUBO y medirlo\n"
              "           contra un control aleatorio, antes de gastar un peso en QPU.")
    else:
        fallan = [str(i) for i, m in enumerate(v.medidas, 1)
                  if m.pasa is not None and not m.pasa]
        print(f"VEREDICTO: NO-GO. Falla en {', '.join(fallan)} "
              f"({v.n_pasa} de {len(v.decisivas)} superadas).")
        print("           Su dinero rinde más en el modelo clásico. Vuelva a "
              "tamizar\n           si cambia la codificación o mejora el hardware.")
    print(f"{A}\n")


def _envolver(t: str, n: int) -> list[str]:
    out, ln = [], ""
    for w in t.split():
        if len(ln) + len(w) + 1 > n and ln:
            out.append(ln); ln = w
        else:
            ln = f"{ln} {w}".strip()
    if ln:
        out.append(ln)
    return out


# ── Dos ejemplos que corren tal cual ────────────────────────────────────
def ejemplo_ascenso_restringido() -> Problema:
    """Ascenso de una aeronave con restricciones estrechas, en cuatro variables.

    Un problema de manual, pero con las unidades cuadradas: el ascenso se
    integra en metros y segundos, y el crucero usa Bréguet con un consumo
    específico realista. Región factible diminuta y costo casi plano dentro de
    ella. Debe salir NO-GO, y por los motivos correctos.

    Variables: v1, v2 [m/s] y γ1, γ2 [rad] al principio y al final del ascenso.
    """
    DH = 7_925.0          # m      — de 10.000 a 36.000 pies
    L = 400_000.0         # m      — alcance de la misión
    V_CRZ = 236.0         # m/s    — velocidad de crucero (Mach 0,80 en altura)
    M0 = 60_000.0         # kg     — masa al entrar en ascenso
    VZ_MIN = 2.54         # m/s    — 500 pies por minuto
    C_ESP = 1.67e-4       # 1/s    — consumo específico del turbofán
    L_D = 17.0            # –      — finura máxima
    CI = 0.5              # kg/s   — índice de coste

    def costo(x):
        v1, v2, g1, g2 = x
        if not (0.02 <= g1 <= 0.20 and 0.02 <= g2 <= 0.20):
            return float("nan")
        if v2 <= v1 or v2 - v1 > 4.0:                    # aceleración admisible
            return float("nan")
        if v2 > V_CRZ:                                   # no rebasar el crucero
            return float("nan")
        # Velocidad vertical dentro de una banda operativa estrecha.
        for v, g in ((v1, g1), (v2, g2)):
            vz = v * np.sin(g)
            if not (VZ_MIN <= vz <= VZ_MIN + 2.6):     # banda operativa estrecha
                return float("nan")

        v_m, g_m = 0.5 * (v1 + v2), 0.5 * (g1 + g2)      # promedios del tramo
        s_asc = DH / np.tan(g_m)                          # m
        t_asc = DH / (v_m * np.sin(g_m))                  # s
        if s_asc >= L:                                    # el ascenso no cabe
            return float("nan")

        m_asc = M0 - C_ESP * 0.22 * M0 * t_asc / 3600.0   # kg quemados subiendo
        R = L - s_asc                                     # m de crucero restantes
        m_fin = m_asc * np.exp(-R * C_ESP / (V_CRZ * L_D))
        t_total = t_asc + R / V_CRZ                       # s
        return float(-m_fin + CI * t_total)

    return Problema("Ascenso con restricciones estrechas",
                    descripcion="Elegir la velocidad y el ángulo de subida al principio y al "
                                "final de un ascenso de 10.000 a 36.000 pies, para llegar al "
                                "crucero gastando el menor combustible posible. Todo lo demás "
                                "—masa, tiempo, distancia— queda determinado por esos cuatro "
                                "números.",
                    variables=["v1 · velocidad inicial [m/s]", "v2 · velocidad final [m/s]",
                               "γ1 · ángulo inicial [rad]", "γ2 · ángulo final [rad]"],
                    cotas=[(150.0, 250.0), (150.0, 250.0), (0.005, 0.20), (0.005, 0.20)],
                    objetivo=costo, bits_por_variable=3,
                    # 150 kg: a esa escala mueven la respuesta las decisiones
                    # de modelado (qué definición de costo se elige, qué
                    # aproximación del crucero). Por debajo de eso, «mejorar»
                    # el objetivo no significa nada.
                    ruido_absoluto=150.0,
                    n_muestras=200_000)


def ejemplo_mezcla_de_produccion() -> Problema:
    """Restricciones holgadas y objetivo con relieve real.

    El contraste: mismo tamaño, pero región factible amplia y costo con
    pendiente. Sale NO DESCARTADO — lo que NO quiere decir que la cuántica
    fuese a ganarle aquí a un solver clásico, que resolvería esto en
    microsegundos. Quiere decir que este problema no falla por las razones
    que el filtro sabe medir.
    """
    def costo(x):
        a, b, c = x
        if a + b + c > 100.0:                               # capacidad de planta
            return float("nan")
        if a + b + c < 40.0:                                # demanda mínima
            return float("nan")
        if c > 0.6 * (a + b):                               # mezcla admisible
            return float("nan")
        margen = 4.2 * a + 3.1 * b + 5.6 * c
        # Rendimientos decrecientes por saturación: tampoco es cuadrático.
        penal = 38.0 * np.log1p((a + 1.4 * b + 2.2 * c) / 18.0) ** 2
        arranque = 6.0 * np.sqrt(a + b + c)
        return -(margen - penal - arranque)

    return Problema("Mezcla de producción",
                    descripcion="Repartir la producción entre tres líneas para sacar el mayor "
                                "margen, respetando la capacidad de la planta, una demanda "
                                "mínima y un tope de mezcla. El margen tiene rendimientos "
                                "decrecientes: producir el doble no da el doble.",
                    variables=["a · línea A [unidades]", "b · línea B [unidades]",
                               "c · línea C [unidades]"],
                    cotas=[(0, 60), (0, 60), (0, 60)],
                    objetivo=costo, bits_por_variable=4, ruido_absoluto=12.0,
                    n_muestras=200_000)


def ejemplo_secuencia_labs() -> Problema:
    """Nivel 3: un problema CON estructura real — y el matiz que enseña.

    LABS (secuencias binarias de baja autocorrelación, usadas en radar y
    comunicaciones) es de los poquísimos problemas combinatorios donde hay
    evidencia publicada de ventaja de escalado para QAOA.

    Y aun así este filtro lo marca en la medida 2. No es un fallo del problema
    ni del filtro: es que el objetivo de LABS es CUÁRTICO en las variables, y
    un QUBO solo puede ser cuadrático. Traducirlo exige variables auxiliares.
    La medida 2 mide si el problema entra en un QUBO tal cual, no si tiene
    estructura — véase «Dónde sí hay caso» en el README.
    """
    N = 16

    def costo(x):
        s = np.where(np.asarray(x) >= 0.5, 1.0, -1.0)     # cada variable es un bit
        # Energía LABS: suma de autocorrelaciones al cuadrado.
        return float(sum(float(s[: N - k] @ s[k:]) ** 2 for k in range(1, N)))

    return Problema("Secuencia LABS (N=16)",
                    descripcion="Encontrar una secuencia de 16 símbolos, cada uno +1 o −1, con "
                                "la menor autocorrelación posible. Se usa en radar y "
                                "comunicaciones: una secuencia así permite distinguir el eco "
                                "propio del ruido y de los ecos ajenos.",
                    variables=[f"s{i} · símbolo {i}" for i in range(1, N + 1)],
                    cotas=[(0.0, 1.0)] * N,
                    objetivo=costo, bits_por_variable=1, ruido_del_modelo=0.01,
                    n_muestras=60_000)


def ejemplo_asignacion_grande() -> Problema:
    """Nivel 4 y, además, ni siquiera cabe: el caso más común en la práctica.

    Una asignación de treinta tareas. El problema está perfectamente planteado
    —restricciones razonables, costo con relieve— pero al codificarlo se va a
    noventa qubits. Falla la primera medida y no hace falta mirar las demás.
    """
    n = 30
    rng = np.random.default_rng(7)
    costo_unitario = rng.uniform(40, 120, n)

    def costo(x):
        x = np.asarray(x)
        total = x.sum()
        if not (500.0 <= total <= 700.0):        # capacidad y demanda de la planta
            return float("nan")
        return float(costo_unitario @ x + 0.02 * (x ** 2).sum())

    return Problema("Asignación de 30 tareas",
                    descripcion="Repartir carga entre treinta tareas al menor costo, con un "
                                "tope de capacidad total y una demanda mínima. Está bien "
                                "planteado en todo lo demás: el problema es que al codificarlo "
                                "se va a noventa qubits.",
                    variables=[f"t{i} · tarea {i}" for i in range(1, n + 1)],
                    cotas=[(0.0, 40.0)] * n,
                    objetivo=costo, bits_por_variable=3, ruido_del_modelo=0.01,
                    n_muestras=20_000)


if __name__ == "__main__":
    tamizar(ejemplo_ascenso_restringido())
    tamizar(ejemplo_mezcla_de_produccion())
    tamizar(ejemplo_secuencia_labs())
    tamizar(ejemplo_asignacion_grande())
