# Auditoría — `tamizador-cuantico`

Registro de defectos encontrados y su estado. La herramienta pide auditar el
banco de pruebas antes de creerse un resultado; lo mínimo es aplicárselo.

**Ronda 1 — 16 de septiembre de 2026.** Ocho hallazgos, dos críticos. Todos
resueltos y con prueba de regresión.

| # | Hallazgo | Severidad | Estado | Prueba |
|---|---|---|---|---|
| C1 | La medida 2 rechazaba un QUBO genuino | **Crítico** | ✅ | Un Ising exacto daba ρ = 0,751 → **FALLA**; ahora ρ = 1,000 |
| C2 | La medida 4 dependía de dónde estuviera el cero | **Crítico** | ✅ | Misma dispersión, mediana 0 → 1,8 × 10¹⁴ %; ahora decide o se declara no concluyente |
| C3 | La línea base clásica estaba subestimada | Alto | ✅ | Mejora sobre Sobol: 0,086 → **1,476** |
| C4 | La medida 2 sobreajustaba con pocos puntos | Alto | ✅ | 40 puntos y ruido puro daban ρ = 1,000; ahora «no se pudo medir» |
| C5 | El ejemplo de ascenso no era dimensionalmente coherente | Medio | ✅ | Reescrito en metros y segundos, con Bréguet y consumo específico real |
| C6 | Deck y herramienta se habían desincronizado | Medio | ✅ | La medida 2 se llamaba distinto en cada sitio |
| C7 | El deck decía «10⁵ muestras Sobol» | Bajo | ✅ | El valor por defecto son 20.000 |
| C8 | `n_muestras` no era lo que se evaluaba | Bajo | ✅ | Documentado: Sobol redondea a la potencia de dos siguiente |
| C9 | El veredicto del intercambio de claves estaba cableado, no medido | **Crítico** | ✅ | Daba «CAE con Shor» incluso en el sitio de demostración post-cuántica de Cloudflare |
| C10 | Los veredictos del certificado tampoco se derivaban de lo medido | Medio | ✅ | Mismo patrón que C9, latente: una firma post-cuántica se habría marcado como caída |

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

## Lo que se comprobó y resistió

- La explicación de LABS es correcta: sobre espines puros da ρ = 0,027 y un
  objetivo cuadrático por la misma tubería da 0,74, así que el ρ bajo viene de
  la **cuarticidad**, no del umbralado.
- La línea base clásica encuentra **E = 24** para LABS con N = 16, que es el
  óptimo conocido (factor de mérito 5,33).
- Una columna de varianza nula no desestabiliza el ajuste de la medida 2.
