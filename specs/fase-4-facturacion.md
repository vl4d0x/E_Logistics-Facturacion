# Fase 4 · Facturación

> **Objetivo**: el corazón. Convertir un servicio "listo" en un CFDI 4.0 + Carta Porte 3.1 timbrado por Facturama, con validación previa. Ya de-risgado por el spike de Fase 0.
> **Depende de**: Fase 3 (servicios), Fase 0 (spike Facturama).
> **Entrega**: timbrado real en sandbox, con PDF y XML guardados; validación pre-timbrado que bloquea errores.
> **Lee antes**: `04-facturacion-cfdi` **completo**, `03-api-contract §8-9`.

## Historias de usuario

### H4.1 — Validación pre-timbrado
Como admin, quiero que el sistema valide el servicio antes de timbrar, para no generar facturas con errores.
**Criterios de aceptación**
- `GET /servicios/{id}/validar` corre todas las reglas de `04-facturacion-cfdi §5` y devuelve `checks[]` con nivel `ok|warning|error` y el `preview` de montos.
- Con algún `error`, el timbrado se **bloquea**; los `warning` se muestran pero permiten continuar.
- Casos que deben marcarse (de la factura real): `PesoBrutoVehicular` que parece kg y no toneladas → warning; permiso SICT incongruente con el servicio → warning; falta de acuse según modo → error.

### H4.2 — Cálculo de impuestos
Como sistema, quiero calcular impuestos correctamente, para que el CFDI cuadre.
**Criterios de aceptación**
- `calcular_impuestos(subtotal, regimen_receptor)`: IVA 16% siempre; retención 4% **solo si moral**; total = subtotal + trasladado − retenido (`04 §3`).
- Ejemplo verificable: subtotal 1650 moral → 264 / 66 / 1848. Física → retención 0.
- `Decimal`, 2 decimales, `ROUND_HALF_UP`.

### H4.3 — Armado del payload CFDI + Carta Porte
Como sistema, quiero mapear el servicio al payload de Facturama, para timbrar.
**Criterios de aceptación**
- Emisor persona física constante (`04 §1`); concepto de flete autogenerado (`04 §2`).
- Ubicaciones: 1 Origen (recolección) + N Destinos (entregas) desde los viajes (`04 §4.2`).
- Mercancías, Autotransporte (unidad) y Figura de transporte (operador con RFC + licencia) mapeados (`04 §4.3-4.5`).
- El armado del payload vive en `modules/facturacion/service.py` y es **testeable sin llamar a Facturama**.
- Hay un test que compara el payload armado contra el **fixture del CFDI real** (INFO REQUERIDA).

### H4.4 — Timbrado
Como admin, quiero facturar un servicio con un clic, para obtener el CFDI timbrado.
**Criterios de aceptación**
- `POST /servicios/{id}/facturar` solo procede si el servicio está `listo` y `GET /validar` no tiene errores; si no, `409`.
- Llama a Facturama (sandbox según `FACTURAMA_ENV`); en éxito guarda `factura` con `uuid_fiscal`, `facturama_id`, montos, `metodo_pago`, `estado=timbrada`, `timbrado_at`.
- Descarga PDF y XML de Facturama y los sube a R2 (`pdf_key`, `xml_key`).
- `servicio.estado` pasa a `facturado`.
- En error del PAC: `estado=error`, se guarda el mensaje de Facturama, responde `502 facturama_error` con detalle; permite reintento.

## Endpoints / pantallas
- Endpoints: `03-api-contract §8` (`/validar`, `/facturar`).
- Pantalla admin: en "Agrupar y facturar", el panel de validación (checks en verde/ámbar/rojo) + desglose IVA/retención + botón "Generar factura" habilitado solo si no hay errores. Tras timbrar, mostrar UUID y enlaces a PDF/XML.

## INFO REQUERIDA (Vlad)
> 🔴 Credenciales del **sandbox de Facturama**. Un **CFDI real (XML + PDF)** como fixture del test de armado. Confirmación de datos del **emisor** y de la **FormaPago** (ver `04 §1, §7`). No subir el CSD al repo.

## Casos borde
- Facturama rechaza por catálogo SAT vencido → mostrar el mensaje, corregir el dato en el catálogo (no en código).
- Timbrado exitoso pero falla la subida a R2 → factura queda timbrada (UUID guardado); reintentar solo la subida, no re-timbrar.
- Doble clic en "Generar factura" → no timbrar dos veces (bloquear/idempotencia por servicio).
- Servicio con retención mal aplicada → la validación lo marca como error.

## Definición de terminado
- [ ] `/validar` implementa todas las reglas de `04 §5`.
- [ ] `calcular_impuestos` pasa los casos del checklist (`04 §10`).
- [ ] Payload coincide con el fixture real (test).
- [ ] Timbrado en sandbox devuelve UUID; PDF+XML en R2.
- [ ] No se puede timbrar con errores de validación ni dos veces.
- [ ] Tests del checklist de `04 §10`.
