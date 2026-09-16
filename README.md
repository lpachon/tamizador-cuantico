# Tamizador cuántico

[![CI](https://github.com/lpachon/tamizador-cuantico/actions/workflows/ci.yml/badge.svg)](https://github.com/lpachon/tamizador-cuantico/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-yellow.svg)](LICENSE)

**¿Merece la pena llevar su problema a un computador cuántico?**
Cinco medidas, cinco umbrales, un veredicto. En su portátil, en minutos, sin
cuenta de IBM y sin hardware cuántico.

La mayoría de los problemas de optimización empresariales **no** ganan nada con
computación cuántica en 2026 — y se puede saber de antemano, midiendo, en vez de
descubrirlo después de pagar un piloto. Esta herramienta hace esa medición.

Material del taller *«Dos relojes distintos»*, Clúster Tecnología & Economía del
Conocimiento, Cámara de Comercio de Bogotá.

---

## Instalación

Necesita Python 3.10 o superior.

```bash
git clone https://github.com/lpachon/tamizador-cuantico.git
cd tamizador-cuantico
pip install -r requirements.txt
```

`numpy` es lo único obligatorio. `scipy` mejora el muestreo y el refinamiento
clásico, pero el tamizador funciona sin él. `qiskit` solo hace falta para la
demostración de interferencia.

## Arranque rápido

```bash
python3 tamizador.py
```

Corre los cuatro ejemplos incluidos. Cada uno falla por un motivo distinto —
el contraste es el punto:

| Ejemplo | Qué le pasa | Veredicto |
|---|---|---|
| Ascenso con restricciones estrechas | Región válida diminuta y costo casi plano | NO-GO (3 y 4) |
| Mezcla de producción | Restricciones holgadas y objetivo con relieve | NO DESCARTADO |
| Secuencia LABS | Estructura de sobra, pero el objetivo es cuártico | NO-GO (2) |
| Asignación de 30 tareas | Bien planteado, pero se va a 90 qubits | NO-GO (1) |

El de LABS merece leerse entero: es de los poquísimos problemas combinatorios
con evidencia publicada de ventaja de escalado para QAOA, y **aun así este
filtro lo marca**. No es un fallo del problema ni del filtro — es que LABS no
cabe en un QUBO —[qué es eso](#qué-es-un-qubo)— sin variables auxiliares.

---

## Qué es un QUBO

El hardware cuántico de hoy acepta **una sola forma de problema**, y tiene
nombre: **QUBO**, del inglés *Quadratic Unconstrained Binary Optimization*.
Las tres palabras son el contrato:

- **Binaria** — las variables solo valen 0 o 1. Una velocidad continua hay que
  trocearla en niveles y escribir cada nivel en binario.
- **Cuadrática** — solo se admiten términos sueltos `qi` y productos de dos,
  `qi·qj`. Nunca de tres. Por eso un objetivo cuártico como LABS no cabe sin
  variables auxiliares.
- **Sin restricciones** — y esta es la palabra dolorosa. Sus restricciones no
  desaparecen: hay que meterlas dentro del propio objetivo como penalizaciones,
  o esconderlas en la codificación. Es parte de por qué la región válida acaba
  siendo una fracción ínfima del espacio.

Traducir su problema a esa forma es una **aproximación**, no una reescritura
exacta. La medida 2 mide cuánto se pierde en la traducción.

---

## Las cinco medidas

Cada pregunta es un número con un umbral. Nada aquí es opinión.

| # | Pregunta | Qué se mide | Umbral de descarte |
|---|---|---|---|
| 1 | ¿Cabe en el hardware de hoy? | Qubits = variables × bits, y profundidad del circuito | más de 30 qubits |
| 2 | ¿Sobrevive la traducción a QUBO? | ρ de Spearman de una cuadrática **sobre los bits** | ρ < 0,90 |
| 3 | ¿Las soluciones válidas son raras? | Rendimiento de factibilidad sobre muestreo Sobol | menos del 0,1 % |
| 4 | ¿El costo es plano? | Dispersión del objetivo **en sus propias unidades** | menos de 3× el ruido de su modelo |
| 5 | Línea base clásica | Mejor valor alcanzado en el mismo tiempo de cómputo | *informativa* |

**La medida 5 no aprueba ni suspende.** Es la cifra que cualquier propuesta
cuántica tiene que superar. Si nadie se la muestra batida, no hay caso que
discutir. El veredicto sale de las cuatro primeras — de las que se hayan podido
medir: si hay tan pocas soluciones válidas que la medida 2 no se puede calcular,
se marca como **no concluyente**, no como suspenso.

### Por qué esas medidas

- **Traducción (2).** El único formato que acepta el hardware actual es un QUBO,
  que *es* una cuadrática sobre variables **binarias**. Por eso el ajuste se hace
  sobre los bits codificados, no sobre las coordenadas continuas: es lo que el
  hardware vería de verdad. Si esa cuadrática no conserva el orden de sus
  soluciones, la traducción pierde justo lo que usted quiere optimizar.
  **Cuidado con la lectura:** un ρ bajo dice «no cabe en un QUBO tal cual», no
  «no tiene estructura». Un objetivo de orden superior —LABS es cuártico— puede
  estar lleno de estructura y aun así necesitar variables auxiliares para
  cuadratizarse.
- **Rareza (3).** Un algoritmo cuántico concentra probabilidad sobre la región
  válida. Si esa región es una fracción ínfima del espacio, ninguna concentración
  alcanzable hoy la encuentra.
- **Planitud (4).** Y aunque la encuentre: si todas las soluciones válidas valen
  casi lo mismo, concentrar probabilidad sobre ellas no mejora el objetivo.

Las tres juntas explican por qué tantos problemas con restricciones duras no
ganan nada con el hardware de hoy: no basta con que la máquina concentre
probabilidad si la región válida es inencontrable, y no sirve de nada
encontrarla si, una vez dentro, todas las soluciones valen lo mismo.

---

## Dónde sí hay caso

Un filtro que solo descarta deja una pregunta abierta: ¿dónde gana la cuántica,
entonces? La respuesta útil no es una lista de sectores, sino **qué tiene que
tener el problema**:

| | Qué tiene el problema | ¿Gana? | Ejemplos |
|---|---|---|---|
| **1** | **Ya es cuántico** | Sí — es el caso más sólido | Moléculas, materiales, reacciones |
| **2** | **Estructura algebraica global** (periodicidad) | Sí, demostrado en teoría | Factorización, logaritmo discreto |
| **3** | **Estructura combinatoria muy particular** | Evidencia de escalado, aún no en hardware útil | LABS, 8-SAT aleatorio |
| **4** | **Ninguna de las anteriores** | No | Ruteo, turnos, carga, portafolio |

**Nivel 1.** La máquina no *simula* el sistema: lo **encarna**. Es el argumento
original de Feynman y el único con una física limpia detrás.

**Nivel 3.** Hay resultados serios de ventaja de *escalado* para QAOA en
problemas como LABS (secuencias binarias de baja autocorrelación, usadas en
radar) y 8-SAT aleatorio — por ejemplo, tiempo hasta solución de 1,11^N frente
a 1,25^N del mejor heurístico clásico. Los matices importan: son simulaciones
sin ruido, a pocas decenas de qubits, extrapoladas, y no son un cambio de clase
de complejidad. Pero el patrón confirma la regla: **donde aparece ventaja es
donde hay una estructura muy peculiar que explotar.**

**Nivel 4 — y aquí está el argumento que casi nunca se hace.** Sin estructura,
lo mejor a lo que se puede aspirar es Grover: una mejora de **raíz cuadrada**.
Y entonces entra el reloj. Una compuerta física de dos qubits tarda unos 100 ns,
pero una compuerta *lógica* con corrección de errores necesita miles de ciclos
físicos, así que el reloj lógico cae a decenas de kilohercios. Enfrente hay
procesadores clásicos a gigahercios y con miles de núcleos: una desventaja de
constante de entre 10⁴ y 10⁶.

> Una mejora de raíz cuadrada sobre una máquina un millón de veces más lenta
> por operación no es una mejora.

Por eso la mayoría de los problemas de optimización empresariales están en el
nivel 4, y por eso este filtro sirve sobre todo para confirmarlo rápido y barato.

---

## Tamizar su propio problema

Lo único que tiene que escribir es una función que devuelva el costo, o `NaN`
si el punto viola alguna restricción.

```python
import numpy as np
from tamizador import Problema, tamizar

def mi_objetivo(x):
    turnos, extras, subcontrata = x
    if turnos + extras > 240:                   # tope de horas
        return float("nan")                     # NaN = no factible
    if subcontrata > 0.3 * (turnos + extras):   # tope de subcontratación
        return float("nan")
    return 52_000 * turnos + 81_000 * extras + 96_000 * subcontrata

tamizar(Problema(
    nombre="Asignación de turnos",
    cotas=[(0, 200), (0, 60), (0, 80)],   # una pareja (mín, máx) por variable
    objetivo=mi_objetivo,
    bits_por_variable=3,                  # resolución de la codificación
    ruido_del_modelo=0.02,                # incertidumbre relativa de su modelo
))
```

Hay una plantilla lista para copiar en [`ejemplos/plantilla.py`](ejemplos/plantilla.py).

### Declare su ruido en unidades del objetivo

`ruido_absoluto` es la forma recomendada: si su objetivo son kilos, déclarelo en
kilos; si son pesos, en pesos. La alternativa relativa (`ruido_del_modelo`) se
calcula contra la mediana, y eso **deja de tener sentido cuando el objetivo
cruza el cero** — un problema de pérdidas y ganancias con mediana cerca de cero
daría una dispersión relativa astronómica y sin significado. En ese caso la
herramienta se declara **no concluyente** y le pide el valor absoluto, en vez de
inventarse un número.

### Lo que imprime antes de medir

Al ejecutarse, la herramienta empieza por decir en voz alta **todo lo que va a
dar por supuesto**: qué decisión se está tomando, cada variable con su rango y
la resolución que le compra su codificación, cuántos qubits salen, qué ruido se
está usando y cuántos puntos va a muestrear.

```
  QUÉ SE DECIDE
    Elegir la velocidad y el ángulo de subida al principio y al final de
    un ascenso de 10.000 a 36.000 pies, para llegar al crucero gastando
    el menor combustible posible.

  VARIABLES DE DECISIÓN
    1. v1 · velocidad inicial [m/s]                150 a 250   paso 14,29
    2. v2 · velocidad final [m/s]                  150 a 250   paso 14,29
    3. γ1 · ángulo inicial [rad]                 0,005 a 0,2   paso 0,02786
    4. γ2 · ángulo final [rad]                   0,005 a 0,2   paso 0,02786

  CODIFICACIÓN      3 bits por variable → 8 niveles cada una → 12 qubits
  RUIDO DEL MODELO  150 en unidades del objetivo (declarado)
  MUESTREO          262.144 puntos (Sobol, semilla 42)
                    pidió 200.000; se redondea a la potencia de dos siguiente
```

Ese bloque no es decoración: **la mitad de los errores de uso se cazan ahí**,
antes de leer un solo veredicto. Un paso de 14,29 m/s cuando usted necesitaba
precisión de 1 m/s se ve de un vistazo, y unas cotas demasiado estrechas
también.

### Los dos errores más comunes

**Olvidar devolver `NaN` en las restricciones.** Sin eso el rendimiento de
factibilidad sale 100 % y la medida 3 pierde todo sentido. Si ve un 100 %,
revise esto antes que nada.

**Poner cotas estrechas «para ayudar».** Las cotas deben cubrir todo el rango que
usted consideraría, no solo la zona buena. Si las aprieta, está respondiendo la
pregunta antes de medirla.

### Parámetros

| Parámetro | Qué es | Por defecto |
|---|---|---|
| `cotas` | Lista de `(mín, máx)`, una por variable de decisión | — |
| `objetivo` | Función que recibe un vector y devuelve costo o `NaN` | — |
| `bits_por_variable` | Resolución de la codificación binaria | `3` |
| `descripcion` | Qué decisión se está tomando. Se imprime al ejecutar | `""` |
| `variables` | Una etiqueta por variable, con unidades | `None` |
| `ruido_del_modelo` | Incertidumbre **relativa** de su modelo (0,01 = 1 %) | `0.01` |
| `ruido_absoluto` | Incertidumbre **en unidades del objetivo**. Preferible | `None` |
| `n_muestras` | Muestras para estimar factibilidad y dispersión. Sobol redondea hacia arriba a la potencia de dos siguiente, así que pedir 20.000 evalúa 32.768 | `20 000` |
| `semilla` | Para reproducir exactamente el mismo resultado | `42` |

Los umbrales están al principio de `tamizador.py` y se pueden ajustar.
`QUBITS_MAX` es el único que envejecerá con el hardware; los demás son
propiedades del problema, no de la máquina.

---

## La demostración de interferencia

```bash
python3 demo_interferencia.py
```

Demuestra en su máquina que dos compuertas Hadamard **no** son dos lanzamientos
de moneda:

```
  Moneda clásica, 2 lanzamientos     0:  49.79 %    1:  50.21 %
  Un qubit, 1 compuerta H            0:  49.60 %    1:  50.40 %
  Un qubit, 2 compuertas H           0: 100.00 %    1:   0.00 %
```

Dos lanzamientos de moneda dan 50/50. Dos compuertas dan 100/0, porque las
amplitudes se **cancelan**: al estado 1 llegan dos caminos, uno con +½ y otro
con −½, y suman cero. Una probabilidad nunca podría hacer eso.

Ese es el recurso que separa un computador cuántico de uno clásico — y también
la razón por la que solo sirve cuando el problema tiene algo que cancelar.

---

## El otro reloj: su inventario criptográfico

El tamizador mide el reloj que **no** corre. Para el que sí corre hay otra
herramienta en este mismo repositorio:

```bash
python3 inventario_cripto.py www.suempresa.com
```

Se conecta a su dominio y le dice qué criptografía usa de verdad — grupo de
intercambio de claves negociado, cifrado simétrico, tipo y tamaño de la clave
del certificado, algoritmo de firma y cuándo caduca — y clasifica cada pieza.

El resultado suele sorprender: **el intercambio de claves ya está protegido**.
Sitios como `google.com` o `www.ccb.org.co` negocian hoy `X25519MLKEM768`, un
grupo híbrido post-cuántico que su proveedor o su CDN activó sin que nadie
hiciera nada. Lo que sigue cayendo son **la clave y la firma del certificado**,
y eso sí es cosa del dueño del dominio.

Medir el grupo negociado necesita un `openssl` 3.5 o superior: el módulo `ssl`
de Python no lo expone. Si no lo encuentra, la herramienta dice **no medido** en
vez de suponer.

Es el mismo reparto que en Bitcoin: el minado se salva, las firmas no.

Y la cuenta que decide si usted ya llegó tarde:

```bash
python3 inventario_cripto.py --mosca 15 7
```

donde 15 son los años que su secreto debe durar y 7 los que tardará su
migración. Si la suma supera el tiempo que falta para que exista la máquina,
hay una ventana de años en la que sus datos quedan expuestos **y usted ya no
puede hacer nada**, porque se cifraron antes de terminar de migrar.

Para ver si su navegador ya usa claves post-cuánticas, sin instalar nada, abra
[pq.cloudflareresearch.com](https://pq.cloudflareresearch.com/).

---

## Qué NO hace esta herramienta

- **No ejecuta nada en hardware cuántico.** Decide si valdría la pena hacerlo.
- **No formula el QUBO por usted.** Si su problema pasa el filtro, ese es el
  siguiente paso y es trabajo de modelado.
- **No cubre criptografía post-cuántica.** Ese es el otro reloj, y corre por su
  cuenta: allí la tarea es un inventario criptográfico, no un tamizado.
- **«NO DESCARTADO» no es una promesa.** El filtro impone condiciones
  **necesarias**, no suficientes: elimina, no selecciona. Superarlo significa que
  el problema no falla por las razones que el filtro sabe medir — no que la
  cuántica vaya a ganarle a su solver clásico. De hecho, el ejemplo de mezcla de
  producción que incluimos lo supera y aun así un solver clásico lo resuelve en
  microsegundos.

## Pruebas

```bash
pip install pytest
pytest tests -q
```

Cada hallazgo de [`AUDITORIA.md`](AUDITORIA.md) tiene su prueba de regresión, así
que el registro no es una promesa sino algo que se comprueba en cada cambio. Se
verificó además que las pruebas **fallan** si se reintroducen los defectos: sin
esa comprobación, una suite verde no dice nada.

CI corre las pruebas en Python 3.10 a 3.13, comprueba que la herramienta
funciona **solo con numpy** —como afirma este README— y que la demostración de
interferencia sigue dando 100 / 0.

## Créditos

Herramienta desarrollada para el taller *«Dos relojes distintos»* del Clúster
Tecnología & Economía del Conocimiento, Cámara de Comercio de Bogotá.

## Licencia

MIT. Cópielo, modifíquelo y repártalo sin pedir permiso.
