# 07 · Subtotal sugerido (v2.1)

> El admin casi siempre ajusta el precio, así que el objetivo **no** es adivinarlo al centavo: es darle un **subtotal de partida, listo para modificar, con la suma que lo explica**, y los precios recientes de la ruta a un clic. Sin machine learning: reglas + consultas SQL + medianas, que con decenas de servicios al mes es lo correcto.
> Implementación: `precios/sugeridor.py` con la lógica pura (recibe historial y parámetros, devuelve sugerencia) y una capa delgada que consulta la DB.
> **v2.1**: la sugerencia trae `desglose` (la suma que explica el subtotal); el cobro de servicios con **varios destinos está en stand-by**; recordatorio de **costos y tarifas pendientes** (§5).

## 1. Entradas

Del servicio (o del formulario de "Nuevo servicio" antes de que exista):
- `cliente_id`
- `unidad_id` (opcional; afina el historial)
- `destinos`: conjunto de `lugar_id` de los viajes con destino (sin importar el orden)
- `km`: Σ `distancia_km` de los destinos (si falta, Σ `km_reportado`; si falta, null)
- `n_destinos`

**Historial** = servicios con factura **vigente** (no canceladas) dentro de `precio.ventana_historial_dias` (default 365), con su `subtotal`, fecha, unidad, destinos y km.

## 2. Reglas en cascada (la primera que aplica gana)

| Nivel | Fuente | Regla | Confianza |
|---|---|---|---|
| 1 | **Tarifa pactada** | Servicio con **un solo destino** que tiene `tarifa_pactada` activa para el cliente → esa tarifa. | alta |
| 2 | **Misma ruta, mismo cliente** | Historial con el **mismo conjunto de destinos**. Si hay ≥2 con la misma unidad, usar solo esos. Tomar los últimos 5: si los últimos 3 están dentro de ±10% entre sí → el **más reciente**; si no → **mediana** de los 5. | alta (≥2 servicios) · media (1) |
| 3 | **$/km del cliente** | Últimos 10 servicios del cliente con km > 0: mediana de `subtotal / km` × `km` actual. Requiere `km`. | media (≥5 servicios) · baja |
| 4 | **Fórmula base** | `tarifa_base + tarifa_km × km`, con los parámetros de `configuracion`. Requiere `km` y parámetros configurados. | baja |
| — | Sin referencia | `monto = null`, mensaje "Sin referencias para esta ruta" | — |

Después de elegir el monto: **redondear** al múltiplo de `precio.redondeo` (default $50) con half-up. Los niveles 1 y 2 no se redondean (son precios reales).

### 2.0 Tarifario fijo por cliente — IMPLEMENTADO (hoy solo Chemital, 5 oct 2026)

Vlad decidió que, por ahora, **solo se precalcula el cliente Chemital** con un tarifario fijo; los demás clientes usan la cascada de abajo. Esta regla tiene prioridad sobre los niveles 1-4 (`fuente = "tarifa_pactada"`, confianza alta, sin redondeo) y conserva `ultimos_precios_ruta` y `rango` como contexto.

- **Quién**: el cliente cuyo nombre comercial o razón social contiene el texto `cliente` del tarifario (case-insensitive; default `chemital`).
- **Unidad**: se clasifica por su peso bruto vehicular: ≤0.5 t Saveiro, ≤1 t Nissan, ≤3.5 t Ram. Una unidad más pesada (Rabón) no tiene tarifa y cae a la cascada.
- **Destino en CDMX**: CP entre 01000 y 16999.
- **Cálculo**: el primer destino en CDMX se cobra con la tarifa `cdmx` de la unidad; **cada destino adicional** (viaje con destino) suma la tarifa `extra`. Sin ningún destino en CDMX la regla no aplica.

| Unidad | Viaje a CDMX | Cada destino adicional |
|---|---|---|
| Saveiro | $1,650 | $660 |
| Nissan | $2,200 | $660 |
| Ram | $2,970 | $990 |

Los valores viven en `configuracion` (`precio.tarifario_cliente`) y se editan en **Configuración → Precios y tarifas** (`GET/PATCH /configuracion`). Código: `precios/tarifario.py`. Esto cubre el caso de varios destinos **para Chemital**; la regla general (§2.1) sigue en stand-by para los demás clientes.

### 2.1 Servicios con varios destinos — EN STAND-BY

Vlad aún no define cómo se cobran (¿suma de tarifas?, ¿la mayor más un cargo por parada?, ¿otra regla?). Hasta que lo defina:
- El nivel 1 **no aplica** a servicios con más de un destino.
- `precio.cargo_parada_extra` existe en `configuracion` pero **no se usa**; la UI lo muestra deshabilitado con la nota "Pendiente de definir".
- Esos servicios se sugieren con los niveles 2, 3 y 4 (el 4, sin cargo por parada).

Cuando se defina, se cambia solo esta sección, `sugeridor.py` y sus tests.

> 🔴 **INFO REQUERIDA (Vlad) — en stand-by** — cómo se cobra un servicio con varios destinos. No bloquea ninguna fase.

## 3. Contexto que siempre se devuelve (aunque gane otro nivel)

- `ultimos_precios_ruta`: hasta 3 `{fecha, subtotal}` de la misma ruta y cliente → chips de un clic en la UI.
- `rango`: `{min, max}` de esos precios.
- `referencias`: los servicios usados para el cálculo (para que el admin pueda abrirlos).

## 4. Salida

```json
{
  "monto": "1650.00",
  "desglose": [
    { "concepto": "Tarifa base", "monto": "600.00" },
    { "concepto": "80 km × $12.50", "monto": "1000.00" },
    { "concepto": "Redondeo a $50", "monto": "50.00" }
  ],
  "confianza": "baja",
  "fuente": "formula",
  "explicacion": "Fórmula base: no hay servicios previos de esta ruta",
  "referencias": [],
  "ultimos_precios_ruta": [],
  "rango": null,
  "configuracion_pendiente": false
}
```
Se guarda como `servicio.precio_sugerido` y `servicio.precio_sugerido_detalle` al timbrar: con eso, más adelante se puede medir qué tan lejos queda la sugerencia del precio final y ajustar las reglas.

### 4.1 `desglose`: la suma que explica el subtotal

Toda sugerencia con monto trae `desglose`, una lista de `{ concepto, monto }` cuya **suma es exactamente el subtotal sugerido**. La UI la pinta como una suma debajo del campo (`05 §5`, SuggestionBreakdown): una línea por concepto y, al pie, "= Subtotal sugerido".

| Fuente | Líneas del desglose |
|---|---|
| `tarifa_pactada` | "Tarifa pactada · {destino}" |
| `historial_ruta` (más reciente) | "Último precio de esta ruta · {fecha} · servicio #{n}" |
| `historial_ruta` (mediana) | "Mediana de los últimos {n} servicios de esta ruta" |
| `historial_km` | "{km} km × ${x}/km (mediana de {cliente})" y, si cambió el monto, "Redondeo a ${r}" |
| `formula` | "Tarifa base", "{km} km × ${tarifa_km}" y, si cambió el monto, "Redondeo a ${r}" |

Reglas: la línea de redondeo puede ser negativa y nunca se omite cuando el redondeo cambió el monto (la suma tiene que cuadrar al centavo). Los textos de `concepto` los arma el backend, en español, listos para mostrar.

## 5. Costos y tarifas pendientes (arranque en frío)

Al inicio no hay historial: solo funcionan los niveles 1 y 4, y ambos dependen de **datos que Vlad todavía no ha capturado**.

> 🔴 **INFO REQUERIDA (Vlad) — COSTOS PENDIENTES** — antes de dar por terminada la Fase 4 (historia H4.6), pide a Vlad que capture en *Configuración → Precios y tarifas*:
> 1. **Tarifas pactadas** por cliente y destino (las rutas habituales).
> 2. **Tarifa base** y **costo por km** de la fórmula (o la decisión de no usar fórmula).
> 3. **Redondeo** (default $50).
>
> No inventes estos valores ni los dejes sembrados en el seed. Si Vlad aún no los tiene, la fase se puede cerrar con la app recordándoselo (abajo).

**Recordatorio dentro de la app** (`GET /configuracion/pendientes`), para que nadie dependa de acordarse:
- Falta `formula` si `precio.tarifa_base` o `precio.tarifa_km` son null.
- Falta `tarifas_pactadas` si no existe ninguna `tarifa_pactada` activa.
- Mientras haya faltantes y `precio.recordatorio_descartado = false`, la UI muestra el aviso **SetupReminder** ("Aún no capturas tus costos y tarifas; la sugerencia solo usa el historial" + botón "Configurar") en tres lugares: debajo del subtotal en Facturar, en la cabecera de Configuración → Precios y tarifas, y sobre los pendientes del dashboard.
- El admin puede descartarlo ("No usaré tarifas ni fórmula") → `precio.recordatorio_descartado = true`; se reactiva desde Configuración.
- Toda sugerencia incluye `configuracion_pendiente` para que la pantalla sepa si mostrar el aviso.

Importar un Excel de facturas pasadas como historial queda fuera del MVP; si se quiere, se especifica aparte.

## 6. Dónde se usa

- **Facturar** (Fase 4): el campo **Subtotal** llega con el sugerido ya escrito y seleccionado, listo para modificar; debajo, la suma del desglose y los últimos precios de la ruta; debajo, el total calculado automáticamente (`05 §7.2`).
- **Nuevo servicio** (el campo existe desde Fase 2; la sugerencia llega en Fase 4): subtotal opcional —obligatorio con timbrado anticipado— con la sugerencia y su desglose a la mano.

## 7. Tests

- [ ] Tarifa pactada de 1 destino; con 2 destinos el nivel 1 no aplica (stand-by).
- [ ] Misma ruta: últimos 3 estables → el más reciente; inestables → mediana de 5; prioriza misma unidad si hay ≥2.
- [ ] Conjunto de destinos igual en distinto orden = misma ruta.
- [ ] $/km con mediana; sin km → salta al siguiente nivel.
- [ ] Fórmula + redondeo a $50; sin parámetros → sin sugerencia. `cargo_parada_extra` no interviene.
- [ ] Facturas canceladas no cuentan como historial.
- [ ] `desglose`: en todas las fuentes, Σ `desglose.monto` = `monto`; con redondeo hacia abajo la línea es negativa.
- [ ] `/configuracion/pendientes`: sin parámetros ni tarifas → dos faltantes; con ambos → `completo`; descartado → la UI no avisa.
