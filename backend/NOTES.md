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

## Pendiente para Fase 4 (no resuelto por este spike)
- Confirmar si `Issuer{}` vacío basta también en producción o hace falta mandar RFC/Nombre/Régimen.
- Confirmar de dónde sacamos `Municipio`/`Localidad` (claves SAT) a partir del CP capturado en `viaje`/`cliente`.
- `IdCCP` (04 §4.1): no apareció en el ejemplo — parece que Facturama lo autogenera. Confirmar en la respuesta del timbrado.
- Repetir esta verificación contra la doc vigente antes de escribir el mapeo real (`04-facturacion-cfdi §intro` — "regla de oro").

## Fuentes
- https://apisandbox.facturama.mx/guias/complementos/complemento-carta-porte-31
- https://apisandbox.facturama.mx/guias/api-web/cfdi/factura
- https://apisandbox.facturama.mx/guias/api-web/cfdi/cancelacion
- https://github.com/Facturama/facturama-python-sdk/wiki/API-Web
