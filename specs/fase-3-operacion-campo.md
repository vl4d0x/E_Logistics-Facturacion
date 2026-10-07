# Fase 3 · Operación en campo (PWA del operador)

> **Objetivo**: que el operador ejecute el servicio desde su celular, con o sin señal: **inspección de salida → terminar cada viaje (mercancía + acuse/folio) → cierre del servicio (km por viaje, gasolina al llegar, cargas de gasolina)**. Y que el admin vea esos reportes.
> **Depende de**: Fase 2 (servicios con viajes), Fase 1 (unidad con tipo de medidor, mercancías).
> **Entrega**: PWA instalable con el flujo completo offline + OperatorReportCard en el detalle del servicio.
> **Lee antes**: `01 §6` (offline), `02 §3.8–3.13`, `03 §7`, `05 §5 (ChecklistToggle, FuelGauge, FuelLoadForm, OperatorReportCard), §8`.

## Decisión de diseño (confirmada por Vlad, 2 oct 2026)
Vlad pidió "un formulario al iniciar y al terminar". Como el reporte final incluye **los km del primer viaje, del segundo, etc.** y la carga de gasolina es "al final del servicio", se interpretó así:
- **Inspección de salida**: una vez por servicio, antes del primer viaje (revisa la camioneta, que es una sola por servicio).
- **Terminar viaje**: por cada viaje (mercancía, acuse o folio, hora).
- **Cierre del servicio**: al final, con km de cada viaje, gasolina al llegar, odómetro y cargas.
Se agregaron dos datos que habilitan el monitoreo futuro de gasolina (`00 §9`): **gasolina al salir** (en la inspección) y **odómetro** al salir y al llegar (opcional).

Todo el reporte se registra contra la **unidad de registro** del servicio. Un servicio **timbrado por anticipado** se ejecuta exactamente igual: la factura no bloquea nada de este flujo (`02 §4`).

## Historias de usuario

### H3.1 — Mis servicios (offline)
Como operador, quiero ver mis servicios de hoy y próximos aunque no tenga señal.
**Criterios de aceptación**
- `GET /operador/servicios` devuelve **solo** los del operador autenticado (`403` al pedir uno ajeno).
- Secciones Hoy / Próximos / Terminados (7 días); card con #, cliente, unidad, ruta y estado ("Por iniciar", "En curso · viaje 2 de 3", "Terminado").
- La respuesta trae todo lo necesario para trabajar offline (lugares con referencia, mercancías del cliente sin claves SAT, modo de acuse, medidor de la unidad) y se persiste en el teléfono.

### H3.2 — Inspección de salida
Como operador, quiero registrar la revisión de la camioneta antes de salir.
**Criterios de aceptación**
- 8 preguntas Sí/No sin respuesta por defecto: unidad limpia, certificado de fumigación vigente, botiquín, casco y chaleco, nivel de aceite óptimo, nivel de anticongelante óptimo, neumáticos en buen estado, carga de extintor óptima.
- **Gasolina al salir** con el FuelGauge de su unidad (aguja o barras); odómetro opcional; observaciones opcionales (si hubo algún "No", el campo invita a describirlo).
- "Iniciar servicio" solo con las 8 respondidas y el medidor puesto; al enviarse: `inspeccion_salida` + `servicio.estado = en_curso` + `iniciado_at`.
- Un "No" **no bloquea** la salida: se guarda y el admin lo ve (warning en el detalle y en el dashboard).

### H3.3 — Terminar viaje
Como operador, quiero reportar cada viaje al terminarlo.
**Criterios de aceptación**
- Solo con el servicio iniciado; en orden sugerido, pero se puede terminar cualquiera pendiente.
- Entregas: elegir mercancía(s) de la lista del cliente, cantidad y kg (precargado con el peso sugerido). Si el admin ya las capturó, llegan precargadas y se pueden ajustar; si el servicio ya está facturado (timbrado anticipado), se muestran en **solo lectura** y no se envían. Recolecciones: sin mercancía ni acuse.
- Acuse según `cliente.modo_acuse`: **escaneo** → foto(s) con CameraCapture (varias páginas, compresión en cliente); **referencia** → folio; **ninguno** → nada. Si falta el acuse requerido, se puede terminar igual con aviso "El admin lo tendrá que subir" (no bloquea la operación; bloquea el timbrado).
- Hora de llegada precargada con la actual; notas opcionales.
- `viaje.estado = terminado`, `terminado_at`.

### H3.4 — Cierre del servicio
Como operador, quiero entregar mi reporte final al terminar el servicio.
**Criterios de aceptación**
- Disponible cuando todos los viajes están terminados.
- **Km por viaje**: una fila por viaje ("Viaje 1 · Recolección · Planta Chemital"), todas obligatorias (≥ 0), con total.
- **Gasolina al llegar** (FuelGauge). Odómetro al llegar opcional; si hay odómetro de salida y de llegada, se muestra el recorrido y su diferencia contra la suma de km (informativo).
- **¿Cargaste gasolina?** Sí/No. Si sí: una o más cargas con litros, precio por litro e importe (con dos se calcula el tercero; aviso si no cuadran por más de $1.00), foto del ticket opcional; total de litros y $.
- Al enviarse: `reporte_cierre`, `viaje.km_reportado` por viaje, `carga_combustible` por carga, `servicio.estado = terminado`, `terminado_at`.

### H3.5 — Medidor de gasolina (FuelGauge)
Como operador, quiero marcar la gasolina como se ve en mi tablero, sin traducirla a porcentaje.
**Criterios de aceptación**
- Modo aguja: semicírculo con marcas en octavos; tocar el arco, arrastrar la aguja o usar `−`/`+`; texto "½ tanque".
- Modo barras: N barras según la unidad; tocar la barra k llena 1..k; botón "Vacío"; texto "5 de 8 barras".
- Slider accesible (`role="slider"`, teclado).
- El backend valida la lectura contra la unidad (tipo y total de barras) y calcula `nivel_combustible` 0–1.

### H3.6 — Offline e idempotencia
Como operador sin señal, quiero que lo que capturo se envíe solo al reconectar, sin duplicarse.
**Criterios de aceptación**
- Las 5 acciones (`iniciar`, `terminar` viaje, `acuse`, `cerrar`, `ticket`) se encolan en IndexedDB con `client_action_id` (las cargas con `id` generado en el teléfono); fotos como Blob.
- Replay FIFO al reconectar y al abrir la app; reintento con backoff ante errores de red.
- Error de negocio → la cola se detiene en esa acción y la UI la muestra con qué hacer; las siguientes esperan.
- El servidor deduplica: reenviar la misma acción responde `200` con el estado actual.
- La UI avanza el flujo de inmediato ("Guardado, se enviará al reconectar") y muestra `PendingBadge`.

### H3.7 — Reportes del operador en el panel admin
Como admin, quiero ver la inspección, el cierre y las cargas de gasolina de cada servicio.
**Criterios de aceptación**
- **OperatorReportCard** en el detalle del servicio (`05 §5`): ítems ✓/✕, observaciones, medidores en solo lectura, odómetros, km por viaje, cargas con miniatura del ticket y total.
- Servicios con inspección con fallas: badge en la lista y filtro `inspeccion_fallas=true` (lo usa el dashboard en Fase 6).
- El admin puede corregir o borrar una carga mal capturada (`PATCH/DELETE /cargas/{id}`); no puede editar `km_reportado`.

## Endpoints / pantallas
- Endpoints: `03 §7`; `PATCH/DELETE /cargas/{id}` (`03 §6`).
- Pantallas: `05 §8` (operador) y OperatorReportCard en `05 §7.1`.

## INFO REQUERIDA (Vlad)
> 🔴 (1) Si algún "No" del checklist debe **impedir** salir (hoy no bloquea). (2) ¿El odómetro debe ser obligatorio? (Recomendado para el monitoreo futuro.) (3) Foto del tablero de cada camioneta para configurar su medidor.

## Casos borde
- Terminar un viaje de un servicio no iniciado → `409 servicio_no_iniciado` (la cola respeta el orden, así que solo pasa si el admin cambió algo).
- El admin borró o reabrió un viaje que el operador tenía en cola → error explicativo, sin perder el resto de la cola.
- Foto no imagen o > 10 MB tras compresión → rechazo con mensaje claro.
- Lectura de barras con un total distinto al de la unidad (se reconfiguró) → `422`; la app refresca el servicio y pide volver a marcar.
- El operador cierra sesión con acciones en cola → advertir; no borrar la cola sin confirmación.
- Dos dispositivos del mismo operador → la idempotencia evita duplicados; el primer cierre válido gana y el segundo recibe el estado actual.

## Definición de terminado
- [ ] **Responsivo** (tablet 820 px y teléfono 390 px sin scroll horizontal; `05 §3.1`, auditoría con `frontend/scripts/audit-responsive.mjs`).
- [ ] Flujo completo Inspección → Viajes → Cierre en la PWA, offline incluido.
- [ ] FuelGauge en modo aguja y barras, con lectura validada en backend.
- [ ] Cargas con cálculo del tercer valor y ticket opcional.
- [ ] Reportes visibles para el admin; corrección de cargas.
- [ ] Tests: filtrado por operador; idempotencia de las 5 acciones (reenvío doble); orden de la cola y detención ante error de negocio; validación de lectura del medidor; cierre exige viajes terminados; km por viaje en `km_reportado`; flujo completo sobre un servicio con factura vigente (anticipado) sin poder cambiar sus mercancías.
