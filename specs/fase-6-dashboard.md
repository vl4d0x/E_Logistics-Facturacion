# Fase 6 · Dashboard y reportes

> **Objetivo**: un dashboard **como el de referencia** (ingresos por periodo, ingresos por mes, por cobrar por cliente, cancelaciones en espera), pero **interactivo**: cada parte azul (cobrado) o roja (por cobrar) lleva a la pantalla donde se administra, y el top de clientes se expande a **todos**. Más pendientes operativos y export a Excel. **Sin tarjetas de egresos ni de combustible** (decisión de Vlad).
> **Depende de**: Fase 5 (cobrado/por cobrar real), Fase 3 (inspecciones).
> **Entrega**: `/admin` con el dashboard completo y exports.
> **Lee antes**: `03 §12`, `05 §5 (Dashboard), §7.6`.

## Historias de usuario

### H6.1 — Pendientes operativos
**Criterios de aceptación**
- 4 tiles clicables: Por facturar (con "N anticipadas" cuando hay servicios con la casilla sin timbrar), Acuses faltantes, REP por emitir (con el vencimiento más próximo y color según `06 §7`), Inspecciones con fallas (`05 §7.6`).
- Si faltan costos y tarifas por capturar, el aviso **SetupReminder** aparece sobre los tiles (`07 §5`).

### H6.2 — Ingresos por periodo
**Criterios de aceptación**
- Dona grande del mes seleccionado (Cobrado / Por cobrar, total facturado al centro), dos donas chicas de los meses anteriores (clic = seleccionarlas) y leyenda con montos.
- Clic en Cobrado → Cobranza "Pagadas" del mes; clic en Por cobrar → Cobranza "Por cobrar" del mes.

### H6.3 — Ingresos por mes
**Criterios de aceptación**
- Barras apiladas de 12 meses (Cobrado + Por cobrar = Facturado) con selector de año; totales del año al pie.
- Clic en un segmento → Cobranza filtrada por ese mes y estado; clic en la barra completa → Facturas del mes.

### H6.4 — Por cobrar por cliente
**Criterios de aceptación**
- Top 5 clientes por saldo con selector de año (incluye "Todos los años").
- **"Ver todos (N clientes)"** expande la tarjeta con todos los clientes con saldo, ordenados, con scroll y total; "Ver menos" la contrae.
- Clic en un cliente → Cobranza "Por cobrar" de ese cliente.

### H6.5 — En espera
**Criterios de aceptación**
- Número de cancelaciones (facturas y REP) esperando aceptación del receptor; clic → drawer con cada solicitud (factura o REP), fecha de solicitud y enlace a su detalle.
- Al cargar el widget, el backend actualiza el estatus de esas cancelaciones con el throttle de `01 §7`.

### H6.6 — Frescura y consistencia
**Criterios de aceptación**
- Cada tarjeta muestra "Actualizado a las HH:MM" y botón de refrescar (como la referencia).
- Ingresos atribuidos al **mes de emisión**; facturas canceladas excluidas; `facturado = cobrado + por_cobrar` por mes (test).
- Meses sin datos → ceros, no errores.

### H6.7 — Export a Excel
**Criterios de aceptación**
- `GET /export/servicios.xlsx` con filtros: fecha, #, cliente, ruta, unidad, operador, km, subtotal, IVA, retención, total, estado, UUID, estado de cobro, saldo, fechas de pago y UUID de REP.
- Rango vacío → archivo con encabezados.

## Endpoints / pantallas
- Endpoints: `03 §12`.
- Pantalla: `05 §7.6`; botón de export en Servicios.

## INFO REQUERIDA (Vlad)
> 🔴 Columnas que pide el contador en el Excel.
>
> Ya decidido por Vlad: el dashboard **no** incluye la mitad de egresos de la referencia ni el gasto en combustible.

## Casos borde
- Factura en `cancelacion_pendiente` → cuenta como vigente hasta que el SAT confirme.
- Pago revertido → deja de contar como cobrado.
- Cliente archivado con saldo → sigue apareciendo en Por cobrar.

## Definición de terminado
- [ ] Las 4 tarjetas de ingresos + pendientes, con el mapa de clics de `05 §7.6`.
- [ ] "Ver todos" en Por cobrar.
- [ ] Leyendas como botones accesibles.
- [ ] Export filtrable.
- [ ] Tests: agregados por mes con invariante, atribución por mes de emisión, top/todos, ceros, conteo de "por facturar" con anticipados, export con y sin datos.
