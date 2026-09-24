# 04 · Facturación CFDI + Carta Porte 3.1

> **El spec más delicado.** Aquí vive el mapeo de un `servicio` a un CFDI 4.0 tipo Ingreso con Complemento Carta Porte 3.1, timbrado por **Facturama**. Un error aquí = factura rechazada o multa del SAT. Este documento está calibrado contra una **factura real de Elogistics de agosto 2026** (los valores de ejemplo salen de ahí).
>
> **Regla de oro para el agente**: los nombres exactos de los campos JSON los define **Facturama**, no este documento. Usa la estructura de abajo como el *qué* (qué dato va dónde a nivel SAT) y **verifica los nombres de propiedades contra la documentación vigente de Facturama para CFDI 4.0 + Carta Porte 3.1** (`https://apisandbox.facturama.mx` / docs de Facturama) antes de dar por buena la integración. No inventes claves de catálogo SAT: Facturama las valida y rechaza las vencidas.

## 1. Naturaleza del comprobante

- **TipoDeComprobante**: `I` (Ingreso — cobramos flete).
- **Version CFDI**: `4.0`. **Version Carta Porte**: `3.1`.
- **Emisor**: persona física. Del ejemplo real:
  - RFC `ZACE880207MC7`, Nombre `ENRIQUE JAVIER ZAMORA CALLEJA`, `RegimenFiscal = 612`.
  - `LugarExpedicion` = CP de expedición (ej. `52176`).
- **Moneda** `MXN`, `TipoCambio` `1`, `Exportacion` `01`.
- Estos datos del emisor son **constantes** (config, no capturados por servicio). Guárdalos en settings/config, no hardcodeados en el código.

> 🔴 **INFO REQUERIDA (Vlad)** — confirma los **datos fiscales del emisor** (persona física) que van como constantes: RFC, nombre, régimen fiscal (612) y CP de expedición (`LugarExpedicion`). Definen quién factura; no los tomes del XML de ejemplo sin que Vlad confirme que siguen vigentes, ni subas su Certificado de Sello Digital (CSD) al repo.

## 2. Regla del concepto (partida)

Un servicio = **un concepto** de flete. Es casi fijo:
- `ClaveProdServ = 78101802` (Servicios de transporte de carga por carretera) — **constante**.
- `ClaveUnidad = E48` o `SX`… (usar la del ejemplo real: `SX`, Unidad `Envío`) — **constante**.
- `Cantidad = 1`.
- `ValorUnitario = Importe = servicio.subtotal`.
- `ObjetoImp = 02` (sí objeto de impuesto).
- `Descripcion`: **autogenerada** desde los viajes del servicio, p.ej.:
  ```
  FLETE UNIDAD {apodo}
  ORIGEN: {origen del viaje de recolección}
  DESTINO: {destinos de las entregas, separados por " / "}
  FECHA: {fecha(s)}
  ```
  (Esto reemplaza el texto que hoy se teclea a mano.)

## 3. Impuestos — retención 4% CONDICIONAL

Sobre la base = `subtotal`:
- **IVA trasladado 16%** siempre: `Traslado {Impuesto:002, TipoFactor:Tasa, TasaOCuota:0.160000, Importe: subtotal*0.16}`.
- **Retención IVA 4%** **solo si `cliente.regimen_receptor = moral`**: `Retencion {Impuesto:002, TipoFactor:Tasa, TasaOCuota:0.040000, Importe: subtotal*0.04}`.
  - Fundamento: el autotransporte de carga a persona moral obliga a la retención del 4% de IVA. A persona física, **no** aplica.
- **Total** = `subtotal + iva_trasladado − iva_retenido`.

Ejemplo real (Chemital, persona moral):
```
subtotal        = 1650.00
iva_trasladado  = 264.00   (16%)
iva_retenido    =  66.00   (4%)
total           = 1848.00
```

> Implementación: función pura `calcular_impuestos(subtotal: Decimal, regimen_receptor) -> {trasladado, retenido, total}`. Redondeo a 2 decimales, `Decimal`, `ROUND_HALF_UP`.

## 4. Complemento Carta Porte 3.1 — mapeo

### 4.1 Atributos raíz
- `TranspInternac = "No"`.
- `TotalDistRec` = suma de distancias recorridas (km) del servicio.
- `IdCCP` = identificador único del complemento (RFC 4122 / lo genera el emisor o Facturama según su API — verificar quién lo genera en Facturama).

### 4.2 Ubicaciones (aquí vive "un servicio = varios viajes")
Un servicio de N viajes produce **una secuencia de ubicaciones**: 1 Origen (la recolección) + N Destinos (las entregas).

Por cada ubicación:
| Campo Carta Porte | Origen | Destino |
|---|---|---|
| `TipoUbicacion` | `Origen` | `Destino` |
| `RFCRemitenteDestinatario` | RFC del cliente (remitente) | `XAXX010101000` (genérico) o RFC real del destinatario |
| `NombreRemitenteDestinatario` | — | nombre del destinatario (ej. "GUADALUPE LIMON") |
| `FechaHoraSalidaLlegada` | salida del origen | llegada al destino |
| `DistanciaRecorrida` | — | km de ese tramo |
| `Domicilio` | `{ Municipio, Estado, Pais:MEX, CodigoPostal }` del origen | idem del destino |

> Del ejemplo: Origen RFC `CME091007LG1` (Chemital), CP `52004`; Destino `XAXX010101000` nombre `GUADALUPE LIMON`, CP `52000`, distancia `80`.

### 4.3 Mercancías
- `PesoBrutoTotal` = suma de `peso_kg` de todos los `viaje_mercancia` del servicio; `UnidadPeso = KGM`.
- `NumTotalMercancias` = conteo.
- Por cada mercancía (de `viaje_mercancia`): `{ BienesTransp (clave SAT), Descripcion, Cantidad, ClaveUnidad, Unidad, PesoEnKg }`.
  - Ejemplo: `BienesTransp 12164501`, `Descripcion "Preservativos de alimentos"`, `ClaveUnidad X4G`, `Unidad "Caja de cartón"`, `PesoEnKg 20`.

### 4.4 Autotransporte (de la `unidad`)
- `PermSCT` = `unidad.perm_sct`, `NumPermisoSCT` = `unidad.num_permiso_sct`.
- `IdentificacionVehicular`: `{ ConfigVehicular, PesoBrutoVehicular, PlacaVM, AnioModeloVM }`.
- `Seguros`: `{ AseguraRespCivil, PolizaRespCivil }`.

### 4.5 Figura de transporte (del `operador`)
- `TiposFigura`: `{ TipoFigura: "01" (operador), RFCFigura: operador.rfc, NumLicencia: operador.num_licencia, NombreFigura: operador.nombre }`.

## 5. Validación pre-timbrado (endpoint `GET /servicios/{id}/validar`)

Antes de llamar a Facturama, corre estas reglas y devuelve `checks[]`. **Bloquea el timbrado si hay algún `error`**; los `warning` se muestran pero permiten continuar.

| Regla | Nivel si falla | Detalle |
|---|---|---|
| Servicio tiene ≥1 viaje | error | |
| Subtotal presente y > 0 | error | |
| Todos los viajes del mismo cliente | error | |
| Cada entrega tiene su acuse según `modo_acuse` | error/warning | escaneo→archivo; referencia→folio; ninguno→ok |
| Peso bruto total ≤ capacidad de la unidad | warning | comparar contra config/capacidad |
| `PesoBrutoVehicular` de la unidad es plausible (en **toneladas**, no kg) | warning | En la factura real venía `500` porque se capturó como kg; **debe ser toneladas**. Avisar si el valor parece kg. |
| Permiso SCT congruente con el servicio | warning | En el ejemplo, `TPAF14` es de paquetería/mensajería para un flete de carga → revisar. |
| Fecha de origen anterior a la de destino | error | |
| Cliente tiene RFC, CP y régimen | error | |
| Operador tiene RFC y licencia | error | |
| Retención 4% aplicada sii receptor moral | error | consistencia de impuestos |

Devuelve también el `preview` de montos (subtotal, iva_trasladado, iva_retenido, total).

## 6. Timbrado vía Facturama (`POST /servicios/{id}/facturar`)

1. Recalcular impuestos y armar el payload CFDI 4.0 + Carta Porte 3.1 (secciones 1–4).
2. Llamar a la API de Facturama para **crear/timbrar** el CFDI (Facturama sella y timbra ante el SAT).
3. En éxito:
   - Guardar `factura`: `uuid_fiscal`, `facturama_id`, montos, `metodo_pago`, `estado=timbrada`, `timbrado_at`.
   - Descargar **PDF y XML** desde Facturama y subirlos a R2 (`pdf_key`, `xml_key`).
   - `servicio.estado = facturado`, ligar `factura_id`.
4. En error del PAC: `estado=error`, guardar el mensaje de Facturama, devolver `502 facturama_error` con el detalle. Permitir reintento.

Cliente HTTP en `integrations/facturama.py`: Basic Auth (`FACTURAMA_USER`/`FACTURAMA_PASSWORD`), base URL según `FACTURAMA_ENV` (`apisandbox.facturama.mx` vs producción). Timeout y manejo de errores explícito. **Toda** la construcción del payload vive en `modules/facturacion/service.py`, testeable sin llamar a Facturama (con un test que compara el payload armado contra un fixture del ejemplo real).

> 🔴 **INFO REQUERIDA (Vlad)** — para construir y probar el mapeo, Vlad debe entregar: (1) las **credenciales del sandbox de Facturama**, y (2) al menos un **CFDI real de Elogistics (XML + PDF)** para usarlo como *fixture* del test que compara el payload armado. Sin ese XML de referencia, el test de equivalencia no puede escribirse.

## 7. Método de pago y REP

- `metodo_pago` viene de `cliente.metodo_pago_default` (la mayoría **PPD**), overrideable por servicio.
- PPD ⇒ `MetodoPago=PPD`, `FormaPago=99` (por confirmar).

> 🔴 **INFO REQUERIDA (Vlad)** — confirma la **`FormaPago`** correcta por defecto (p. ej. `99` para PPD) y si algún cliente usa **PUE** en lugar de PPD.
- **REP (complemento de pago)**: cuando el cliente paga, se emite un CFDI de tipo `P` con complemento de pago referenciando el UUID de esta factura. **BACKLOG** — la tabla `pago_rep` ya está modelada (`02 §3.11`). No implementar en MVP, pero **no bloquear** el diseño: dejar `metodo_pago` y el UUID accesibles para cuando se construya.

## 8. Cancelación (`POST /facturas/{id}/cancelar`)

- Llama al endpoint de cancelación de Facturama con `motivo ∈ {01,02,03,04}`.
  - `01` (comprobante con errores con relación) requiere `uuid_sustitucion` (el UUID del CFDI que lo reemplaza).
  - `02` errores sin relación, `03` no se llevó a cabo la operación, `04` operación nominativa en factura global.
- Guardar `motivo_cancelacion`, `uuid_sustitucion`, `estado=cancelada`, y el **acuse de cancelación** (XML del SAT) en R2.
- Al confirmarse la cancelación, `servicio.estado`: `facturado → cancelado`, y queda editable (`cancelado → borrador` al re-editar).

## 9. Catálogos SAT — no hardcodear

Las claves del SAT (`c_ClaveProdServCP`, `c_ClaveUnidad`, `c_ConfigAutotransporte`, `c_CodigoPostal`, tipos de permiso, materiales peligrosos) cambian (hubo actualización en enero 2026). **No las quemes en código.** Se guardan por dato de negocio en nuestros catálogos (`unidad`, `mercancia_frecuente`) y **Facturama valida** contra catálogos vigentes al timbrar. Si Facturama rechaza por catálogo vencido, se corrige el dato en el catálogo, no en el código.

## 10. Checklist de aceptación (para tests de la Fase 4)

- [ ] `calcular_impuestos` da 264.00 / 66.00 / 1848.00 para subtotal 1650 y receptor moral.
- [ ] Receptor persona física ⇒ retención 4% = 0.
- [ ] Un servicio con 1 recolección + 2 entregas produce 1 Origen + 2 Destinos en `Ubicaciones`.
- [ ] `PesoBrutoTotal` = suma de pesos de las mercancías.
- [ ] La `Descripcion` del concepto se autogenera desde unidad/origen/destino/fecha.
- [ ] La figura de transporte incluye RFC y NumLicencia del operador.
- [ ] `GET /validar` bloquea timbrado sin subtotal y con acuse faltante (modo escaneo).
- [ ] El payload armado coincide (campos SAT) con el fixture del CFDI real de agosto.
- [ ] Timbrado en sandbox devuelve UUID y se guardan PDF+XML en R2.
- [ ] Cancelación con motivo 01 exige uuid_sustitucion.
