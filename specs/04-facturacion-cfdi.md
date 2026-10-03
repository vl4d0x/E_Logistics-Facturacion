# 04 · Facturación CFDI 4.0 + Carta Porte 3.1 (v2)

> **El spec más delicado.** Mapeo de un `servicio` a un CFDI 4.0 tipo Ingreso con Complemento Carta Porte 3.1, timbrado por **Facturama**. Calibrado contra una factura real de Elogistics (ago 2026).
>
> **Regla de oro**: los nombres exactos de los campos JSON los define **Facturama**. Este documento es el *qué* (qué dato va dónde a nivel SAT). **Verifica nombres y estructura contra la documentación vigente de Facturama** para CFDI 4.0 + Carta Porte 3.1 antes de dar por buena la integración, y reutiliza lo aprendido en el spike de Fase 0. No inventes claves de catálogo SAT.
>
> **v2**: unidad y operador salen del servicio; ubicaciones salen del catálogo `lugar`; pantalla "Facturar" con datos editables y precio sugerido; impuestos desde total; cancelación con aceptación del receptor (RMF 2026); el envío por correo vive aquí. El complemento de pago está en `06`.
>
> **v2.1**: se factura después del servicio por decisión de negocio (§1.1); **timbrado anticipado** opcional (§1.2); la unidad que va en la Carta Porte es la **unidad de registro**; descarga de PDF/XML (§9); `servicio.estado_facturacion` reemplaza al estado operativo "facturado".

## 1. Naturaleza del comprobante

- `TipoDeComprobante = I`, CFDI `4.0`, Carta Porte `3.1`.
- **Emisor persona física**, constantes de configuración (env, `01 §8`): RFC, nombre, `RegimenFiscal = 612`, `LugarExpedicion` (CP).
- `Moneda MXN`, `TipoCambio 1`, `Exportacion 01`.

> 🔴 **INFO REQUERIDA (Vlad)** — confirma los datos fiscales del emisor (RFC, nombre, régimen 612, CP de expedición). No los tomes del XML de ejemplo sin confirmación, y nunca subas el CSD al repo.

### 1.1 Momento del timbrado (decisión tomada)

- **Flujo normal: se timbra después del servicio**, con el servicio `terminado`. Motivo de negocio: a veces hay que acordar términos con el cliente (precio final, condiciones) antes de poder timbrar.
- **Excepción: timbrado anticipado** (§1.2), para los casos en que el cliente pide la Carta Porte antes del traslado.

Quien implemente no cambia esta regla por su cuenta: el flujo normal no timbra antes, y el anticipado solo se activa con la casilla.

### 1.2 Timbrado anticipado

Se activa por servicio con la casilla **"Timbrar antes del servicio"** (`servicio.timbrado_anticipado`, **apagada por defecto**), al crear o editar el servicio.

- **Exige subtotal** al guardar. Para timbrar hacen falta además, capturados por el admin: las **mercancías** de cada entrega (con peso), las **horas programadas** de salida y de llegada (`viaje.hora_salida_programada`, `viaje.hora_llegada_programada`) y las distancias.
- Se timbra desde la misma pantalla "Facturar", con el servicio todavía `programado` (o `en_curso`). Aún no hay acuse, así que no se exige.
- Las fechas de las ubicaciones salen de lo **programado** (§4.2).
- Al timbrar: `estado_facturacion = facturado`; el estado operativo no cambia. El operador ejecuta el servicio como siempre (inspección, viajes, acuses, cierre); las mercancías ya no se pueden modificar y las ve en solo lectura.
- El admin **descarga el PDF y el XML** (o los envía por correo) para entregarlos al cliente antes del traslado (§9). Cuando el servicio termina puede reenviar el correo, ya con los acuses.
- Si después cambia algo fiscal (precio, destino, mercancía, unidad), hay que **cancelar la factura y volver a timbrar** (§8). La pantalla lo advierte antes de timbrar por anticipado.
- Si un servicio con la casilla llega a `terminado` sin haberse timbrado, se valida y timbra con las reglas del flujo normal (datos reales y acuse).

## 2. Concepto (partida)

Un servicio = **un concepto** de flete:
- `ClaveProdServ = 78101802` · `ClaveUnidad = SX` (Unidad "Envío") · `Cantidad = 1` — constantes de config.
- `ValorUnitario = Importe = servicio.subtotal` · `ObjetoImp = 02`.
- `Descripcion`: si `servicio.descripcion_concepto` es null, **se autogenera**:
  ```
  FLETE UNIDAD {unidad.apodo}
  ORIGEN: {nombres de los lugares de origen, " / "}
  DESTINO: {nombres de los lugares de destino en orden, " / "}
  FECHA: {fecha o rango "dd/mm/aaaa – dd/mm/aaaa"}
  ```
  El admin puede editar el texto en la pantalla "Facturar" (se guarda en `descripcion_concepto`) o volver al autogenerado ("Regenerar" → `null`).

> 🔴 **INFO REQUERIDA (Vlad)** — confirma si la descripción debe mostrar el apodo de la unidad o su placa (el apodo es interno; el cliente lo verá en su factura).

## 3. Impuestos — retención 4% condicional

Sobre la base `subtotal`:
- **IVA trasladado 16%** siempre: `{Impuesto 002, Tasa, 0.160000, Importe = subtotal × 0.16}`.
- **Retención IVA 4%** solo si `cliente.regimen_receptor = moral`: `{Impuesto 002, Tasa, 0.040000, Importe = subtotal × 0.04}`.
- **Total** = `subtotal + iva_trasladado − iva_retenido`.

Ejemplo real (Chemital, moral): `1650.00 → 264.00 / 66.00 / 1848.00`.

Implementación: `facturacion/taxes.py`, función pura `calcular_impuestos(subtotal: Decimal, regimen_receptor) -> Montos`. `Decimal`, 2 decimales, `ROUND_HALF_UP` en cada impuesto. El frontend replica la misma función en `lib/money.ts` para feedback instantáneo, pero **el backend es la verdad** (ver `total_esperado` en §6).

### 3.1 Capturar el total en lugar del subtotal

A veces el precio se pacta "con IVA". La pantalla permite capturar el total:
```
factor = 1.12 si moral (1 + 0.16 − 0.04), 1.16 si física
subtotal = round_half_up(total / factor, 2)
montos   = calcular_impuestos(subtotal, regimen)
```
Por redondeo, `montos.total` puede diferir ±$0.01 del total tecleado: la UI muestra el total resultante. Función pura `subtotal_desde_total(total, regimen)`. Caso de prueba: `1848.00, moral → 1650.00`.

## 4. Complemento Carta Porte 3.1 — mapeo

### 4.1 Atributos raíz
- `TranspInternac = "No"`.
- `TotalDistRec` = Σ `DistanciaRecorrida` de los destinos.
- `IdCCP`: identificador del complemento — verificar si lo genera Facturama o nosotros (resuelto en el spike).

### 4.2 Ubicaciones (desde los viajes del servicio, en `orden`)

```
for viaje in servicio.viajes order by orden:
    if viaje.tipo in (recoleccion, recoleccion_entrega):
        agregar Origen(lugar = viaje.origen, fecha_hora = salida(viaje))
    if viaje.tipo in (entrega, recoleccion_entrega):
        agregar Destino(lugar = viaje.destino, fecha_hora = llegada(viaje), distancia = viaje.distancia_km)
```
- `IDUbicacion`: `OR` + 6 dígitos para orígenes, `DE` + 6 dígitos para destinos, consecutivos (`OR000001`, `DE000001`, `DE000002`…). Verificar formato en Facturama.
- `salida(viaje)`: si el viaje ya está terminado, `viaje.terminado_at` de la recolección (salió cargado); si no, `viaje.fecha + hora_salida_programada`. Últimos recursos en el flujo normal: `servicio.iniciado_at`, o `viaje.fecha 08:00` local + **warning**.
- `llegada(viaje)`: si el viaje ya está terminado, `viaje.fecha + viaje.hora_llegada` (o `viaje.terminado_at` si no se capturó la hora); si no, `viaje.fecha + hora_llegada_programada`.
- En la práctica: en el flujo normal salen de lo **real**; en timbrado anticipado, de lo **programado**. El borrador de factura indica la fuente de cada fecha (`fecha_hora_fuente`).
- Todas las fechas en hora local de México, formato `AAAA-MM-DDTHH:MM:SS`.
- `DistanciaRecorrida` = `viaje.distancia_km` (la del admin). `km_reportado` del operador solo se usa para sugerir y para la regla de discrepancia de §5.

Por ubicación (desde `lugar`):
| Campo Carta Porte | Fuente |
|---|---|
| `TipoUbicacion` | `Origen` / `Destino` |
| `RFCRemitenteDestinatario` | `lugar.rfc_remitente_destinatario` |
| `NombreRemitenteDestinatario` | `lugar.nombre_remitente_destinatario` (si hay) |
| `FechaHoraSalidaLlegada` | ver arriba |
| `DistanciaRecorrida` | solo destinos |
| `Domicilio` | `{ Calle?, NumeroExterior?, Colonia?, Localidad?, Municipio?, Estado, Pais, CodigoPostal }` |

Ejemplo real: Origen RFC `CME091007LG1` (Chemital) CP `52004`; Destino `XAXX010101000` "GUADALUPE LIMON", CP `52000`, distancia `80`.

### 4.3 Mercancías
- Fuente: todos los `viaje_mercancia` del servicio (los captura el operador al terminar cada entrega o, en timbrado anticipado, el admin al crear el servicio).
- `PesoBrutoTotal = Σ peso_kg`, `UnidadPeso = KGM`, `NumTotalMercancias = conteo`.
- Por mercancía: `{ BienesTransp, Descripcion, Cantidad, ClaveUnidad, Unidad, PesoEnKg }`.
- `CantidadTransporta` (ligar mercancía a origen/destino): no en MVP salvo que Facturama lo exija — verificar.

### 4.4 Autotransporte (de `servicio.unidad`)
- `PermSCT`, `NumPermisoSCT`.
- `IdentificacionVehicular { ConfigVehicular, PesoBrutoVehicular (toneladas), PlacaVM, AnioModeloVM }`.
- `Seguros { AseguraRespCivil, PolizaRespCivil }`.
- Un solo vehículo por CFDI: va la **unidad de registro** del servicio, aunque físicamente hayan participado más camionetas.

### 4.5 Figura de transporte (de `servicio.operador`)
- `TiposFigura { TipoFigura "01", RFCFigura, NumLicencia, NombreFigura }`.

## 5. Validación pre-timbrado (`GET /servicios/{id}/validar`)

Devuelve `checks[]` y `preview`. **Cualquier `error` bloquea el timbrado**; los `warning` se muestran y permiten continuar. Cada check lleva `campo` cuando aplica para que la UI enfoque la sección a corregir.

**Modo de validación**: `anticipado` si `servicio.timbrado_anticipado` y `estado ≠ terminado`; en cualquier otro caso, `normal`. La columna "Aplica" dice en qué modo corre cada regla.

| Regla | Nivel | Aplica | Detalle |
|---|---|---|---|
| Servicio en estado `terminado` | error | normal | Fallback: el admin puede "marcar terminado". En anticipado basta con que no esté `cancelado` |
| Sin factura vigente | error | ambos | |
| ≥1 Origen y ≥1 Destino | error | ambos | |
| Subtotal presente y > 0 | error | ambos | |
| Acuse según `modo_acuse` en cada entrega | error | normal | escaneo → archivo; referencia → folio. En anticipado el acuse llega después |
| Cada destino con `distancia_km` > 0 | error | ambos | |
| Hora programada de salida en cada origen y de llegada en cada destino (viajes aún no terminados) | error | anticipado | |
| `km_reportado` vs `distancia_km` difieren > 20% | warning | normal | "El operador reportó 95 km; la Carta Porte dice 80" |
| Salida del origen anterior a la llegada de cada destino | error | ambos | |
| Ninguna fecha futura | error | normal | en anticipado las fechas son futuras por definición |
| Alguna fecha programada ya pasó | warning | anticipado | "La salida programada ya pasó; revisa fecha y hora" |
| Al menos una mercancía con peso > 0 en el servicio | error | ambos | en anticipado las captura el admin |
| Alguna entrega sin mercancías | warning | ambos | |
| Peso total ≤ `unidad.capacidad_carga_kg` | warning | ambos | solo si hay capacidad registrada |
| `PesoBrutoVehicular` plausible en **toneladas** | warning | ambos | si > 100, "parece estar en kg" (la factura real traía `500`) |
| Permiso SCT a revisar | warning | ambos | si `perm_sct` está en `configuracion["facturacion.permisos_revisar"]` (default `["TPAF14"]`, paquetería en un flete de carga) |
| Lugares con CP, estado y país | error | ambos | |
| Cliente con RFC, CP fiscal y régimen; operador con RFC y licencia; unidad con placa, permiso y póliza | error | ambos | |
| Retención 4% aplicada sii receptor moral | error | ambos | consistencia |
| Inspección de salida con fallas | warning | normal | "La inspección reportó: extintor" |
| Servicio terminado por el admin sin reporte del operador | warning | normal | |

## 6. Timbrado (`POST /servicios/{id}/facturar`)

1. Bloquear el servicio (`SELECT … FOR UPDATE`). Si ya hay factura vigente → `409` (protege el doble clic). Si hay una factura `error` previa, se reutiliza esa fila.
2. Correr §5; con errores → `409`.
3. Recalcular montos; si `total ≠ body.total_esperado` → `409 total_no_coincide` (la UI estaba desactualizada).
4. Armar el payload (`facturacion/payload.py`, puro y testeable) y guardarlo en `factura.payload`.
5. Llamar a Facturama (crear/timbrar). Timeout y errores explícitos.
6. Éxito: `factura.estado = timbrada`, `uuid_fiscal`, `facturama_id`, `serie/folio`, `fecha_emision`, montos, `saldo_insoluto = total`, `estado_cobro = pendiente`, `timbrado_at`; `servicio.estado_facturacion = facturado` (el estado operativo no cambia); guardar `servicio.precio_sugerido(_detalle)` mostrado. **Commit.**
7. Después del commit: descargar PDF y XML de Facturama y subirlos a R2. Si falla, la factura sigue timbrada y se reintenta con `POST /facturas/{id}/reintentar-archivos` (nunca re-timbrar).
8. Error del PAC: `estado = error`, `error_detalle` = mensaje de Facturama, `502 facturama_error`; reintentable.

Cliente HTTP en `integrations/facturama.py`: Basic Auth, base URL por `FACTURAMA_ENV`.

> 🔴 **INFO REQUERIDA (Vlad)** — credenciales del sandbox y al menos un **CFDI real (XML + PDF)** como fixture del test de equivalencia del payload.

## 7. Método y forma de pago

- Todas las facturas son **PPD** (`MetodoPago = PPD`, `FormaPago = 99`). `cliente.metodo_pago_default` y `servicio.metodo_pago` existen para casos excepcionales (PUE con forma de pago real).
- Cada pago recibido de una factura PPD requiere un **REP**: ver `06`.

> 🔴 **INFO REQUERIDA (Vlad)** — confirma `FormaPago = 99` para PPD y si algún cliente es PUE.

## 8. Cancelación (`POST /facturas/{id}/cancelar`)

Reglas vigentes (RMF 2026), que **no implementamos nosotros**: las aplica el SAT y Facturama devuelve el estatus. Nuestra app solo refleja ese estatus.
- Una factura de ingreso de **más de $1,000** necesita **aceptación del receptor**, salvo que se cancele **dentro del día hábil siguiente** a su emisión. El receptor tiene **3 días hábiles**; si no responde, se considera aceptada. Si la rechaza, la factura sigue vigente.
- Una factura con **CFDI relacionados vigentes** (sus REP) no se puede cancelar: primero se cancela el REP y se revierte la aplicación del pago (`06 §6`). Nuestro endpoint lo valida antes (`409 factura_con_rep`).
- Plazo: para persona física, hasta la presentación de la declaración anual (abril del año siguiente). Mostrar **warning** si la factura es de un ejercicio anterior; no bloquear (el SAT decide).

Flujo:
1. Validar: factura `timbrada`, sin aplicaciones de pago activas; motivo válido.
2. Llamar a la cancelación de Facturama con el motivo.
3. Según la respuesta: `cancelada` (sin aceptación) → guardar acuse en R2 y `servicio.estado_facturacion = pendiente` (datos fiscales editables de nuevo); o `cancelacion_pendiente` → `cancelacion_solicitada_at`.
4. Mientras esté `cancelacion_pendiente`: los datos fiscales del servicio siguen bloqueados; el estatus se consulta bajo demanda (`POST /facturas/{id}/actualizar-estatus`, widget "En espera" del dashboard, detalle de factura) con throttle de 5 min.
5. Al confirmarse: `cancelada`, `cancelada_at`, acuse en R2, servicio → `estado_facturacion = pendiente`. Si el receptor rechaza: vuelve a `timbrada` y se informa al admin.

Motivos en MVP: **02** (errores sin relación — el camino normal para "corregir y volver a facturar"), **03** (no se llevó a cabo la operación), **04** (factura global, prácticamente no aplica). **01** (errores con relación / sustitución) requiere timbrar primero la factura sustituta relacionada; queda en **backlog** porque implica dos facturas vigentes del mismo servicio a la vez.

Confirmado por Vlad (2 oct 2026): las correcciones habituales usan el motivo **02**. Es también el camino cuando una factura timbrada por anticipado necesita cambios.

## 9. Descarga y envío por correo

- **Descarga**: botones **Descargar PDF** y **Descargar XML** en la pantalla Facturar (al timbrar), en el detalle del servicio y en el detalle de la factura (`GET /facturas/{id}/descargar?formato=pdf|xml`), con nombre `{serie}{folio}_{rfc_receptor}.pdf|xml`. Es el camino principal en timbrado anticipado, cuando el admin se los pasa al cliente por su cuenta.

**Envío** (`POST /facturas/{id}/enviar`):

- Destinatarios: `to` o `cliente.emails_facturacion`.
- Adjuntos: XML + PDF; si el cliente es `escaneo`, todas las páginas de acuse que existan en ese momento. Si es `referencia`, sin adjunto de acuse: los folios van en el cuerpo. En timbrado anticipado aún no hay acuses: el correo se puede **reenviar** al terminar el servicio, ya con ellos.
- Asunto: `Factura {serie}{folio} · Servicio #{numero} · Elogistics`. Cuerpo breve: cliente, fecha(s), ruta, total, UUID, folios de acuse si aplica.
- Registrar `enviado_at`, `envio_destinatarios`; en fallo, `envio_error` y permitir reintento editando destinatarios.

> 🔴 **INFO REQUERIDA (Vlad)** — remitente verificado en Resend y, si se desea, el texto del correo.

## 10. Catálogos SAT — no hardcodear

`c_ClaveProdServCP`, `c_ClaveUnidad`, `c_ConfigAutotransporte`, `c_CodigoPostal`, `c_Estado`, `c_Municipio`, permisos y materiales peligrosos cambian. Se guardan como datos de negocio (`unidad`, `mercancia_frecuente`, `lugar`) y **Facturama valida**. Si rechaza por catálogo vencido, se corrige el dato en el catálogo, no el código. Las únicas constantes son las del concepto (§2), y viven en config.

## 11. Checklist de aceptación (tests de Fase 4)

- [ ] `calcular_impuestos(1650, moral)` = 264.00 / 66.00 / 1848.00; física → retención 0.
- [ ] `subtotal_desde_total(1848.00, moral)` = 1650.00; caso con redondeo documentado.
- [ ] Servicio de 1 recolección + 2 entregas → 1 Origen + 2 Destinos con `IDUbicacion` consecutivos y `TotalDistRec` = suma.
- [ ] Viaje `recoleccion_entrega` → un Origen y un Destino.
- [ ] `PesoBrutoTotal` = suma de pesos; mercancías de todas las entregas.
- [ ] Descripción autogenerada vs editada (y "Regenerar" la vuelve a null).
- [ ] Autotransporte y figura salen de la unidad y el operador **del servicio**.
- [ ] `/validar` (modo normal) bloquea: sin subtotal, acuse faltante (escaneo y referencia), sin destino, fechas invertidas, servicio no terminado.
- [ ] `/validar` advierte: PBV en kg, permiso a revisar, km discrepantes, inspección con fallas.
- [ ] `/facturar` con `total_esperado` distinto → 409; doble llamada → una sola factura.
- [ ] Payload equivalente (campos SAT) al fixture del CFDI real.
- [ ] Sandbox: timbra, guarda UUID, PDF y XML en R2; fallo de R2 no re-timbra.
- [ ] Cancelación: inmediata vs `cancelacion_pendiente` (mock de Facturama); al confirmarse, `estado_facturacion` vuelve a `pendiente`; rechazo → vuelve a `timbrada`; con aplicaciones de pago → 409.
- [ ] Timbrado anticipado: servicio `programado` con casilla, subtotal, mercancías y horas programadas → timbra; las fechas de las ubicaciones son las programadas; no exige acuse. Sin horas programadas o sin mercancías → error de validación.
- [ ] Tras timbrar por anticipado: `estado` sigue `programado` y `estado_facturacion = facturado`; el operador puede iniciar, terminar viajes, subir acuses y cerrar; editar subtotal, lugares o mercancías → 409.
- [ ] Sin la casilla, timbrar un servicio no terminado → 409.
- [ ] Servicio con casilla ya `terminado` y sin factura → se valida en modo normal.
- [ ] Descarga de PDF y XML con el nombre de archivo esperado.
