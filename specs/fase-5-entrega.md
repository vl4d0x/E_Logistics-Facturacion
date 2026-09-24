# Fase 5 · Entrega

> **Objetivo**: cerrar el ciclo — enviar la factura al cliente, cancelar cuando haga falta, ver el negocio en el dashboard y exportar a Excel.
> **Depende de**: Fase 4 (facturas timbradas).
> **Entrega**: envío por correo con adjuntos, cancelación ante el SAT, dashboard de ingresos/pendientes y export a Excel.
> **Lee antes**: `03-api-contract §9-10`, `04-facturacion-cfdi §8` (cancelación), `02-data-model §3.10`.

## Historias de usuario

### H5.1 — Enviar factura por correo
Como admin, quiero enviar la factura al cliente con sus adjuntos, para completar el servicio.
**Criterios de aceptación**
- `POST /facturas/{id}/enviar` manda correo (Resend) al `email_facturacion` del cliente (o `to` explícito).
- Adjunta **XML + PDF**; si el cliente es modo **escaneo**, adjunta también el acuse escaneado; si es **referencia**, no adjunta acuse (la referencia va en el cuerpo/registro).
- Registra `enviado_at`; el estado de envío (enviado/rebotado) es visible.
- Plantilla de correo simple y clara, con datos del servicio.

### H5.2 — Cancelar factura
Como admin, quiero cancelar una factura ante el SAT, para poder corregir un servicio ya facturado.
**Criterios de aceptación**
- `POST /facturas/{id}/cancelar` con `motivo ∈ {01,02,03,04}`; motivo `01` exige `uuid_sustitucion` (`04 §8`).
- Llama a la cancelación de Facturama; guarda `motivo_cancelacion`, `uuid_sustitucion`, `estado=cancelada` y el acuse de cancelación (XML del SAT) en R2.
- Al confirmarse, el servicio pasa `facturado → cancelado` y queda editable (`cancelado → borrador` al re-editar).
- Un servicio facturado solo se puede modificar por esta vía (regla dura).

### H5.3 — Dashboard
Como admin, quiero ver ingresos y pendientes de un vistazo, para saber qué me falta.
**Criterios de aceptación**
- `GET /dashboard/resumen` devuelve: ingresos del mes/trimestre/año y por cobrar (PPD); ingresos por mes (para la gráfica); pendientes (viajes sin agrupar, servicios listos, servicios sin acuse); y la lista de servicios listos para facturar.
- Los montos son consistentes con las facturas timbradas.
- La pantalla sigue el diseño aprobado (tarjetas de ingresos, mini-gráfica, tiles de pendientes, lista).

### H5.4 — Export a Excel
Como admin, quiero exportar los servicios a Excel, para conciliar con contabilidad.
**Criterios de aceptación**
- `GET /export/servicios.xlsx` con filtros (fecha, cliente, estado) devuelve un `.xlsx` (openpyxl/pandas).
- Columnas útiles: fecha, cliente, ruta, viajes, subtotal, IVA, retención, total, estado, UUID.

## Endpoints / pantallas
- Endpoints: `03-api-contract §9-10`.
- Pantallas admin: detalle de factura (UUID, PDF/XML, botón enviar y cancelar), dashboard, y botón de export en el listado de servicios.

## INFO REQUERIDA (Vlad)
> 🔴 API key de **Resend** y correo/dominio remitente verificado (`EMAIL_FROM`). Texto/plantilla del correo si quiere uno específico. Confirmar qué columnas quiere en el Excel para contabilidad.

## Casos borde
- Correo rebota (email inválido) → registrar el fallo, permitir reintento/edición del destinatario.
- Cancelar una factura ya cancelada → `409`.
- Cancelación con motivo 01 sin `uuid_sustitucion` → `422`.
- Dashboard sin datos (mes sin facturas) → ceros, no error.
- Export con rango vacío → archivo con solo encabezados.

## Definición de terminado
- [ ] Envío por correo con adjuntos según modo de acuse del cliente.
- [ ] Cancelación ante SAT con motivos y acuse guardado; servicio vuelve a editable.
- [ ] Dashboard con ingresos (mes/trimestre/año) y pendientes.
- [ ] Export a Excel filtrable.
- [ ] Tests: adjuntos por modo de acuse, reglas de motivo de cancelación, agregados del dashboard.

---

## Backlog (post-MVP, NO en este alcance)
- **REP (complemento de pago)**: emitir CFDI tipo P al recibir pago de facturas PPD, referenciando el UUID. Tabla `pago_rep` ya modelada.
- **Plantillas de servicio recurrente**: clientes/rutas semanales a un clic.
