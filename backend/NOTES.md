# NOTES — aprendizajes de integración con Facturama (H0.5, spike Fase 0)

> Estructura real del payload de Facturama, verificada contra su documentación oficial
> (`apisandbox.facturama.mx/guias/...`) el 2026-09-23. Sirve de base para `04-facturacion-cfdi`
> y para el mapeo completo de Fase 4. **Vuelve a verificar contra la doc vigente antes de Fase 4**
> por si Facturama cambió algo.

## Endpoints (API Web, single-issuer — la que usamos)

| Acción | Método | Path | Notas |
|---|---|---|---|
| Crear/timbrar CFDI | `POST` | `/3/cfdis` | Nótese: **sin** prefijo `/api`. Devuelve el CFDI timbrado, incluye `Id` y el UUID fiscal en `Complement.TaxStamp.Uuid`. |
| Descargar archivo | `GET` | `/api/Cfdi/{format}/{type}/{id}` | `format` = `pdf`\|`xml`\|`html`. `type` = `issued` (nosotros siempre emitimos). Respuesta: `{ContentEncoding, ContentType, ContentLength, Content}` — `Content` viene en **base64**. |
| Cancelar CFDI | `DELETE` | `/cfdi/{cfdiId}?type=issued&motive={01-04}&uuidReplacement={uuid}` | `uuidReplacement` solo si `motive=01`. Respuesta incluye `Status: "canceled"` o `"pending"` (espera de aceptación 72h). |

Auth: **HTTP Basic** (`FACTURAMA_USER`/`FACTURAMA_PASSWORD`) en todas.
Base URL: sandbox `https://apisandbox.facturama.mx`, producción `https://api.facturama.mx` (según `FACTURAMA_ENV`).

## Estructura del payload de creación (`POST /3/cfdis`)

Campos raíz: `Serie`, `CfdiType` (`"I"` para nosotros — Ingreso), `PaymentForm`, `ExpeditionPlace`,
`PaymentMethod` (`PUE`|`PPD`), `Currency` (`"MXN"`), `Exportation` (`"01"`), `Receiver{}`, `Issuer{}`, `Items[]`, `Complemento{}`.

- `Issuer`: en el ejemplo oficial aparece **vacío** (`"Issuer": {}`) — el sandbox usa el emisor/CSD demo
  configurado en la cuenta. **Para producción hay que confirmar** si hace falta enviar `Rfc`/`Name`/`FiscalRegime`
  explícitos o si los toma del CSD cargado en el panel de Facturama (pendiente de confirmar al conectar cuenta real).
- `Receiver`: `{ Name, CfdiUse, Rfc, FiscalRegime, TaxZipCode }`.
- `Items[]`: **un item = nuestro concepto de flete** (`04-facturacion-cfdi §2`):
  ```json
  {
    "Quantity": "1",
    "ProductCode": "78101802",
    "UnitCode": "SX",
    "Unit": "Envío",
    "Description": "<autogenerada>",
    "UnitPrice": "<subtotal>",
    "Subtotal": "<subtotal>",
    "TaxObject": "02",
    "Taxes": [
      {"Name": "IVA", "Rate": "0.16", "Total": "<subtotal*0.16>", "Base": "<subtotal>", "IsRetention": "false", "IsFederalTax": "true"},
      {"Name": "IVA RET", "Rate": "0.04", "Total": "<subtotal*0.04>", "Base": "<subtotal>", "IsRetention": "true", "IsFederalTax": "true"}
    ],
    "Total": "<subtotal + iva - retencion>"
  }
  ```
  El bloque `IVA RET` **solo se incluye si `cliente.regimen_receptor == moral`** (`04 §3`).
  `TaxObject = "02"` = "sí objeto de impuesto, desglosar a nivel Concepto".

## Complemento Carta Porte 3.1

`Complemento.CartaPorte31`:

```
CartaPorte31
├── TranspInternac        ("No" para nosotros — siempre nacional)
├── TotalDistRec
├── Ubicaciones[]          # TipoUbicacion, IDUbicacion, RFCRemitenteDestinatario,
│                          # NombreRemitenteDestinatario, FechaHoraSalidaLlegada,
│                          # DistanciaRecorrida, Domicilio{Pais,CodigoPostal,Estado,Municipio,Localidad}
├── Mercancias
│   ├── PesoBrutoTotal
│   ├── UnidadPeso         ("KGM")
│   ├── NumTotalMercancias
│   ├── Mercancia[]        # BienesTransp, Descripcion, Cantidad, ClaveUnidad, Unidad, PesoEnKg
│   └── Autotransporte     # ⚠️ ANIDADO DENTRO de Mercancias, no es hermano
│       ├── PermSCT, NumPermisoSCT
│       ├── IdentificacionVehicular{ConfigVehicular, PesoBrutoVehicular, PlacaVM, AnioModeloVM}
│       └── Seguros{AseguraRespCivil, PolizaRespCivil}
└── FiguraTransporte[]     # hermano de Ubicaciones/Mercancias
                           # TipoFigura ("01"), RFCFigura, NumLicencia, NombreFigura
```

Confirma exactamente lo modelado en `04-facturacion-cfdi §4` — el único detalle no obvio es que
**`Autotransporte` vive dentro de `Mercancias`**, no al mismo nivel.

Nota: `Domicilio` en el ejemplo oficial usa `Municipio`/`Localidad` como **claves numéricas del catálogo
SAT** (ej. `"028"`, `"05"`), no texto libre — confirmar contra el catálogo `c_Municipio`/`c_Localidad`
al construir el mapeo real de Fase 4 (nuestro `cliente`/`viaje` solo guardan CP; puede hacer falta
resolver Municipio/Estado desde el CP, o dejar que Facturama lo infiera del CP — **verificar en Fase 4**).

## Perfil fiscal de la cuenta — requisito previo a poder timbrar

Corrido el spike de verdad (2026-09-26) contra la cuenta sandbox real (RFC `ZACE880207MC7`,
el mismo emisor de `04-facturacion-cfdi §1`). Una cuenta nueva **no puede timbrar de inmediato**;
hace falta configurar esto primero (una sola vez, no por cada CFDI):

1. **`PUT /api/TaxEntity`** — datos fiscales del emisor. Es un **reemplazo completo**, no parcial:
   hay que mandar TODOS los campos (`Rfc`, `Email`, `TaxName`, `FiscalRegime`, `TaxAddress{Street,
   Neighborhood, ZipCode, Locality, Municipality, State, Country}`) aunque no cambien, o rechaza con
   "field is required" los que falten.
   - ⚠️ **`TaxAddress.State`** quiere el **nombre completo del catálogo** (`"Estado de México"`),
     **no** la clave SAT de 3 letras (`"MEX"`) que sí se usa en `Domicilio` de Carta Porte — dos
     convenciones distintas dentro de la misma API. Se resuelve con `GET /api/Catalogs/States`.
   - `Municipality`/`Locality`/`StateCode` para un CP se resuelven con
     `GET /Catalogs/PostalCodes?keyword={cp}` (devuelve `StateCode`, `MunicipalityCode`,
     `LocationCode`) — **esto responde el pendiente de abajo** sobre de dónde sacar esas claves
     a partir del CP capturado en `cliente`/`viaje`: se consulta este endpoint, no se hardcodea.
2. **`GET /api/BranchOffice`** — el `TaxAddress` del perfil **no** cuenta como lugar de expedición
   por sí solo. Si devuelve `[]`, hay que crear uno con **`POST /api/BranchOffice`**
   (`{Name, Description, IsDefault, Address{...mismos campos...}}`) — el CP de ese branch office es
   el único valor válido para `ExpeditionPlace` en el CFDI. Error si falta:
   `El atributo 'ExpeditionPlace' debe existir como código postal en alguno de los Lugares de
   expedición en tu Perfil Fiscal`.
3. **`POST /serie/{idBranchOffice}`** — el `Serie` del CFDI debe existir previamente registrado en
   esa sucursal (`{IdBranchOffice, Name, Description?}` — sí, `IdBranchOffice` va **tanto en la URL
   como repetido en el body**, o rechaza "field is required"). `Name`: alfanumérico, 1-10 chars.
   Error si falta: `El atributo 'Serie' debe existir en la sucursal`.
4. **CSD (Certificado de Sello Digital)** — aunque todo lo anterior esté bien, timbrar falla con
   `No fue posible sellar el cfdi: El certificado no puede ser nulo o estar vacio` si la cuenta no
   tiene un CSD cargado. **No hay CSD "demo" gratis para un RFC real** (los CSD de prueba públicos
   de Facturama son solo para el RFC genérico `EKU9003173C9`, no sirven para nuestro emisor real).
   Subir el CSD real (`.cer`+`.key`+contraseña) es responsabilidad de Vlad, **directo en el panel
   de dev.facturama.mx** — nunca por chat con un agente ni al repo (ver `00-overview §0`).
   **Este es el único paso que faltó completar en el spike de Fase 0.**

Endpoints de catálogo usados (todos `GET`, mismo Basic Auth):
- `GET /Catalogs/PostalCodes?keyword={cp}` → `[{StateCode, MunicipalityCode, LocationCode, Name, Value}]`
- `GET /api/Catalogs/States` → `[{Name, Value}]` (para `TaxEntity.TaxAddress.State`, usar `Name`)
- `GET /TaxEntity` → perfil fiscal actual de la cuenta

## Pendiente para Fase 4 (no resuelto por este spike)
- Confirmar si `Issuer{}` vacío en el CFDI basta una vez que el perfil fiscal + CSD ya están
  completos, o hace falta mandar `Rfc`/`Name`/`FiscalRegime` explícitos ahí también — no llegamos
  a probar esto porque el CSD quedó pendiente de subir.
- `IdCCP` (04 §4.1): no apareció en el ejemplo — parece que Facturama lo autogenera. Confirmar en la respuesta del timbrado (una vez que exista CSD y se pueda timbrar de verdad).
- Repetir esta verificación contra la doc vigente antes de escribir el mapeo real (`04-facturacion-cfdi §intro` — "regla de oro").
- ~~Confirmar de dónde sacamos Municipio/Localidad a partir del CP~~ → resuelto arriba (catálogo `PostalCodes`).

## Fuentes
- https://apisandbox.facturama.mx/guias/complementos/complemento-carta-porte-31
- https://apisandbox.facturama.mx/guias/api-web/cfdi/factura
- https://apisandbox.facturama.mx/guias/api-web/cfdi/cancelacion
- https://github.com/Facturama/facturama-python-sdk/wiki/API-Web
- https://apisandbox.facturama.mx/docs/api/GET-BranchOffice, POST-BranchOffice, POST-serie-idBranchOffice
- https://apisandbox.facturama.mx/docs/api/GET-TaxEntity, PUT-api-TaxEntity
- https://facturama.elevio.help/es/articles/151-csd-de-pruebas-principal (CSD de prueba — solo válido para RFC genérico, no para un emisor real)
