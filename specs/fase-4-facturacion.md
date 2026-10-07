# Fase 4 · Facturación

> **Objetivo**: convertir un servicio "por facturar" en un CFDI 4.0 + Carta Porte 3.1 timbrado, desde una pantalla donde el admin **ve todo precargado, revisa el acuse, ajusta el subtotal sugerido y timbra**. Incluye el **timbrado anticipado** (antes del traslado, para clientes que lo piden), la descarga de PDF/XML, el envío por correo y la cancelación con aceptación del receptor.
> **Depende de**: Fase 3 (reportes del operador), Fase 2 (servicios), Fase 0 (spike Facturama).
> **Entrega**: facturación real en sandbox de punta a punta.
> **Lee antes**: `04` completo (en especial §1.1–1.2 y §5), `07` completo, `03 §8–10`, `05 §5 (PriceField, SuggestionBreakdown, SetupReminder, MoneyBreakdown, AcuseViewer), §7.2, §7.3`.

## Orden sugerido de implementación
1. `taxes.py` + `payload.py` + timbrado contra sandbox (reutilizando el spike) con el test del fixture real.
2. Validación pre-timbrado.
3. Pantalla Facturar (sin sugerencia).
4. Sugeridor de precio + tarifas + configuración.
5. Envío por correo.
6. Lista/detalle de facturas y cancelación.
7. Timbrado anticipado (reutiliza todo lo anterior con otro modo de validación).

## Historias de usuario

### H4.1 — Cálculo de impuestos
**Criterios de aceptación**
- `calcular_impuestos(subtotal, regimen)`: IVA 16% siempre; retención 4% solo moral; `Decimal`, `ROUND_HALF_UP` (`04 §3`).
- `subtotal_desde_total(total, regimen)` (`04 §3.1`).
- Misma lógica en `frontend/src/lib/money.ts` con tests espejo (mismos casos, mismos resultados).
- `POST /impuestos/preview`.

### H4.2 — Payload CFDI + Carta Porte
**Criterios de aceptación**
- Emisor desde config; concepto con descripción autogenerada o editada (`04 §2`).
- Ubicaciones desde los viajes en orden, con `IDUbicacion`, fechas y distancias (`04 §4.2`); Domicilio desde `lugar`.
- Mercancías de todas las entregas; Autotransporte de `servicio.unidad`; Figura de `servicio.operador`.
- Vive en `facturacion/payload.py`, testeable sin red; test de equivalencia contra el fixture del CFDI real.

### H4.3 — Validación pre-timbrado
**Criterios de aceptación**
- `GET /servicios/{id}/validar` implementa **todas** las reglas de `04 §5`, cada una con `campo` para que la UI lleve a la sección.
- Errores bloquean; warnings permiten continuar.

### H4.4 — Pantalla "Facturar"
Como admin, quiero ver todos los datos precargados y el acuse en una sola pantalla y cambiar el precio en segundos, para facturar sin abrir otro sistema.
**Criterios de aceptación**
- Layout de `05 §7.2`: PriceField hero arriba a la izquierda; secciones colapsables (Receptor y pago, Concepto, Ruta y ubicaciones, Mercancías, Unidad y operador); a la derecha AcuseViewer + Resumen con validación y botón "Timbrar".
- El campo es el **subtotal**: tiene el foco al abrir y llega con el **subtotal sugerido ya escrito y seleccionado**, listo para modificar (teclear lo reemplaza). Si el servicio ya tenía precio, llega ese.
- Debajo del campo se ve **la suma que explica el sugerido** (una línea por concepto y el total de la suma) y, debajo, IVA, retención y **total calculados automáticamente** con cada tecla.
- Si el admin no toca el sugerido, ese valor se guarda al timbrar. Enlace discreto "Capturar el total con IVA" calcula el subtotal a partir del total.
- **Todo es editable**: precio, descripción, uso CFDI/método/forma de pago, distancias y lugares, mercancías y pesos, acuses (subir/reemplazar/folio), unidad y operador del servicio; los datos de catálogo (fiscales del cliente, placas, permisos, licencia) se editan en un drawer del catálogo sin salir de la pantalla. Lo editado se guarda en el servicio/viajes/catálogo (una sola fuente de verdad), no solo en la factura.
- Si el operador reportó km distintos a la distancia de Carta Porte, chip "Operador: 95 km · usar".
- La validación se recalcula tras cada guardado; clic en un check abre su sección.
- "Timbrar" deshabilitado con errores; `ConfirmDialog` con receptor y total; envía `total_esperado`.
- Tras timbrar: UUID, PDF/XML y botón "Enviar al cliente".

### H4.5 — Precio sugerido
Como admin, quiero un precio de partida con su explicación y los precios recientes de la ruta a un clic.
**Criterios de aceptación**
- `GET /servicios/{id}/precio-sugerido` y `POST /precios/sugerir` según `07` (cascada tarifa pactada → historial de ruta → $/km → fórmula), con **`desglose`** (Σ = subtotal sugerido, `07 §4.1`), explicación, referencias, últimos precios y rango.
- Servicios con varios destinos: reglas de `07 §2.1` (stand-by; no usar `cargo_parada_extra`).
- En Facturar: si el servicio no tiene precio, la sugerencia se precarga en el campo; si ya tiene, queda como referencia con "Usar sugerido".
- En Nuevo servicio (Fase 2): la sugerencia y su desglose aparecen en el PriceField `compact` cuando hay cliente y destinos.
- Al timbrar se guardan `precio_sugerido` y su detalle en el servicio.

### H4.6 — Tarifas pactadas y parámetros de precio
> **Alcance reducido (5 oct 2026):** por ahora solo hay tarifario fijo para Chemital (`07 §2.0`), editable en Configuración → Precios y tarifas. La tabla de tarifas pactadas por destino, `GET /configuracion/pendientes` y el aviso SetupReminder quedan fuera hasta que se amplíe a más clientes.
Como admin, quiero registrar tarifas acordadas por cliente y destino, y ajustar la fórmula base, sin código.
**Criterios de aceptación**
- Configuración → Precios y tarifas: parámetros (`tarifa_base`, `tarifa_km`, redondeo, ventana de historial) y tabla de tarifas pactadas; también en la tab "Tarifas" del cliente. `cargo_parada_extra` se muestra deshabilitado ("Pendiente de definir").
- Solo una tarifa activa por cliente + destino.
- **Recordatorio de costos pendientes**: `GET /configuracion/pendientes` y el aviso **SetupReminder** en Facturar, en esta pantalla y en el dashboard mientras falten tarifas o parámetros; se puede descartar (`07 §5`).
- **Antes de cerrar esta historia, pídele a Vlad sus costos y tarifas** (ver INFO REQUERIDA). No siembres valores inventados.

### H4.7 — Timbrado
**Criterios de aceptación**
- `POST /servicios/{id}/facturar` según `04 §6`: lock del servicio, validación, `total_esperado`, payload guardado, Facturama, commit, PDF/XML a R2 después del commit.
- Doble clic → una sola factura. Fallo de R2 → factura timbrada y `reintentar-archivos`. Error del PAC → `502` con mensaje, factura `error` reintentable.
- `servicio.estado_facturacion = facturado` (el estado operativo no cambia); `saldo_insoluto = total`; `estado_cobro = pendiente`.

### H4.8 — Descarga y envío por correo
**Criterios de aceptación**
- Botones **Descargar PDF** y **Descargar XML** al timbrar, en el detalle del servicio y en el detalle de la factura (`GET /facturas/{id}/descargar`), con nombre `{serie}{folio}_{rfc_receptor}`.
- `POST /facturas/{id}/enviar` según `04 §9`: XML + PDF + acuses escaneados que existan (todas las páginas) o folios en el cuerpo; destinatarios editables; `enviado_at`/`envio_error`; reintento y reenvío.

### H4.9 — Facturas: lista y detalle
**Criterios de aceptación**
- Lista filtrable (estado fiscal, cobro, cliente, mes de emisión) y detalle según `05 §7.3`; descargas con URLs firmadas.

### H4.10 — Cancelación con aceptación del receptor
**Criterios de aceptación**
- `POST /facturas/{id}/cancelar` según `04 §8` con motivos 02/03/04; refleja el estatus que devuelva Facturama: `cancelada` o `cancelacion_pendiente`.
- "En espera": banner en el detalle, botón "Actualizar estatus" (throttle 5 min); al confirmarse, servicio → `estado_facturacion = pendiente` (editable y re-facturable); si el receptor rechaza, vuelve a `timbrada` con aviso.
- Bloqueo con pagos aplicados (`409 factura_con_rep`): la regla se ejercita de verdad en Fase 5, pero el chequeo se implementa aquí.

### H4.11 — Timbrado anticipado
Como admin, quiero timbrar la Carta Porte antes del traslado cuando el cliente la pide, y descargar el PDF y el XML para enviárselos.
**Criterios de aceptación**
- Solo para servicios con la casilla "Timbrar antes del servicio" (H2.7). Sin la casilla, timbrar un servicio no terminado → `409`.
- En Nuevo servicio, con la casilla marcada el primario dice **"Crear y revisar para timbrar"** y abre la pantalla Facturar del servicio recién creado.
- La pantalla Facturar entra en **modo anticipado** (`04 §5`): no exige servicio terminado ni acuse; exige subtotal, mercancías por entrega y horas programadas; las fechas de la Carta Porte son las programadas.
- El `ConfirmDialog` avisa que, si después cambia el precio, la ruta o la mercancía, habrá que cancelar la factura.
- Al timbrar: `estado_facturacion = facturado`, el estado operativo sigue igual; aparecen **Descargar PDF**, **Descargar XML** y "Enviar al cliente".
- El operador ejecuta el servicio con normalidad (Fase 3); sus mercancías quedan en solo lectura. Al terminar, el admin puede **reenviar** el correo, ya con los acuses.
- Un servicio con la casilla que llega a `terminado` sin timbrar se factura con las reglas normales.

## Endpoints / pantallas
- Endpoints: `03 §8–10`.
- Pantallas: Facturar (`05 §7.2`), Facturas (`05 §7.3`), Configuración → Precios y tarifas y tab Tarifas del cliente (`05 §7.5`).

## INFO REQUERIDA (Vlad)
> 🔴 **Costos y tarifas (pendiente de Vlad)**: tarifas pactadas por cliente y destino, tarifa base, costo por km y redondeo (`07 §5`). Recuérdaselo al llegar a H4.6; si aún no los tiene, la fase se cierra con el aviso dentro de la app activo.
>
> 🔴 Además: credenciales del **sandbox de Facturama**; un **CFDI real (XML + PDF)** como fixture; datos del **emisor**; `FormaPago` (`04 §7`); apodo vs placa en la descripción (`04 §2`); remitente de **Resend**. Nunca subir el CSD al repo.
>
> En stand-by (no bloquea): cómo se cobra un servicio con varios destinos (`07 §2.1`).

## Casos borde
- Facturama rechaza por catálogo SAT vencido → mostrar su mensaje y llevar al dato de catálogo a corregir.
- El admin cambia el precio en otra pestaña → `409 total_no_coincide`; la pantalla recarga montos y pide confirmar de nuevo.
- Servicio sin historial ni tarifas → "Sin referencias para esta ruta"; el campo queda vacío y con foco.
- Cancelación pendiente por más de 3 días hábiles sin cambio → mostrar "debería haberse resuelto; actualiza el estatus".
- Factura `error` y luego se edita el servicio → el reintento rearma el payload con los datos nuevos.
- Timbrado anticipado con la salida programada ya pasada → warning, no bloquea.
- Se desmarca la casilla en un servicio ya timbrado por anticipado → `409` (dato fiscal bloqueado).
- Cancelación de una factura anticipada confirmada con el servicio en curso → vuelve a "Por facturar" y se puede corregir y re-timbrar (anticipado si no ha terminado, normal si ya terminó).

## Definición de terminado
- [ ] Tests del checklist de `04 §11` y de `07 §7`.
- [ ] Pantalla Facturar completa: subtotal sugerido listo para modificar con su suma y el total calculado debajo, todo editable, acuse visible, validación navegable.
- [ ] Timbrado anticipado de punta a punta en sandbox, con descarga de PDF y XML.
- [ ] Aviso de costos pendientes funcionando; costos reales pedidos a Vlad.
- [ ] Timbrado sandbox con PDF/XML en R2; sin doble timbrado.
- [ ] Descarga de PDF/XML y envío por correo con adjuntos según modo de acuse.
- [ ] Cancelación inmediata y "en espera" con actualización de estatus.
