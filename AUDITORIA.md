# Auditoría — `tamizador-cuantico`

Registro de defectos encontrados y su estado. La herramienta pide auditar el
banco de pruebas antes de creerse un resultado; lo mínimo es aplicárselo.

Tres rondas, quince hallazgos, todos resueltos y con prueba de regresión.
Cada prueba se validó **reintroduciendo el defecto** en una copia: una suite
verde que no se ha probado contra el bug no demuestra nada.

| # | Ronda | Hallazgo | Severidad | Estado | Prueba |
|---|---|---|---|---|---|
| C1 | 1 | La medida 2 rechazaba un QUBO genuino | **Crítico** | ✅ | Un Ising exacto daba ρ = 0,751 → **FALLA**; ahora ρ = 1,000 |
| C2 | 1 | La medida 4 dependía de dónde estuviera el cero | **Crítico** | ✅ | Misma dispersión, mediana 0 → 1,8 × 10¹⁴ %; ahora decide o se declara no concluyente |
| C3 | 1 | La línea base clásica estaba subestimada | Alto | ✅ | Mejora sobre Sobol: 0,086 → **1,476** |
| C4 | 1 | La medida 2 sobreajustaba con pocos puntos | Alto | ✅ | 40 puntos y ruido puro daban ρ = 1,000; ahora «no se pudo medir» |
| C5 | 1 | El ejemplo de ascenso no era dimensionalmente coherente | Medio | ✅ | Reescrito en metros y segundos, con Bréguet y consumo específico real |
| C6 | 1 | Deck y herramienta se habían desincronizado | Medio | ✅ | La medida 2 se llamaba distinto en cada sitio |
| C7 | 1 | El deck decía «10⁵ muestras Sobol» | Bajo | ✅ | El valor por defecto son 20.000 |
| C8 | 1 | `n_muestras` no era lo que se evaluaba | Bajo | ✅ | Documentado: Sobol redondea a la potencia de dos siguiente |
| C9 | 2 | El veredicto del intercambio de claves estaba cableado, no medido | **Crítico** | ✅ | Daba «CAE con Shor» incluso en el sitio de demostración post-cuántica de Cloudflare |
| C10 | 2 | Los veredictos del certificado tampoco se derivaban de lo medido | Medio | ✅ | Mismo patrón que C9, latente: una firma post-cuántica se habría marcado como caída |
| C11 | 3 | La medida 1 prometía más alcance del que medía | Bajo | ✅ | Titulaba «el hardware de hoy» y solo modela el de compuertas |
| C12 | 3 | La línea base clásica se salía de las cotas | **Crítico** | ✅ | La plantilla proponía producción **negativa**; ahora devuelve el óptimo del borde |
| C13 | 3 | El formato numérico se contradecía a sí mismo | Alto | ✅ | El mismo 32768 salía «32.768» y «32,768» en una ejecución |
| C14 | 3 | El job `sin scipy` del CI estaba rojo por el código | Alto | ✅ | La prueba fijaba el conteo de Sobol; ahora comprueba el invariante |
| C15 | 3 | El Spearman de repuesto no promediaba empates | Medio | ✅ | Con objetivo constante daba FALLA donde scipy da «no concluyente» |

## Ronda 2 — 16 de septiembre de 2026

### C9 · El intercambio de claves se afirmaba, no se medía

`inventario_cripto.py` imprimía «Intercambio de claves · CAE con Shor» como
**constante escrita a mano**. Ninguna variable lo alimentaba. El propio texto se
contradecía: decía «curva elíptica, *salvo que el servidor negocie un grupo
híbrido*» y acto seguido sentenciaba que caía.

Lo destapó correrlo contra `pq.cloudflareresearch.com` — el sitio de
demostración post-cuántica de Cloudflare — donde dio el veredicto **exactamente
al revés** del real.

**Arreglo:** el grupo se mide de verdad, invocando un `openssl` con ML-KEM y
leyendo el grupo negociado. Tres veredictos posibles: *ya protegido* si es
híbrido post-cuántico, *cae* si es clásico, y **no medido** si no hay un openssl
capaz — que es lo que hay que decir en vez de suponer.

**Y cambió el mensaje.** Medido de verdad, `pq.cloudflareresearch.com`,
`google.com` y el propio `www.ccb.org.co` ya negocian `X25519MLKEM768`. El
intercambio de claves ya está migrado, casi siempre sin que el dueño del sitio
hiciera nada. Lo que sigue cayendo son los certificados y las firmas — que sí
son cosa suya.

## Los dos críticos de la ronda 1, en detalle

### C1 · La medida 2 rechazaba un QUBO genuino

El sustituto cuadrático se ajustaba sobre las coordenadas **continuas** del
muestreo Sobol, pero el objetivo de un problema binario es una función escalón
de esas coordenadas. Un modelo de Ising exacto —el objeto más cuadrático que
existe— puntuaba ρ = 0,751 y quedaba descartado.

**Arreglo:** el ajuste se hace sobre los **bits codificados**, que es lo que un
QUBO vería de verdad, y sin términos q² porque para un bit q² = q. Es
literalmente la forma de un QUBO.

### C2 · La medida 4 dependía de dónde estuviera el cero

La dispersión se normalizaba por la mediana. El mismo problema, con la misma
dispersión absoluta de 2,0, daba:

| mediana | dispersión reportada | veredicto |
|---:|---:|---|
| 1000 | 0,18 % | FALLA |
| 10 | 18 % | PASA |
| 0,1 | 1.800 % | PASA |
| 0 | 1,8 × 10¹⁴ % | PASA |

Un objetivo de pérdidas y ganancias que cruce el cero daba un número sin
significado.

**Arreglo:** la comparación se hace en **unidades del objetivo**. `ruido_absoluto`
es la forma recomendada de declarar la incertidumbre. Si solo se da la relativa
y la mediana no domina a la dispersión, la medida se declara **no concluyente**
en vez de inventarse una cifra.

## Ronda 3 — 17 de septiembre de 2026

### C11 · La medida 1 prometía más alcance del que medía

**Severidad:** de comunicación, no de cálculo.

El título de la medida 1 era «¿Cabe en el hardware de hoy?», pero su propio
comentario interno declara que modela «QAOA p=2 sobre topología heavy-hex»: es
decir, hardware **de compuertas**. Un asistente que conozca D-Wave —5.760 qubits
físicos— tenía derecho a preguntar por qué la herramienta corta en 30, y el texto
no se lo contestaba en ningún sitio.

El veredicto no cambia: el estudio revisado por pares que compara el resolvedor
híbrido de D-Wave contra CPLEX, Gurobi e IPOPT concluye que las implementaciones
actuales están «limited in size and not yet upscaled to real-world situations».
Lo que cambia es la **razón**, y esa razón faltaba.

**Arreglo:** el título ahora dice «¿Cabe en el hardware **de compuertas** de
hoy?», el detalle remite a la sección nueva del README, y esa sección explica el
muro real del annealing: el *minor embedding* (en Pegasus, K₁₅₀ con cadenas de 14
qubits — 38 veces más qubits físicos que variables) y el rango dinámico finito de
los acopladores.

### C12 · La línea base clásica se salía de las cotas

**Severidad: crítica.** Es la cifra sobre la que descansa todo el argumento de
la herramienta: *«si nadie se la muestra batida, no hay caso que discutir»*.

`_m5_clasico` refinaba con COBYLA **sin pasarle las cotas**. COBYLA no las
respeta si no se le dan: se iba fuera de la caja y el valor que volvía se
aceptaba tal cual. Corriendo `ejemplos/plantilla.py`, que es exactamente lo que
hace la sala en el taller:

```
x = [42,0   −0,87   58,87]     frente a cotas [(0, 60), (0, 60), (0, 60)]
```

Una producción de **−0,87 unidades** en la línea B, anunciada como «la cifra a
batir». En un caso con el óptimo fuera de la caja, informaba `0,0000` cuando lo
mejor alcanzable dentro es `4,0000`. No era solo la plantilla:
`ejemplo_mezcla_de_produccion`, del propio repositorio, ya se salía.

**Arreglo:** se le pasan las cotas a COBYLA (`bounds`, con reserva para scipy
anterior a 1.11) y además se **recorta y reevalúa** el punto final. La cifra a
batir tiene que ser alcanzable dentro de lo que el usuario declaró.

### C13 · El formato numérico se contradecía a sí mismo

`_num()` existía para escribir en castellano pero solo se usaba en el eco de
parámetros; las cinco medidas formateaban en inglés. En una sola ejecución:

```
MUESTREO   32.768 puntos                       ← punto = millar
medido :   57.4310%  (18,819 de 32,768)        ← punto = decimal, coma = millar
```

El caso peor era la medida 4: `dispersión = 151.5` frente a `umbral > 5.229`,
que en castellano se lee como un suspenso y marcaba **PASA**. Y cualquier valor
entre 1.000 y 9.999 salía como `1,500`, que se lee 1,5: error de factor mil.

**Arreglo:** `_ent`, `_fij` y `_pct` junto a `_num`, y todas las medidas pasan
por ellos. La prueba compara que el mismo número se escriba igual en los dos
bloques, en vez de fijar una cadena concreta.

## Lo que se comprobó y resistió

- La explicación de LABS es correcta: sobre espines puros da ρ = 0,027 y un
  objetivo cuadrático por la misma tubería da 0,74, así que el ρ bajo viene de
  la **cuarticidad**, no del umbralado.
- La línea base clásica encuentra **E = 24** para LABS con N = 16, que es el
  óptimo conocido (factor de mérito 5,33).
- Una columna de varianza nula no desestabiliza el ajuste de la medida 2.
- Los cuatro veredictos son **idénticos con y sin scipy** (comprobado ejecutando
  los ejemplos en las dos ramas).
- La guarda antisobreajuste de C4 aguanta **en su propio límite**: con ruido
  puro y el triple de muestras que términos, ρ sale entre 0,52 y 0,61 — lejos
  del umbral de 0,90.
- El `grep` del job de demostración coincide exacto con lo que imprime
  `demo_interferencia.py`.

