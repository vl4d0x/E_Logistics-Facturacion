# 03 · API contract (v2)

> Contrato REST. JSON snake_case. Prefijo `/api/v1`. Todo requiere `Authorization: Bearer <access_token>` salvo `/auth/login`, `/auth/refresh` y `/health`.
> **v2**: desaparecen `/servicios` de agrupar/desagrupar y `/viajes` sueltos; los viajes viven dentro del servicio. Nuevos grupos: operación en campo, precios, cobranza/REP, dashboard nuevo.
> **v2.1**: `timbrado_anticipado` y horas programadas en el servicio; el servicio expone `estado` (operativo) y `estado_facturacion`; la lista se filtra por `vista`; la sugerencia de precio trae `desglose`; las sugerencias de conciliación traen los servicios; descarga de PDF/XML; sin endpoints de combustible en el dashboard.

## 1. Convenciones

- **Fechas**: ISO 8601 UTC en el wire (`2026-08-11T14:23:49Z`); `date` como `YYYY-MM-DD`; `time` como `HH:MM`.
- **Dinero**: string decimal (`"1650.00"`).
- **IDs**: UUID string. Los servicios también exponen `numero` (int).
- **Paginación**: `?page=1&size=20` → `{ items, total, page, size }`.
- **Archivos**: subida `multipart/form-data`; lectura con URLs firmadas de vida corta (`url`, `expira_at`).
- **Acciones permitidas**: los detalles de servicio, factura y pago incluyen `acciones_permitidas: string[]` (p. ej. `["editar","facturar"]`) para que la UI no duplique reglas de estado.

## 2. Formato de error

```json
{
  "error": {
    "code": "conflict",
    "reason": "servicio_facturado",
    "message": "El servicio ya está facturado. Cancela la factura para modificar sus datos fiscales.",
    "details": [ { "field": "subtotal", "issue": "requerido" } ]
  }
}
```
`code`: `unauthorized` (401), `forbidden` (403), `not_found` (404), `validation_error` (422), `conflict` (409), `facturama_error` (502), `internal_error` (500).
`reason` (opcional, para la UI): `servicio_facturado`, `servicio_no_iniciado`, `viaje_terminado`, `catalogo_en_uso`, `factura_con_rep`, `total_no_coincide`, `aplicacion_no_cuadra`, `ya_procesado`, etc.

## 3. Auth (Fase 0, sin cambios)

```
POST /auth/login     { email, password } → 200 { access_token, refresh_token, user: { id, nombre, rol, operador_id } }
POST /auth/refresh   { refresh_token } → 200 { access_token }
GET  /auth/me        → 200 { id, nombre, email, rol, operador_id }
```

## 4. Health

```
GET /health → 200 { status: "ok" }
```

## 5. Catálogos y accesos (Fase 1) — solo admin

Patrón CRUD para `unidades`, `operadores`, `clientes`, `lugares`, y `mercancias` (anidadas en cliente):

```
GET    /catalogos/unidades?activo=true|false|todos&q=&page=&size=
POST   /catalogos/unidades
GET    /catalogos/unidades/{id}
PATCH  /catalogos/unidades/{id}
GET    /catalogos/unidades/{id}/uso       → { referencias: { servicios: 12, facturas: 9 }, accion_al_eliminar: "archivar" | "eliminar", bloqueos: [ { servicio_id, numero, estado } ] }
DELETE /catalogos/unidades/{id}           → 200 { resultado: "eliminado" | "archivado" }
POST   /catalogos/unidades/{id}/restaurar → 200 { ...unidad, activo: true }
```

- `DELETE` es "inteligente": si el registro nunca se referenció lo **elimina**; si se usó, lo **archiva** (`activo=false`). Si hay servicios `programado`/`en_curso` que lo usan, responde `409 catalogo_en_uso` con la lista en `details` (hay que reasignarlos primero).
- Bodies:
  - unidad: `{ apodo, placa, anio_modelo, config_vehicular, peso_bruto_vehicular, capacidad_carga_kg?, perm_sct, num_permiso_sct, aseguradora_resp_civil, poliza_resp_civil, tipo_medidor, num_barras?, capacidad_tanque_l?, tipo_combustible? }`
  - operador: `{ nombre, rfc, num_licencia, telefono? }`
  - cliente: `{ razon_social, nombre_comercial, rfc, cp_fiscal, regimen_fiscal, regimen_receptor, uso_cfdi, metodo_pago_default, modo_acuse, emails_facturacion: [..], dias_credito }`
  - lugar: `{ cliente_id?, nombre, rfc_remitente_destinatario, nombre_remitente_destinatario?, calle?, num_exterior?, colonia?, localidad?, municipio?, estado, pais, codigo_postal, referencia?, es_origen_predeterminado }`

```
GET  /catalogos/clientes/{id}/mercancias
POST /catalogos/clientes/{id}/mercancias   { nombre_humano, bienes_transp, clave_unidad, unidad_desc?, peso_kg_sugerido? }
PATCH/DELETE /catalogos/mercancias/{id}    # DELETE inteligente igual que arriba
GET  /catalogos/lugares?cliente_id=&incluir_globales=true&q=
```

**Acceso del operador a la app:**
```
GET    /catalogos/operadores/{id}/acceso   → { usuario_id, email, activo } | 404 si no tiene
POST   /catalogos/operadores/{id}/acceso   { email, password_temporal } → 201
PATCH  /catalogos/operadores/{id}/acceso   { email?, password_temporal?, activo? }
```

**Usuarios administradores:**
```
GET   /usuarios?rol=admin
POST  /usuarios            { nombre, email, password_temporal }    # siempre rol=admin
PATCH /usuarios/{id}       { nombre?, email?, password_temporal?, activo? }
```
Reglas: un admin no puede desactivarse a sí mismo; no se puede desactivar al último admin activo.

## 6. Servicios y viajes — admin (Fase 2)

```
POST /servicios
  body: {
    cliente_id, unidad_id, operador_id, fecha, subtotal?, notas?,      # unidad_id = unidad de registro
    timbrado_anticipado?: bool,        # default false; con true, subtotal es obligatorio (422 si falta)
    viajes: [ { tipo, fecha?, origen_lugar_id?, destino_lugar_id?, distancia_km?, notas_admin?,
                hora_salida_programada?, hora_llegada_programada?,
                mercancias?: [ { mercancia_frecuente_id, cantidad, peso_kg } ] } ]   # en orden
  }
  201: { ...servicio_detalle, estado: "programado", estado_facturacion: "pendiente" }

GET  /servicios?vista=&estado=&estado_facturacion=&cliente_id=&operador_id=&unidad_id=&fecha_desde=&fecha_hasta=&acuses_pendientes=true&inspeccion_fallas=true&q=&page=&size=
  # vista = programados | en_curso | por_facturar | facturados | cancelados   (las tabs de la UI)
  #   por_facturar = estado_facturacion "pendiente" y (estado "terminado" o timbrado_anticipado), sin cancelados
  #   facturados   = estado_facturacion "facturado" (sea cual sea el estado operativo)
  # q busca por número, cliente o lugar. Respuesta por item:
  # { id, numero, fecha, estado, estado_facturacion, timbrado_anticipado, cliente, unidad_apodo, operador_nombre, ruta_resumen,
  #   viajes_total, viajes_terminados, acuses: { requeridos, completos }, subtotal, total?, factura_vigente? }
GET  /servicios/conteos?…mismos filtros  → { programados, en_curso, por_facturar, facturados, cancelados }

GET   /servicios/{id}          → servicio_detalle (abajo)
PATCH /servicios/{id}          { unidad_id?, operador_id?, fecha?, subtotal?, notas?, timbrado_anticipado? }
                               # 409 servicio_facturado si hay factura vigente (salvo `notas`); 409 si cancelado
POST  /servicios/{id}/duplicar { fecha } → 201 servicio nuevo "programado" con los mismos viajes (sin estados, km, acuses, precio ni timbrado anticipado)
POST  /servicios/{id}/marcar-terminado   # fallback admin; exige todos los viajes terminados
POST  /servicios/{id}/cancelar { motivo } # solo sin factura vigente

POST   /servicios/{id}/viajes            { tipo, fecha?, origen_lugar_id?, destino_lugar_id?, distancia_km?, notas_admin?, hora_salida_programada?, hora_llegada_programada? }
PATCH  /viajes/{id}                      { tipo?, fecha?, origen_lugar_id?, destino_lugar_id?, distancia_km?, notas_admin?, hora_salida_programada?, hora_llegada_programada? }
DELETE /viajes/{id}                      # 409 viaje_terminado si ya está terminado
                                         # los tres: 409 servicio_facturado con factura vigente (salvo PATCH de `notas_admin`)
POST   /servicios/{id}/viajes/orden      { viaje_ids: [..] }

POST /viajes/{id}/terminar      # admin en nombre del operador; mismo body que §7 (client_action_id opcional)
POST /viajes/{id}/reabrir       # reglas en 02 §4 (con servicio terminado, solo sin factura vigente; el servicio vuelve a "en_curso")
PUT  /viajes/{id}/mercancias    [ { mercancia_frecuente_id?, descripcion?, bienes_transp?, clave_unidad?, cantidad, peso_kg } ]   # 409 servicio_facturado con factura vigente
POST /viajes/{id}/acuses        multipart: file, pagina?      |  json: { referencia }      # operativo: permitido aunque haya factura
DELETE /acuses/{id}

GET /lugares/distancia-sugerida?origen_lugar_id=&destino_lugar_id=   → { distancia_km, fuente: "ultimo_viaje" | null }

PATCH  /cargas/{id}   { litros?, precio_litro?, importe?, tipo_combustible? }   # corrección del admin
DELETE /cargas/{id}
```

**`servicio_detalle`:**
```json
{
  "id": "…", "numero": 128, "fecha": "2026-09-30",
  "estado": "terminado", "estado_facturacion": "pendiente", "timbrado_anticipado": false,
  "cliente":  { "id": "…", "nombre_comercial": "Chemital", "modo_acuse": "referencia", "regimen_receptor": "moral" },
  "unidad":   { "id": "…", "apodo": "Saveiro Roja", "tipo_medidor": "barras", "num_barras": 8 },
  "operador": { "id": "…", "nombre": "…" },
  "subtotal": "1650.00", "notas": null,
  "viajes": [
    { "id": "…", "orden": 1, "tipo": "recoleccion", "estado": "terminado", "fecha": "2026-09-30",
      "origen": { "id": "…", "nombre": "Planta Chemital", "codigo_postal": "52004" }, "destino": null,
      "hora_salida_programada": null, "hora_llegada_programada": null,
      "distancia_km": null, "km_reportado": "12.00", "hora_llegada": "09:10", "terminado_at": "…",
      "mercancias": [], "acuses": [], "acuse_requerido": false, "acuse_completo": true }
  ],
  "inspeccion": { "todo_ok": false, "fallas": ["extintor_ok"], "observaciones": "…", "nivel_combustible": "0.625", "lectura_medidor": { "tipo": "barras", "barras": 5, "total": 8 }, "odometro_km": 84213, "realizada_at": "…" },
  "cierre": { "nivel_combustible": "0.375", "lectura_medidor": { … }, "odometro_km": 84305, "cargo_combustible": true, "cerrado_at": "…" },
  "cargas": [ { "id": "…", "litros": "30.00", "precio_litro": "24.590", "importe": "737.70", "ticket_url": "…" } ],
  "combustible_total": { "litros": "30.00", "importe": "737.70" },
  "documentacion": { "acuses_requeridos": 2, "acuses_completos": 1 },
  "factura_vigente": null,                 // { id, uuid_fiscal, estado, total, estado_cobro, pdf_url, xml_url } si existe
  "datos_fiscales_bloqueados": false,      // true con factura vigente (02 §4)
  "acciones_permitidas": ["editar", "facturar", "cancelar"]
}
```

## 7. Operador — PWA con offline (Fase 3)

Todo filtra por `user.operador_id`; acceder a un servicio ajeno → `403`. Todas las escrituras son **idempotentes**: si el `client_action_id` (o el `id` de la carga) ya se procesó, `200` con el estado actual.

```
GET /operador/servicios?estado=programado,en_curso,terminado&desde=
  # default: programados y en curso + terminados de los últimos 7 días
  200: [ servicio_detalle + {
           lugares completos (nombre, dirección, referencia),
           mercancias_cliente: [ { id, nombre_humano, unidad_desc, peso_kg_sugerido } ],   # sin claves SAT
           # las mercancías que el admin ya capturó vienen en cada viaje; datos_fiscales_bloqueados indica si son de solo lectura
           medidor: { tipo_medidor, num_barras } } ]

POST /operador/servicios/{id}/iniciar
  body: { client_action_id, realizada_at,
          checklist: { unidad_limpia, fumigacion_vigente, botiquin, casco_chaleco,
                       aceite_ok, anticongelante_ok, neumaticos_ok, extintor_ok },   # todos bool, obligatorios
          observaciones?, lectura_medidor: { tipo, octavos? | barras?, total? }, odometro_km? }
  200: servicio_detalle con estado "en_curso"
  # el server calcula nivel_combustible desde la lectura y valida contra la unidad (tipo y total de barras)

POST /operador/viajes/{id}/terminar
  body: { client_action_id, terminado_at, hora_llegada?, notas?,
          mercancias: [ { mercancia_frecuente_id, cantidad, peso_kg } ],   # entregas; vacío en recolección.
                                                                           # Con factura vigente (timbrado anticipado) se omite: se conservan las facturadas
          referencia_acuse? }                                              # modo referencia
  200: viaje
  409 servicio_no_iniciado si el servicio sigue "programado"

POST /operador/viajes/{id}/acuses
  multipart: file=<imagen|pdf>, client_action_id, pagina?
  200: { acuse: { id, tipo: "escaneo", pagina, url } }

POST /operador/servicios/{id}/cerrar
  body: { client_action_id, cerrado_at,
          km_por_viaje: [ { viaje_id, km } ],              # uno por cada viaje del servicio
          lectura_medidor, odometro_km?, observaciones?,
          cargo_combustible: bool,
          cargas: [ { id, litros, precio_litro, importe, tipo_combustible?, cargada_at } ] }   # id generado en el teléfono
  200: servicio_detalle con estado "terminado"
  409 si hay viajes pendientes

POST /operador/cargas/{id}/ticket
  multipart: file
  200: { ticket_url }     # reemplaza el anterior si se reenvía
```

## 8. Precios (Fase 4) — solo admin

```
GET  /servicios/{id}/precio-sugerido
POST /precios/sugerir   { cliente_id, unidad_id?, destino_lugar_ids: [..], distancia_km? }   # para "Nuevo servicio", antes de existir
  200: { monto: "1650.00" | null,                       # SUBTOTAL sugerido
         desglose: [ { concepto: "Tarifa base", monto: "600.00" },
                     { concepto: "80 km × $12.50", monto: "1000.00" },
                     { concepto: "Redondeo a $50", monto: "50.00" } ],        # Σ desglose = monto (07 §4.1)
         confianza: "alta" | "media" | "baja" | null,
         fuente: "tarifa_pactada" | "historial_ruta" | "historial_km" | "formula" | null,
         explicacion: "4 servicios Chemital → Guadalupe Limón; el último (12 sep) fue $1,650",
         referencias: [ { servicio_id, numero, fecha, ruta_resumen, subtotal } ],
         ultimos_precios_ruta: [ { fecha, subtotal } ], rango: { min, max } | null,
         configuracion_pendiente: bool }                 # true si faltan costos/tarifas por capturar (07 §5)

GET/POST/PATCH/DELETE /precios/tarifas      { cliente_id, destino_lugar_id, monto, vigente_desde, notas? }
GET   /configuracion                         → { "precio.tarifa_km": "…", … }
PATCH /configuracion                         { clave: valor, … }
GET   /configuracion/pendientes              → { completo: bool, faltantes: [ { clave: "tarifas_pactadas" | "formula", titulo, ruta_ui } ] }   # 07 §5
```

## 9. Facturación (Fase 4) — solo admin

```
GET /servicios/{id}/facturacion
  # "borrador de factura": TODO lo que se va a timbrar, ya precargado
  200: {
    modo: "normal" | "anticipado",          # anticipado = casilla marcada y servicio aún no terminado (04 §5)
    servicio: servicio_detalle,
    receptor: { razon_social, rfc, cp_fiscal, regimen_fiscal, regimen_receptor, uso_cfdi, metodo_pago, forma_pago },
    concepto: { clave_prod_serv, clave_unidad, descripcion, descripcion_autogenerada: bool },
    ubicaciones: [ { id_ubicacion, tipo: "Origen"|"Destino", viaje_id, lugar, fecha_hora, fecha_hora_fuente: "real"|"programada", distancia_km, km_reportado } ],
    mercancias: [ { viaje_id, descripcion, bienes_transp, clave_unidad, cantidad, peso_kg } ],
    autotransporte: { apodo, placa, config_vehicular, peso_bruto_vehicular, perm_sct, num_permiso_sct, aseguradora, poliza },
    figura: { nombre, rfc, num_licencia },
    montos: { subtotal, iva_trasladado, iva_retenido, total },
    precio_sugerido: { …ver §8 },
    acuses: [ { viaje_id, tipo, url?, referencia?, pagina } ]
  }

PATCH /servicios/{id}/facturacion
  body: { subtotal?, descripcion_concepto? (null = volver a autogenerar), uso_cfdi?, metodo_pago? }
  # persiste en el servicio; ubicaciones/mercancías/acuses se editan con los endpoints de §6
  # unidad/operador: PATCH /servicios/{id}; datos fiscales del cliente o la unidad: endpoints de catálogo

POST /impuestos/preview  { regimen_receptor, subtotal? | total? }
  200: { subtotal, iva_trasladado, iva_retenido, total }      # total → subtotal con 04 §3.1

GET /servicios/{id}/validar
  200: { ok: bool, checks: [ { regla, nivel: "ok"|"warning"|"error", mensaje, campo? } ],
         preview: { subtotal, iva_trasladado, iva_retenido, total } }

POST /servicios/{id}/facturar
  body: { total_esperado: "1848.00" }     # lo que el admin vio; si no coincide con el cálculo → 409 total_no_coincide
  200: { factura: { id, uuid_fiscal, estado, total, pdf_url, xml_url } }
  409: servicio no "terminado" (y sin timbrado anticipado), validación con errores, o factura vigente existente
  502: facturama_error (mensaje del PAC); la factura queda "error" y se puede reintentar
```

## 10. Facturas (Fase 4) — solo admin

```
GET  /facturas?estado=&estado_cobro=&cliente_id=&mes_emision=YYYY-MM&anio=&q=&page=&size=
GET  /facturas/{id}           # incluye urls firmadas PDF/XML/acuses, aplicaciones de pago y REPs relacionados, acciones_permitidas
GET  /facturas/{id}/descargar?formato=pdf|xml   # 302 a URL firmada con Content-Disposition: attachment
                                                # nombre: {serie}{folio}_{rfc_receptor}.pdf|xml
POST /facturas/{id}/enviar    { to?: [email] }   # default: cliente.emails_facturacion → 200 { enviado_at }
POST /facturas/{id}/reintentar-archivos         # si timbró pero falló la subida a R2: re-descarga PDF/XML (no re-timbra)
POST /facturas/{id}/cancelar  { motivo: "02|03|04" }        # 01 (sustitución) en backlog, ver 04 §8
  200: { estado: "cancelada" | "cancelacion_pendiente", acuse_cancelacion_url? }
  409 factura_con_rep si tiene aplicaciones de pago activas
  422 si el motivo no es 02, 03 o 04
POST /facturas/{id}/actualizar-estatus           # consulta a Facturama (throttle 5 min) → { estado, consultado_at }
```

## 11. Cobranza y REP (Fase 5) — solo admin

```
GET /cobranza/clientes?anio=YYYY|todos
  200: [ { cliente: { id, nombre_comercial }, saldo, facturas_abiertas, saldo_vencido, factura_mas_antigua: "2026-07-14" } ]   # orden: saldo desc

GET /cobranza/facturas?cliente_id=&estado_cobro=pendiente,parcial|pagada&mes_emision=&anio=&page=&size=
  # item: { id, folio, uuid_fiscal, fecha_emision, servicio: { id, numero, fecha, ruta_resumen }, total, saldo_insoluto,
  #         estado_cobro, dias_transcurridos, vencida: bool }

POST /cobranza/sugerencias
  body: { cliente_id, monto, fecha_pago? }
  200: resultado del algoritmo (06 §3.6) — sin efectos secundarios.
       Cada candidato trae `facturas` con su servicio (número, fecha, ruta) para que el admin corrobore.

POST /pagos
  body: { cliente_id, fecha_pago, monto, forma_pago, num_operacion?, rfc_emisor_cta_ord?, cta_ordenante?,
          rfc_emisor_cta_ben?, cta_beneficiario?, notas?,
          aplicaciones?: [ { factura_id, monto } ],      # si viene, registra y aplica en una transacción
          emitir_rep?: bool }                              # si viene true (y aplicaciones), timbra el REP al final
  201: pago (+ rep si se emitió)
POST /pagos/{id}/comprobante   multipart: file            # comprobante bancario (opcional)

GET  /pagos?cliente_id=&estado=&rep_pendiente=true&fecha_desde=&fecha_hasta=&page=&size=
GET  /pagos/{id}               # aplicaciones, rep vigente/históricos, vence_rep: "2026-10-05", acciones_permitidas
POST /pagos/{id}/aplicar       { aplicaciones: [ { factura_id, monto } ] }   # 422 aplicacion_no_cuadra si Σ ≠ monto
POST /pagos/{id}/revertir      # solo sin REP vigente; restaura saldos
POST /pagos/{id}/rep           # timbra el REP (idempotente por pago: si ya hay REP vigente → 200 con él)
  200: { rep: { id, uuid_fiscal, estado, pdf_url, xml_url } }   |  502 facturama_error

GET  /reps/{id}
POST /reps/{id}/enviar         { to?: [email] }
POST /reps/{id}/cancelar       { motivo, uuid_sustitucion? }   → { estado: "cancelacion_pendiente" | "cancelado" }
POST /reps/{id}/actualizar-estatus
```

## 12. Dashboard y export (Fase 6) — solo admin

Todas las respuestas incluyen `actualizado_at`.

```
GET /dashboard/pendientes
  200: { por_facturar: n, por_facturar_anticipados: n,      # anticipados = con la casilla y aún sin timbrar (incluidos en por_facturar)
         acuses_faltantes: n, inspecciones_con_fallas: n, costos_pendientes: bool,
         rep_por_emitir: { pagos: n, monto, vence: "2026-10-05" } }

GET /dashboard/ingresos?anio=2026&mes=10
  200: { periodo: { mes: "2026-10", facturado, cobrado, por_cobrar },
         meses_previos: [ { mes: "2026-09", facturado, cobrado, por_cobrar }, { mes: "2026-08", … } ],
         por_mes: [ { mes: "2026-01", facturado, cobrado, por_cobrar }, … 12 ],
         totales_anio: { facturado, cobrado, por_cobrar } }

GET /dashboard/por-cobrar?anio=2026|todos&limit=5        # limit omitido = todos
  200: { total_clientes, items: [ { cliente: { id, nombre_comercial }, saldo, facturas_abiertas } ] }

GET /dashboard/cancelaciones-en-espera
  200: { total, items: [ { factura_id, folio, cliente, total, solicitada_at, tipo: "factura"|"rep" } ] }

GET /export/servicios.xlsx?fecha_desde=&fecha_hasta=&cliente_id=&vista=
```

No hay endpoints de egresos ni de combustible en el dashboard (decisión de Vlad).

Semántica de ingresos (igual que el dashboard de referencia): se atribuyen al **mes de emisión** de la factura. `facturado = Σ total` de facturas vigentes emitidas en el mes; `cobrado = Σ aplicaciones` sobre esas facturas; `por_cobrar = Σ saldo_insoluto`. Invariante: `facturado = cobrado + por_cobrar`.

## 13. Archivos (R2)

- Keys: `acuses/{servicio_id}/{viaje_id}/{acuse_id}.jpg`, `tickets/{carga_id}.jpg`, `comprobantes/{pago_id}.*`, `cfdi/{uuid}.xml|pdf`, `rep/{uuid}.xml|pdf`, `cancelaciones/{uuid}.xml`.
- El frontend nunca recibe credenciales de R2: solo URLs firmadas de corta vida.

## 14. Mapa endpoint → fase

- **Fase 0**: `/health`, `/auth/*`.
- **Fase 1**: `/catalogos/*`, `/usuarios/*`.
- **Fase 2**: `/servicios` (CRUD, duplicar, cancelar, marcar-terminado), `/viajes/*`, `/acuses/*`, `/lugares/distancia-sugerida`, `/cargas/{id}`.
- **Fase 3**: `/operador/*`.
- **Fase 4**: `/precios/*`, `/configuracion`, `/servicios/{id}/precio-sugerido|facturacion|validar|facturar`, `/impuestos/preview`, `/facturas/*`.
- **Fase 5**: `/cobranza/*`, `/pagos/*`, `/reps/*`.
- **Fase 6**: `/dashboard/*`, `/export/*`.
