# Fase 5 · Cobranza y complemento de pago (REP)

> **Objetivo**: saber cuánto debe cada cliente, registrar sus pagos, **identificar automáticamente qué facturas pagó** cuando no lo dice, y emitir el REP en uno o dos clics antes del día 5.
> **Depende de**: Fase 4 (facturas timbradas).
> **Entrega**: sección Cobranza completa con REP timbrado en sandbox.
> **Lee antes**: `06` completo, `02 §3.14–3.17, §4, §5`, `03 §11`, `05 §5 (PaymentMeter, ReconciliationSuggestions, AgingBadge, DueBadge), §7.4`.

## Paso 0 — Spike de REP (de-risk)
Antes de las historias: script `backend/scripts/spike_rep.py` que timbra en sandbox un REP de una factura de prueba (pago total) y otro con dos parcialidades, para confirmar la estructura que espera Facturama (qué calcula su API y qué hay que enviar, `06 §4`). Anotar hallazgos en `06` o en `NOTES.md`.

## Historias de usuario

### H5.1 — Por cobrar por cliente
Como admin, quiero ver cuánto me debe cada cliente y qué facturas tiene abiertas.
**Criterios de aceptación**
- Tab "Por cobrar": lista de clientes ordenada por saldo (con "Todos") y tabla de facturas abiertas con folio, fecha, servicio, total, saldo y **AgingBadge** según `dias_credito`.
- Filtros en la URL: `cliente`, `mes` (de emisión), `anio` — los usa el dashboard (Fase 6).

### H5.2 — Registrar pago
Como admin, quiero capturar un depósito en segundos.
**Criterios de aceptación**
- Panel "Registrar pago" fijo a la derecha con el **monto enfocado**, fecha, forma de pago (default 03), referencia, comprobante opcional y notas.
- Atajo desde el detalle de una factura ("Registrar pago" con esa factura y su saldo).

### H5.3 — Conciliación automática
Como admin, quiero que el sistema me diga qué facturas suman exactamente el pago, porque algunos clientes no lo especifican.
**Criterios de aceptación**
- Al teclear el monto (debounce 300 ms) se llama `POST /cobranza/sugerencias`; algoritmo de `06 §3` en `cobranza/conciliacion.py` (función pura, centavos enteros).
- Candidatos según `06 §3.7`: exacta (verde, preseleccionada), varias exactas (banner ámbar y alternativas), aproximada (diferencia y factura parcial), FIFO parcial, excede saldo.
- Cada candidato —y siempre la **coincidencia exacta**— muestra **los servicios que cubre** (folio, servicio #, fecha, ruta y monto), para corroborar antes de aplicar; cada servicio enlaza a su detalle.
- "Usar" marca las facturas en la tabla; el admin puede marcar/desmarcar a mano y el **PaymentMeter** se actualiza en vivo.

### H5.4 — Aplicar y revertir
**Criterios de aceptación**
- Aplicar según `06 §2.3–2.4`: transacción con lock, Σ = monto al centavo, parcialidades numeradas por factura, saldos y `estado_cobro` actualizados.
- Si lo seleccionado excede el pago, elegir qué factura queda con pago parcial.
- Revertir (`06 §2.5`) solo sin REP vigente.

### H5.5 — Emitir y enviar el REP
Como admin, quiero generar el comprobante de pago con un clic.
**Criterios de aceptación**
- Botón principal **"Aplicar y generar REP"** (aplica + timbra) y secundario "Solo aplicar".
- `POST /pagos/{id}/rep`: payload de `06 §4–5` en `cobranza/rep_payload.py` (puro y testeable), idempotente por pago, PDF/XML a R2, `pago.estado = rep_emitido`.
- ConfirmDialog con cliente, monto, facturas (con su servicio) y parcialidades; tras timbrar: UUID, PDF/XML y "Enviar al cliente" (`POST /reps/{id}/enviar`, mismos destinatarios que la factura).

### H5.6 — Cancelar REP y cancelar una factura ya pagada
**Criterios de aceptación**
- `POST /reps/{id}/cancelar` según `06 §6` (siempre con aceptación del receptor en 2026; "en espera" igual que facturas; estatus bajo demanda).
- Al quedar cancelado: `pago.estado = aplicado`; desde ahí re-emitir REP o revertir.
- El detalle de una factura pagada guía la secuencia: cancelar REP → revertir aplicación → cancelar factura.

### H5.7 — REP por emitir y vencimientos
Como admin, quiero no pasarme del día 5.
**Criterios de aceptación**
- Tab "Pagos y REP": pagos con REP pendiente arriba, con **DueBadge** (`06 §7`); encabezado "N REP por emitir · vence el 5 oct".
- `GET /dashboard/pendientes` ya expone `rep_por_emitir` (se pinta en Fase 6).

### H5.8 — Pagadas e historial
**Criterios de aceptación**
- Tab "Pagadas": facturas con `estado_cobro = pagada`, filtrables por mes y cliente, con enlace a su REP.
- Detalle de pago (`/admin/cobranza/pagos/:id`): aplicaciones, REP vigente/históricos, comprobante bancario.

## Endpoints / pantallas
- Endpoints: `03 §11`.
- Pantallas: `05 §7.4`.

## INFO REQUERIDA (Vlad)
> 🔴 Un **REP real** como fixture; cómo avisan hoy los clientes sus pagos; si se registran cuentas bancarias en el REP; cómo manejan pagos en exceso o diferencias de centavos (`06 §2.4`).

## Casos borde
- Pago de un cliente sin facturas abiertas → mensaje claro; no se puede aplicar.
- Dos admins aplicando pagos a la misma factura a la vez → el lock evita saldo negativo; el segundo recibe `409` con el saldo actual.
- Factura cancelada después de tener pagos → imposible por la regla (`02 §5`).
- REP con error del PAC → `pago` sigue `aplicado`, REP `error` reintentable; el vencimiento sigue corriendo.
- Pago registrado con una fecha cuyo plazo de REP ya venció → aviso "el REP de este pago ya está vencido; emítelo hoy".

## Definición de terminado
- [ ] Spike de REP documentado.
- [ ] Tests de `06 §8` (conciliación, aplicación, REP, cancelación, vencimientos).
- [ ] Flujo completo en sandbox: registrar → sugerencia exacta → aplicar y generar REP → enviar.
- [ ] Conciliación < 1.5 s con 60 facturas.
