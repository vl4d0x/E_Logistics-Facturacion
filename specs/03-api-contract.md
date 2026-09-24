# 03 · API contract

> Contrato REST. Los endpoints están agrupados por módulo y por fase. JSON snake_case. Prefijo `/api/v1`. Todos requieren `Authorization: Bearer <access_token>` salvo `/auth/login`, `/auth/refresh` y `/health`.

## 1. Convenciones

- **Base**: `/api/v1`.
- **Auth**: header `Authorization: Bearer <token>`.
- **Content types**: `application/json`; subida de archivos con `multipart/form-data`.
- **Fechas**: ISO 8601 UTC en el wire (`2026-08-11T14:23:49Z`). El backend convierte a hora de México para lo fiscal.
- **Dinero**: string decimal (`"1650.00"`) para evitar errores de float.
- **IDs**: UUID string.
- **Paginación**: query `?page=1&size=20`; respuesta `{ items, total, page, size }`.
- **Filtros**: query params explícitos por endpoint (abajo).

## 2. Formato de error (envelope estándar)

```json
{
  "error": {
    "code": "validation_error",
    "message": "Descripción legible en español",
    "details": [ { "field": "subtotal", "issue": "requerido" } ]
  }
}
```
Códigos: `unauthorized` (401), `forbidden` (403), `not_found` (404), `validation_error` (422), `conflict` (409), `facturama_error` (502), `internal_error` (500).

## 3. Auth (Fase 0)

```
POST /auth/login
  body: { email, password }
  200:  { access_token, refresh_token, user: { id, nombre, rol, operador_id } }
  401:  credenciales inválidas

POST /auth/refresh
  body: { refresh_token }
  200:  { access_token }

GET  /auth/me
  200:  { id, nombre, email, rol, operador_id }
```
`require_role("admin")` protege todo lo administrativo. El operador solo accede a sus endpoints (§7).

## 4. Health (Fase 0)
```
GET /health → 200 { status: "ok" }   # sin auth, para Railway
```

## 5. Catálogos (Fase 1) — solo admin

Patrón CRUD idéntico para `unidades`, `operadores`, `clientes`, y `mercancias` (esta anidada bajo cliente). Ejemplo con unidad:

```
GET    /catalogos/unidades?activo=true&page=&size=
POST   /catalogos/unidades          body: {apodo, placa, anio_modelo, config_vehicular,
                                           peso_bruto_vehicular, perm_sct, num_permiso_sct,
                                           aseguradora_resp_civil, poliza_resp_civil}
GET    /catalogos/unidades/{id}
PATCH  /catalogos/unidades/{id}      body: campos parciales
DELETE /catalogos/unidades/{id}      → soft-delete (activo=false)
```

```
GET/POST/PATCH/DELETE /catalogos/operadores
  body: { nombre, rfc, num_licencia }

GET/POST/PATCH/DELETE /catalogos/clientes
  body: { razon_social, rfc, cp_fiscal, regimen_fiscal, regimen_receptor,
          uso_cfdi, metodo_pago_default, modo_acuse, email_facturacion }

GET  /catalogos/clientes/{id}/mercancias
POST /catalogos/clientes/{id}/mercancias
  body: { nombre_humano, bienes_transp, clave_unidad, unidad_desc }
PATCH/DELETE /catalogos/mercancias/{id}
```

## 6. Viajes — admin (Fase 2)

```
POST /viajes                         # admin registra
  body: { cliente_id, unidad_id, operador_id, tipo, fecha,
          origen_texto?, origen_cp?, origen_rfc?,
          destino_texto?, destino_cp?, destino_nombre?, distancia_km?, notas? }
  201:  { ...viaje, estado: "asignado" }
  # validación: según `tipo`, exigir origen y/o destino (02 §5)

GET   /viajes?cliente_id=&estado=&sin_agrupar=true&fecha_desde=&fecha_hasta=&operador_id=&page=&size=
  # lista para el admin; `sin_agrupar=true` = servicio_id null (para la pantalla de agrupar)
GET   /viajes/{id}
PATCH /viajes/{id}                   # editar mientras no esté en servicio facturado
DELETE /viajes/{id}
```

## 7. Viajes — operador (Fase 2, con offline)

```
GET  /operador/viajes?estado=asignado
  # SOLO los viajes del operador autenticado (server filtra por user.operador_id)
  200: [ { ...viaje, cliente, unidad_apodo, origen, destino, modo_acuse } ]

POST /operador/viajes/{id}/cerrar
  headers: Idempotency-Key: <client_action_id UUID>   # o en el body
  body: {
    client_action_id,           # UUID generado en el teléfono (idempotencia)
    hora_llegada?, notas?,
    mercancias: [ { mercancia_frecuente_id, cantidad, peso_kg } ],   # vacío si solo recolección
    ref_acuse?                  # si modo_acuse=referencia
  }
  200: { ...viaje, estado: "cerrado" }
  # IDEMPOTENTE: si client_action_id ya se procesó, responde 200 con el estado actual, sin duplicar.
  # Validación de acuse según cliente.modo_acuse (02 §5).

POST /operador/viajes/{id}/acuse    # subir foto (modo escaneo)
  multipart: file=<imagen>, client_action_id=<UUID>
  200: { acuse: { id, tipo: "escaneo", archivo_key } }
  # también idempotente por client_action_id
```

**Contrato offline (frontend):**
- El operador puede encolar `cerrar` + `acuse` sin conexión; se reenvían al reconectar en orden.
- El backend deduplica por `client_action_id`. Reenviar = seguro.

## 8. Servicios — agrupar y facturar (Fase 3 + 4) — solo admin

```
POST /servicios                      # crear servicio agrupando viajes
  body: { cliente_id, viaje_ids: [UUID], subtotal? }
  201:  { ...servicio, estado: "borrador" }
  # valida: todos los viaje_ids son del mismo cliente y están sin agrupar

GET   /servicios?cliente_id=&estado=&fecha_desde=&fecha_hasta=&page=&size=
  # listado/base de datos; incluye ruta resumida y total
GET   /servicios/{id}                # detalle: viajes, ubicaciones, mercancías, montos calculados
PATCH /servicios/{id}                # editar subtotal, agregar/quitar viajes (solo si borrador)
  body: { subtotal?, add_viaje_ids?, remove_viaje_ids? }
POST  /servicios/{id}/desagrupar     # devuelve viajes a "sin agrupar" (solo si borrador)

GET   /servicios/{id}/validar        # validación pre-timbrado (04 §5)
  200:  { ok: bool, checks: [ { regla, nivel: "ok|warning|error", mensaje } ],
          preview: { subtotal, iva_trasladado, iva_retenido, total } }
```

Facturación (Fase 4):
```
POST /servicios/{id}/facturar        # timbra vía Facturama
  body: { }                          # usa datos ya capturados
  200:  { factura: { id, uuid_fiscal, estado, total, pdf_url, xml_url } }
  409:  si el servicio no está "listo" o ya facturado
  502:  facturama_error (con message del PAC)
  # precondición: GET /validar debe pasar sin errores (solo warnings permitidos)
```

## 9. Facturas — entrega y cancelación (Fase 5) — solo admin

```
GET  /facturas?estado=&cliente_id=&page=&size=
GET  /facturas/{id}                  # incluye urls firmadas de PDF/XML/acuse
POST /facturas/{id}/enviar           # correo al cliente
  body: { to?: [email] }             # default: cliente.email_facturacion
  200:  { enviado_at }
  # adjunta XML + PDF (+ acuse si modo escaneo). Clientes "referencia": sin adjunto de acuse.

POST /facturas/{id}/cancelar         # cancelación ante el SAT vía Facturama
  body: { motivo: "01|02|03|04", uuid_sustitucion? }   # 01 requiere uuid_sustitucion
  200:  { estado: "cancelada", acuse_cancelacion_url }
  # al confirmar el SAT, el servicio vuelve a editable (facturado→cancelado→borrador)
```

## 10. Dashboard y export (Fase 5) — solo admin

```
GET /dashboard/resumen
  200: {
    ingresos: { mes, trimestre, anio, por_cobrar_ppd },     # montos string decimal
    ingresos_por_mes: [ { mes: "2026-09", total } ],        # para la gráfica
    pendientes: { viajes_sin_agrupar, servicios_listos, servicios_sin_acuse },
    servicios_listos: [ { id, cliente, resumen, total, estado } ]
  }

GET /export/servicios.xlsx?fecha_desde=&fecha_hasta=&cliente_id=&estado=
  200: archivo .xlsx (para conciliar con contabilidad)
```

## 11. Archivos (R2)
- Subidas de acuse: vía backend (multipart), guardadas en R2, referenciadas por `archivo_key`.
- Lecturas: el backend genera **URLs firmadas** (presigned, expiración corta) y las devuelve en los detalles; el frontend nunca recibe credenciales de R2.

## 12. Mapa endpoint → fase (para los agentes)
- **Fase 0**: `/health`, `/auth/*`.
- **Fase 1**: `/catalogos/*`.
- **Fase 2**: `/viajes/*`, `/operador/viajes/*` (+ offline).
- **Fase 3**: `/servicios` (crear, listar, editar, desagrupar, detalle).
- **Fase 4**: `/servicios/{id}/validar`, `/servicios/{id}/facturar`.
- **Fase 5**: `/facturas/*`, `/dashboard/*`, `/export/*`.
