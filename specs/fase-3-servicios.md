# Fase 3 · Servicios

> **Objetivo**: el "unir viajes". El admin agrupa uno o más viajes en un servicio, le pone el subtotal, y lo deja listo para facturar.
> **Depende de**: Fase 2 (viajes cerrados/registrados).
> **Entrega**: creación y gestión de servicios agrupando viajes, con estados y montos calculados.
> **Lee antes**: `02-data-model §3.9, §4` (máquinas de estado), `03-api-contract §8`.

## Historias de usuario

### H3.1 — Agrupar viajes en un servicio
Como admin, quiero unir varios viajes en un servicio, porque un servicio se factura como un solo CFDI.
**Criterios de aceptación**
- En la vista de un cliente, veo sus viajes **sin agrupar**, mostrados **agrupados por fecha**.
- Marco uno o más viajes y los agrupo en un servicio nuevo.
- Todos los viajes de un servicio deben ser del **mismo cliente** (validado; si no, error claro).
- El servicio nace en `estado=borrador`.
- A la derecha veo la ruta armada como línea de tiempo (origen de la recolección → destinos de las entregas).

### H3.2 — Capturar subtotal y ver montos
Como admin, quiero poner el subtotal y ver el total con impuestos, antes de facturar.
**Criterios de aceptación**
- Puedo capturar/editar el `subtotal` del servicio.
- El detalle muestra el preview de montos: subtotal, IVA 16%, retención 4% (si el cliente es moral), total (`04-facturacion-cfdi §3`).
- La descripción del concepto se autogenera desde unidad/origen/destino/fecha (`04 §2`).

### H3.3 — Editar y desagrupar
Como admin, quiero corregir un servicio en borrador, para arreglar errores antes de facturar.
**Criterios de aceptación**
- Mientras está en `borrador`, puedo agregar/quitar viajes y cambiar el subtotal.
- Puedo desagrupar: los viajes vuelven a "sin agrupar" (`servicio_id=null`).
- Un servicio `facturado` es **inmutable**: no se edita ni desagrupa hasta cancelar su factura (regla dura de `02-data-model §4`).

### H3.4 — Pasar a "listo"
Como admin, quiero marcar un servicio como listo, cuando ya tiene todo para facturar.
**Criterios de aceptación**
- Un servicio pasa a `listo` solo si: tiene ≥1 viaje, tiene `subtotal > 0`, y pasa la validación pre-timbrado sin errores (la validación completa se implementa en Fase 4; en Fase 3 basta la parte no-fiscal).
- El listado y el dashboard distinguen `borrador` / `listo`.

## Endpoints / pantallas
- Endpoints: `03-api-contract §8` (crear servicio, listar, detalle, editar, desagrupar).
- Pantallas admin: "Agrupar y facturar" (dos columnas: viajes sin agrupar por fecha ↔ servicio en construcción con timeline y montos) y "Servicios" (la base de datos filtrable por cliente/fecha/estado).

## Casos borde
- Intentar agrupar viajes de clientes distintos → `422`.
- Intentar editar/desagrupar un servicio facturado → `409`.
- Servicio sin subtotal no pasa a `listo`.
- Quitar el último viaje de un servicio → el servicio queda sin viajes (impedir pasar a listo).

## Definición de terminado
- [ ] Crear servicio agrupando viajes del mismo cliente.
- [ ] Editar/desagrupar solo en borrador; inmutable si facturado.
- [ ] Preview de montos correcto (incluida retención condicional).
- [ ] Listado de servicios filtrable y agrupado por fecha.
- [ ] Tests: agrupación misma-cliente, cálculo de montos, transición de estados, inmutabilidad post-factura.
