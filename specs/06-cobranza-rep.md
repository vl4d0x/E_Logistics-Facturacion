# 06 · Cobranza y Complemento de Pago (REP)

> Todas las facturas de Elogistics son **PPD**. Cuando un cliente paga, hay que (1) saber **qué facturas** pagó, (2) bajar sus saldos y (3) emitir un **CFDI de tipo P con Complemento de Pagos 2.0 (REP)**. El problema real: algunos clientes depositan un monto sin decir qué facturas cubre. Este spec define el flujo, el **algoritmo de conciliación** y el mapeo del REP.
>
> **Regla de oro** (igual que `04`): los nombres JSON los define Facturama. Verifica contra su documentación vigente de CFDI de pago 2.0.
>
> **v2.1**: cada combinación sugerida —en especial la coincidencia exacta— muestra **los servicios que cubre**, para que el admin corrobore antes de aplicar.

## 1. Contexto fiscal

- El REP se emite **a más tardar el día 5 natural del mes siguiente** al del pago (regla 2.7.1.32 RMF 2026; si cae en inhábil, se recorre al siguiente hábil).
- Un REP puede documentar uno o varios pagos del mismo receptor del periodo. **MVP: 1 pago = 1 REP** (más simple de conciliar, cancelar y explicar). Agrupar varios pagos en un REP queda en backlog.
- Solo se emite REP de pagos **efectivamente recibidos**.
- Su cancelación **siempre** requiere aceptación del receptor en 2026 (§6).

## 2. Flujo

```
Registrar pago ──> Conciliar (sugerencias automáticas o selección manual) ──> Aplicar ──> Timbrar REP ──> Enviar
                                                                     └─ "Aplicar y generar REP" hace los tres en un clic
```

### 2.1 Registrar pago
Datos: cliente, fecha de pago (y hora si se conoce; si no, 12:00 local), monto, forma de pago (default `03` transferencia), número de operación/referencia bancaria (opcional pero recomendado), cuentas ordenante/beneficiaria (opcionales), comprobante bancario (archivo opcional), notas.

### 2.2 Conciliar
- Si el cliente **sí dijo** qué pagó: el admin marca esas facturas (buscador por folio, UUID, número de servicio, fecha o monto).
- Si **no lo dijo**: en cuanto se teclea el monto, el sistema llama a `POST /cobranza/sugerencias` y propone combinaciones (§3). El admin elige una con un clic y puede ajustar marcando/desmarcando.
- Atajo: desde el detalle de una factura, "Registrar pago" abre el formulario con esa factura seleccionada y su saldo como monto.

### 2.3 Aplicar
En **una transacción**, con `SELECT … FOR UPDATE` sobre las facturas:
1. Validar: facturas del mismo cliente, `PPD`, vigentes, con saldo; cada monto ≤ saldo; Σ = `pago.monto` (§2.4).
2. Por factura: `num_parcialidad` = (aplicaciones activas previas + 1), `saldo_anterior`, `saldo_insoluto = saldo_anterior − monto`.
3. Actualizar `factura.saldo_insoluto` y `estado_cobro`; `pago.estado = aplicado`, `aplicado_at`.

### 2.4 Regla de cuadre
- **MVP**: Σ aplicaciones **=** monto del pago, al centavo.
- Si el pago es **menor** que lo seleccionado: la última factura (o la que el admin elija) recibe un **pago parcial**; su saldo queda abierto.
- Si el pago es **mayor** que todo el saldo abierto del cliente (anticipo/pago en exceso): fuera de alcance del MVP. La UI lo dice claramente y sugiere registrarlo por el monto aplicable y anotar el excedente en notas.

> 🔴 **INFO REQUERIDA (Vlad)** — confirmar con el contador cómo manejan hoy los pagos en exceso o con diferencias de centavos (p. ej. el cliente redondeó la retención distinto).

### 2.5 Revertir
`POST /pagos/{id}/revertir` (solo si no hay REP vigente): borra las aplicaciones, restaura saldos y `estado_cobro`, `pago.estado = registrado`. Uso típico: se aplicó a facturas equivocadas.

## 3. Algoritmo de conciliación (`cobranza/conciliacion.py`)

Función pura, sin DB ni red: recibe facturas y monto, devuelve candidatos. Se trabaja **en centavos enteros**.

### 3.1 Entrada
```
facturas: [ { id, folio, fecha_emision, saldo_cents } ]   # facturas abiertas del cliente (saldo > 0)
objetivo_cents: int
tolerancia_cents: int          # configuracion["conciliacion.tolerancia"], default 100 ($1.00)
max_facturas: int              # default 60
tiempo_max_ms: int             # default 1500
```
La función solo necesita ids, fechas y saldos. La capa de servicio (`POST /cobranza/sugerencias`) **enriquece** después cada factura de la salida con su folio, total, saldo y **su servicio** (número, fecha y ruta), que es lo que el admin reconoce a simple vista.

### 3.2 Preparación
- Ordenar por `(fecha_emision, folio)` ascendente → define el orden "FIFO" y la noción de consecutivas.
- Si `objetivo > Σ saldos` → devolver `excede_saldo = objetivo − Σ` y solo la propuesta "pagar todo" (no hay combinación exacta posible).
- Si hay más de `max_facturas`, la búsqueda general (§3.4) usa las `max_facturas` más antiguas y lo reporta (`busqueda_completa = false`); las búsquedas rápidas (§3.3) usan todas.

### 3.3 Candidatos rápidos (O(n²), siempre se corren)
1. **Factura única** con saldo = objetivo.
2. **Prefijo FIFO**: las k más antiguas suman exactamente el objetivo (el caso más común: "pagó todo lo que debía hasta tal fecha").
3. **Ventana consecutiva**: facturas i..j consecutivas en orden de fecha que suman el objetivo (p. ej. "pagó la semana del 8 al 12").

### 3.4 Búsqueda general (subset sum exacto)
Para combinaciones no consecutivas. Clave de rendimiento y de UX: **agrupar facturas con el mismo saldo**. Si hay cinco facturas de $1,848.00, no se exploran las 10 formas de escoger dos; se decide "cuántas de ese monto" y se toman **las más antiguas** de ese grupo (forma canónica).

```python
def buscar(grupos, objetivo, tolerancia, deadline):
    # grupos: [(saldo_cents, [facturas del grupo ordenadas por fecha asc])], ordenados por saldo DESC
    # sufijo[i] = Σ saldo*len(facturas) de grupos[i:]  (máximo alcanzable desde i)
    exactas, aproximadas = [], []

    def dfs(i, restante, eleccion):              # eleccion: [(idx_grupo, k)]
        if time_now() > deadline: raise Timeout
        if restante == 0:
            exactas.append(expandir(eleccion)); return
        if -tolerancia <= restante < 0:
            # las facturas suman un poco MÁS que el pago: aplicable dejando un saldo mínimo en una de ellas
            aproximadas.append((expandir(eleccion), -restante)); return
        if restante < -tolerancia or i == len(grupos) or sufijo[i] < restante:
            return
        saldo, facts = grupos[i]
        k_max = min(len(facts), (restante + tolerancia) // saldo)
        for k in range(k_max, -1, -1):           # probar primero tomar más del monto grande
            dfs(i + 1, restante - k * saldo, eleccion + ([(i, k)] if k else []))

    # expandir((i, k)) = las k facturas más antiguas del grupo i
```
- Cortar al llegar a 200 soluciones exactas o al `deadline`; en ese caso `busqueda_completa = false`.
- Con el volumen real (≤ ~40 facturas abiertas por cliente) termina en milisegundos.
- Deduplicar soluciones (mismo conjunto de ids).

### 3.5 Ranking de soluciones exactas
Orden lexicográfico (menor es mejor), pensado para ser **explicable**:
1. `saltadas`: facturas abiertas **más antiguas** que la más reciente seleccionada y que **no** se seleccionaron. (Los clientes suelen pagar lo más viejo primero; FIFO puro = 0.)
2. `huecos`: número de "saltos" entre seleccionadas en el orden por fecha (consecutivas = 0).
3. `fecha` de la factura más reciente seleccionada (más antigua primero).
4. Número de facturas (menos primero).

Etiquetas para la UI: `fifo` (saltadas = 0), `consecutivas` (huecos = 0), `mismo_mes`, `unica_factura`.

### 3.6 Salida
```json
{
  "objetivo": "45320.00",
  "saldo_total_cliente": "120480.00",
  "exactas": [
    { "factura_ids": ["…","…","…"],
      "facturas": [
        { "factura_id": "…", "folio": "A-120", "fecha_emision": "2026-08-04", "total": "18480.00", "saldo": "18480.00",
          "servicio": { "id": "…", "numero": 101, "fecha": "2026-08-03", "ruta_resumen": "Planta Chemital → Guadalupe Limón" } }
      ],
      "aplicaciones": [ { "factura_id": "…", "monto": "…" } ],
      "suma": "45320.00",
      "etiquetas": ["fifo", "consecutivas", "mismo_mes"],
      "explicacion": "Las 3 facturas más antiguas, consecutivas (4–15 ago 2026)" }
  ],
  "total_exactas": 1,
  "ambigua": false,
  "nota_montos_iguales": false,
  "aproximadas": [ { "…": "…", "diferencia": "0.03", "factura_parcial_id": "…" } ],
  "fifo_parcial": { "aplicaciones": [ … ], "factura_parcial_id": "…", "monto_parcial": "2300.00" },
  "excede_saldo": null,
  "busqueda_completa": true,
  "facturas_consideradas": 34
}
```
- `exactas`: máximo 5, ya rankeadas.
- `facturas`: presente en **todos** los candidatos (exactas, aproximadas y FIFO parcial): el detalle de cada factura con su servicio, para corroborar.
- `ambigua = true` si hay **más de una** solución exacta distinta (después de la forma canónica). La UI lo advierte y pide al admin confirmar la elección.
- `nota_montos_iguales = true` si la elegida tomó k de un grupo con más de k facturas del mismo saldo ("hay facturas del mismo monto; se tomaron las más antiguas").
- `aproximadas`: solo si **no** hubo exactas; máximo 3, ordenadas por diferencia y luego por el ranking de §3.5. Solo se proponen combinaciones que suman **un poco más** que el pago (hasta la tolerancia): se aplican dejando esa diferencia como saldo en `factura_parcial_id` (la más reciente de la combinación). El caso típico es un cliente que redondeó distinto y pagó unos centavos menos. Si las facturas suman *menos* que el pago, no hay forma de cuadrar sin un excedente (§2.4).
- `fifo_parcial`: **siempre** presente (salvo `excede_saldo`): aplica completas las más antiguas mientras quepan y deja el remanente como pago parcial en la siguiente. Es la salida de emergencia cuando nada cuadra.

### 3.7 Qué hace la UI con cada caso
| Caso | UI |
|---|---|
| 1 exacta | Preselecciona y muestra "Coincidencia exacta" (verde) **con la lista de servicios que cubre** (folio, servicio #, fecha, ruta y monto), para corroborar. Un clic en "Aplicar y generar REP". |
| Varias exactas | Preselecciona la primera, banner ámbar "Hay N combinaciones que suman exacto", lista las alternativas con su explicación y sus servicios. |
| Solo aproximadas | Muestra "No hay combinación exacta; la más cercana difiere $0.03". Elegirla aplica el pago con la última factura como parcial. |
| Ninguna | Ofrece "Aplicar a las más antiguas (FIFO) con pago parcial" y la selección manual. |
| Excede saldo | Error explicativo (§2.4). |

## 4. Mapeo del REP (CFDI tipo P, Pagos 2.0)

`cobranza/rep_payload.py`, puro y testeable.

**Comprobante**: `TipoDeComprobante P`, `SubTotal 0`, `Total 0`, `Moneda XXX`, `Exportacion 01`, `LugarExpedicion` del emisor; mismo Emisor que las facturas; Receptor = cliente (`Rfc`, `Nombre`, `DomicilioFiscalReceptor`, `RegimenFiscalReceptor`, `UsoCFDI CP01`).
**Concepto único**: `ClaveProdServ 84111506`, `Cantidad 1`, `ClaveUnidad ACT`, `Descripcion "Pago"`, `ValorUnitario 0`, `Importe 0`, `ObjetoImp 01`.
**Complemento Pagos 2.0**:
- `Totales`: `TotalRetencionesIVA`, `TotalTrasladosBaseIVA16`, `TotalTrasladosImpuestoIVA16`, `MontoTotalPagos`.
- `Pago`: `FechaPago`, `FormaDePagoP`, `MonedaP MXN`, `TipoCambioP 1`, `Monto`, `NumOperacion?`, `RfcEmisorCtaOrd?`, `CtaOrdenante?`, `RfcEmisorCtaBen?`, `CtaBeneficiario?`.
- `DoctoRelacionado` (uno por aplicación): `IdDocumento` (UUID de la factura), `Serie?`, `Folio?`, `MonedaDR MXN`, `EquivalenciaDR 1`, `NumParcialidad`, `ImpSaldoAnt`, `ImpPagado`, `ImpSaldoInsoluto`, `ObjetoImpDR 02`, `ImpuestosDR` (§5).
- `ImpuestosP`: suma de los `ImpuestosDR` del pago (traslados IVA 16% con su base; retenciones IVA).

> **Verificado en sandbox (6 oct 2026):** el JSON es `Complemento.Payments[].RelatedDocuments[]`, sin `Items` en la raíz y **sin `ExchangeRate`** en pesos; `Totales` e `ImpuestosP` los calcula Facturama. Detalle en `backend/NOTES.md`.

Verificar en Facturama qué parte calcula su API (algunos PAC calculan `Totales`/`ImpuestosP`) y enviar solo lo que pida.

## 5. Impuestos proporcionales por documento relacionado

Por cada aplicación con `ImpPagado = p` sobre una factura con `subtotal S`, `total T`, `iva_trasladado IVA`, `iva_retenido RET`:
```
si p == T (pago completo en una sola parcialidad):
    base = S;  traslado = IVA;  retencion = RET
si saldo_insoluto == 0 (última parcialidad de varias):
    base = S − Σ bases de parcialidades anteriores        # absorbe el redondeo
    traslado = IVA − Σ traslados anteriores; retencion = RET − Σ retenciones anteriores
si no:
    base = round_half_up(p × S / T, 2)
    traslado = round_half_up(base × 0.16, 2)
    retencion = round_half_up(base × 0.04, 2) si receptor moral, si no 0
```
Así la suma de todas las parcialidades de una factura reproduce exactamente sus impuestos. Guardar `base/traslado/retencion` calculados en el `payload` del REP para que las siguientes parcialidades los lean.

## 6. Cancelación de REP

- `POST /reps/{id}/cancelar` con motivo (MVP: `02`). En 2026 **siempre** requiere aceptación del receptor; si no responde en 3 días hábiles se considera aceptada. Estados: `cancelacion_pendiente` → `cancelado` (o vuelve a `timbrado` si la rechaza). Consulta de estatus bajo demanda, igual que facturas (`01 §7`).
- Al quedar `cancelado`: `pago.estado = aplicado` (los saldos no cambian). Desde ahí: re-emitir REP, o revertir la aplicación (§2.5).
- Para cancelar una **factura** que ya tiene pagos: cancelar REP → revertir aplicación → cancelar factura (`04 §8`). La UI guía esa secuencia.

## 7. Vencimientos del REP

- `vence_rep(pago) = día 5 del mes siguiente a fecha_pago` (si cae sábado/domingo, el lunes siguiente; los días festivos no se calculan en MVP — la UI dice "vence el 5").
- "REP por emitir" = pagos `aplicado` sin REP vigente. Estados visuales: normal; "vence en ≤ 3 días" (warning); "vencido" (danger).
- Aparece en el dashboard (`/dashboard/pendientes`) y en Cobranza → Pagos.

## 8. Checklist de aceptación (tests de Fase 5)

- [ ] Conciliación: factura única exacta; prefijo FIFO; ventana consecutiva; combinación no consecutiva única; dos combinaciones exactas → `ambigua`; montos iguales → toma las más antiguas y `nota_montos_iguales`; diferencia de $0.03 → aproximada; sin coincidencia → `fifo_parcial`; objetivo > saldo total → `excede_saldo`.
- [ ] Ranking: entre dos exactas, gana la que salta menos facturas antiguas.
- [ ] La respuesta de `/cobranza/sugerencias` trae, por cada factura de cada candidato, su servicio (número, fecha y ruta).
- [ ] Rendimiento: 60 facturas aleatorias responde en < `tiempo_max_ms` y marca `busqueda_completa` correctamente.
- [ ] Aplicar: Σ ≠ monto → 422; parcialidades numeradas por factura; saldos y `estado_cobro` correctos; concurrencia (dos aplicaciones simultáneas sobre la misma factura no la dejan negativa).
- [ ] Revertir restaura saldos; bloqueado con REP vigente.
- [ ] REP: payload con un pago y N documentos; impuestos proporcionales y última parcialidad cuadrando al centavo; timbrado en sandbox con UUID, PDF y XML.
- [ ] Cancelar factura con REP vigente → 409; secuencia cancelar REP → revertir → cancelar factura funciona.
- [ ] Vencimiento: pago del 20 sep → vence 5 oct; pago del 28 feb → vence 5 mar (y corrimiento si cae en fin de semana).

> 🔴 **INFO REQUERIDA (Vlad)** — (1) un **REP real** (XML) de Elogistics o de su contador como fixture; (2) cómo avisan los clientes sus pagos hoy (correo del banco, estado de cuenta, remesa) — define si en el futuro conviene importar estados de cuenta; (3) si quieren registrar las cuentas bancarias ordenante/beneficiaria en el REP.
