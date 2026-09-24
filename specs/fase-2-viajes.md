# Fase 2 · Viajes

> **Objetivo**: la captura operativa completa. El admin registra viajes; el operador los ve y los cierra en campo, con **sincronización offline**.
> **Depende de**: Fase 1 (catálogos).
> **Entrega**: viajes registrables por admin y cerrables por operador desde la PWA, offline incluido.
> **Lee antes**: `02-data-model §3.6-3.8`, `03-api-contract §6-7`, `01-architecture §6` (offline).

## Historias de usuario — Admin

### H2.1 — Registrar viaje
Como admin, quiero registrar un viaje con lo mínimo, para asignárselo a un operador.
**Criterios de aceptación**
- Formulario: tipo de viaje (recolección / entrega / recolección y entrega), cliente, fecha, unidad (por apodo), operador, y origen y/o destino según el tipo.
- Según el tipo, la forma exige: recolección→origen; entrega→destino; ambas→los dos (`02-data-model §5`).
- El **subtotal se puede dejar vacío** al registrar (se captura al facturar) y no bloquea el registro.
- Al guardar, el viaje queda `estado=asignado`, `servicio_id=null`.
- Un panel muestra qué se inferirá para la Carta Porte (placa, config, permiso, licencia) desde la unidad y el operador — solo lectura.

### H2.2 — Ver y editar viajes
Como admin, quiero ver los viajes y filtrarlos, para gestionarlos y agruparlos después.
**Criterios de aceptación**
- Listado filtrable por cliente, estado, fecha, operador, y "sin agrupar".
- Los viajes se muestran **agrupados por fecha** (encabezado de día + viajes de ese día).
- Puedo editar un viaje mientras no pertenezca a un servicio ya facturado.

## Historias de usuario — Operador (PWA, offline)

### H2.3 — Ver mis viajes
Como operador, quiero ver los viajes que tengo asignados, incluso sin señal.
**Criterios de aceptación**
- `GET /operador/viajes` devuelve **solo** los viajes del operador autenticado (el server filtra por `user.operador_id`); nunca los de otro.
- Cada viaje muestra: cliente, unidad (apodo), origen/destino, notas, y qué exige su cierre (según `cliente.modo_acuse`).
- La lista se cachea para verse **offline**.

### H2.4 — Cerrar viaje
Como operador, quiero cerrar un viaje en campo, para reportar que terminó.
**Criterios de aceptación**
- Botón "Servicio terminado". Según el tipo/cliente:
  - Si transportó mercancía: selecciona mercancía(s) de la lista precargada del cliente y captura kg.
  - Modo **escaneo**: debe subir foto del acuse.
  - Modo **referencia**: captura el folio/referencia (sin foto).
  - Modo **ninguno** (p. ej. solo fue a cargar): marca terminado sin adjunto.
- Al cerrar, `estado=cerrado`, `cerrado_at` se registra.
- Campos opcionales: hora de llegada, notas.
- Validación de acuse según `cliente.modo_acuse` (`02-data-model §5`): sin el acuse requerido, no se considera cerrado.

### H2.5 — Offline e idempotencia
Como operador sin señal, quiero cerrar viajes y que se sincronicen solos al reconectar, sin duplicar.
**Criterios de aceptación**
- Sin conexión, el cierre (y la foto) se **encolan en IndexedDB**; la UI marca el viaje como "pendiente de sincronizar".
- Cada acción lleva un `client_action_id` (UUID generado en el teléfono).
- Al reconectar (evento `online` o reapertura de la app), la cola se reproduce en orden contra la API.
- `POST /operador/viajes/{id}/cerrar` es **idempotente**: reenviar el mismo `client_action_id` responde `200` con el estado actual, sin crear duplicados (`01-architecture §6`, `03-api-contract §7`).
- La foto del acuse se sube al reconectar (multipart al backend → R2).

## Casos borde
- Operador intenta cerrar un viaje que no es suyo → `403`.
- Cierre offline reproducido dos veces → una sola aplicación (idempotencia).
- Foto grande / formato no imagen → validar tamaño/tipo, comprimir en cliente si aplica.
- Pérdida de señal a mitad de subida → reintento seguro por `client_action_id`.
- Cliente en modo escaneo pero el operador solo recolectó (sin entrega) → no exigir acuse en ese viaje de recolección.

## INFO REQUERIDA (Vlad)
> 🔴 (Ninguna nueva; usa catálogos de Fase 1.) Confirmar si se usará el estado intermedio `en_curso` o el cierre es directo `asignado→cerrado`.

## Definición de terminado
- [ ] Admin registra viajes con la forma adaptada al tipo.
- [ ] Operador ve solo los suyos y los cierra en los 3 modos de acuse.
- [ ] Offline: cola, replay y idempotencia funcionando (test que reenvía la misma acción).
- [ ] Listados agrupados por fecha.
- [ ] Tests: filtrado por operador, validación de acuse por modo, idempotencia del cierre.
