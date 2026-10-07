# Fase 2 · Servicios y viajes

> **Objetivo**: el nuevo corazón operativo. El admin **crea un servicio y, dentro de él, sus viajes** (ya no hay viajes sueltos ni paso de "agrupar"). También puede editar, duplicar, cancelar, subir acuses y cerrar viajes en nombre del operador, para que la operación nunca dependa de la PWA.
> **Depende de**: Fase 1 (catálogos, lugares).
> **Entrega**: pantallas Servicios (lista), Nuevo/editar servicio y Detalle de servicio, de punta a punta con datos de catálogo.
> **Lee antes**: `00 §3`, `02 §3.7–3.10, §4, §5`, `03 §6`, `04 §1.1–1.2` (por qué existe la casilla), `05 §5 (ServiceBuilder, LugarSelect, AcuseViewer), §7.1`.

## Historias de usuario

### H2.1 — Crear servicio con sus viajes
Como admin, quiero registrar un servicio completo en una sola pantalla, para asignarlo y no tener que agruparlo después.
**Criterios de aceptación**
- Formulario con cliente, fecha, **unidad de registro** (por apodo), operador, notas, y la lista de viajes (**ServiceBuilder**).
- La unidad es una sola por servicio: aunque físicamente participen varias camionetas, el admin elige la que queda en el registro y en la factura (el campo lleva esa ayuda).
- Al elegir cliente se precarga "1 recolección en su origen predeterminado + 1 entrega vacía"; se pueden agregar recolecciones/entregas, cambiar el tipo, reordenar y quitar.
- Cada viaje exige origen y/o destino según su tipo (`02 §3.8`); los lugares se eligen con **LugarSelect** (del cliente + globales) y se pueden crear sin salir de la pantalla.
- La distancia de cada viaje con destino se precarga con la última usada para ese par de lugares (`GET /lugares/distancia-sugerida`) y es editable.
- El precio (subtotal) es **opcional** —obligatorio solo con timbrado anticipado (H2.7)— (PriceField `compact`; la sugerencia automática llega en Fase 4).
- Panel derecho: timeline de la ruta, datos que irán a la Carta Porte (solo lectura) y qué se le pedirá al operador según el cliente.
- Si la unidad ya tiene otro servicio esa fecha → aviso (no bloquea).
- Al guardar: `estado = programado`, número legible (`#128`), toast y redirección al detalle.
- `POST /servicios` acepta servicio + viajes en una sola llamada y una transacción.

### H2.2 — Lista de servicios
Como admin, quiero ver todos los servicios por estado y fecha, para saber qué está pendiente.
**Criterios de aceptación**
- Tabs con conteo: Todos · Programados · En curso · **Por facturar** · Facturados · Cancelados, definidas por `vista` (`03 §6`). "Por facturar" = pendiente de factura y (terminado o con timbrado anticipado).
- Filtros: cliente, operador, unidad, fechas, "acuses pendientes"; buscador por número, cliente o lugar. Filtros en la URL.
- Tabla agrupada por fecha: #, cliente, ruta resumida, unidad · operador, viajes terminados/total, acuses completos/requeridos, total (si hay precio), estado (badge de operación + badge de facturación + etiqueta "Anticipada") y menú.

### H2.3 — Detalle y edición
Como admin, quiero ver y corregir un servicio antes de facturarlo.
**Criterios de aceptación**
- Detalle con encabezado, barra de progreso de estado, viajes (estado, mercancías, acuses) y acciones según `acciones_permitidas`.
- Editar cabecera (unidad, operador, fecha, notas, precio) y viajes (agregar, editar, reordenar, quitar) mientras el servicio no esté cancelado **ni tenga factura vigente**.
- Un viaje `terminado` no se puede quitar sin "Reabrir"; sus datos (lugar, distancia, mercancías) sí se corrigen. Reabrir un viaje de un servicio `terminado` lo regresa a `en_curso` (`02 §4`).
- Con factura vigente, los **datos fiscales** quedan en solo lectura con el motivo visible (`409 servicio_facturado` por API); los operativos (acuses, terminar viajes, reportes) siguen abiertos. Un servicio `cancelado` es de solo lectura.
- El detalle muestra dos carriles de progreso: Operación y Cobro (`05 §7.1`).

### H2.4 — Acuses y cierre desde escritorio (fallback del operador)
Como admin, quiero subir el acuse escaneado o capturar el folio desde la oficina, y terminar un viaje si el operador no pudo usar la app.
**Criterios de aceptación**
- En cada viaje de entrega: subir una o varias páginas (imagen o PDF) o capturar el folio, según `cliente.modo_acuse`; ver/quitar acuses.
- "Terminar en nombre del operador": mismo formulario que la PWA (mercancías y kg, acuse, hora); `terminado_por` = admin.
- "Marcar servicio como terminado" cuando todos los viajes están terminados aunque no haya reporte del operador (`terminado_por_admin = true`).
- Un viaje puede terminarse sin el acuse requerido (llega después); el servicio queda con "acuses pendientes".

### H2.5 — Duplicar servicio
Como admin, quiero copiar un servicio recurrente a otra fecha, porque muchas rutas se repiten.
**Criterios de aceptación**
- "Duplicar" pide la fecha y crea un servicio `programado` con mismo cliente, unidad, operador, viajes, lugares y distancias; sin precio, km reportados, mercancías, acuses, reportes ni timbrado anticipado.
- Abre el nuevo servicio en modo edición.

### H2.6 — Cancelar servicio
Como admin, quiero cancelar un servicio que no se realizó, para que no aparezca como pendiente.
**Criterios de aceptación**
- Solo sin factura vigente; pide motivo; `estado = cancelado`; visible en la tab Cancelados.

### H2.7 — Marcar un servicio para timbrar antes
Como admin, quiero indicar al crear el servicio que el cliente necesita la Carta Porte antes del traslado, para poder timbrarla sin esperar a que termine.
**Criterios de aceptación**
- Casilla **"Timbrar antes del servicio"** en Nuevo/editar servicio, **apagada por defecto** (`servicio.timbrado_anticipado`).
- Al marcarla: el **subtotal es obligatorio** (`422` sin él); el ServiceBuilder muestra la hora programada de salida/llegada de cada viaje y las mercancías de cada entrega (se guardan con el servicio; se exigen al timbrar, no al guardar).
- El servicio queda con la etiqueta "Anticipada" y aparece en la tab "Por facturar" desde que se crea.
- Se puede desmarcar mientras no haya factura vigente.
- En esta fase la casilla **solo guarda datos**. El timbrado y el botón "Crear y revisar para timbrar" se conectan en la Fase 4 (H4.11); mientras tanto el primario sigue siendo "Crear servicio".

## Endpoints / pantallas
- Endpoints: `03 §6` (incluye `GET /servicios/conteos`).
- Pantallas: `05 §7.1`. El detalle deja el espacio del **OperatorReportCard** (se llena en Fase 3).
- Actualizar `contar_uso` de los catálogos (Fase 1) para contar servicios y viajes, y bloquear archivar unidad/operador/cliente/lugar con servicios `programado`/`en_curso`.

## INFO REQUERIDA (Vlad)
> 🔴 Ninguna. Ya confirmado por Vlad: aunque en la vida real participen varias camionetas, el admin elige **una unidad de registro** por servicio (`00 §3`).

## Casos borde
- Servicio sin viajes → `422`.
- Timbrado anticipado marcado sin subtotal → `422` junto al campo.
- Entrega sin destino / recolección sin origen → `422` en el viaje.
- Lugar de otro cliente (no global) → `422`.
- Reordenar con ids ajenos al servicio → `422`.
- Editar un servicio que el operador tiene offline: se permite; si luego el operador termina un viaje que ya no existe, su cola se detiene con un error explicativo (Fase 3).
- Dos admins editando el mismo servicio: gana el último en guardar (volumen bajo); el detalle se refresca al enfocar la ventana.

## Definición de terminado
- [ ] **Responsivo** (tablet 820 px y teléfono 390 px sin scroll horizontal; `05 §3.1`, auditoría con `frontend/scripts/audit-responsive.mjs`).
- [ ] Crear servicio con N viajes en una transacción; número legible.
- [ ] Lista con tabs/conteos, filtros en URL y agrupación por fecha.
- [ ] Edición restringida por estado y por factura vigente; reabrir viajes.
- [ ] Casilla de timbrado anticipado (apagada por defecto) con subtotal obligatorio, horas programadas y mercancías.
- [ ] Acuses (escaneo multipágina / folio) y cierre desde escritorio.
- [ ] Duplicar y cancelar.
- [ ] Tests: validación por tipo de viaje, transacción de creación, bloqueo de datos fiscales con factura vigente (simulada) y datos operativos abiertos, reordenamiento, duplicado, regla de acuse por modo, vistas y conteos, timbrado anticipado exige subtotal, reabrir viaje regresa el servicio a `en_curso`, conteo de uso en catálogos.
