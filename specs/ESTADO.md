# Estado del proyecto y guía para continuar

> **Para el siguiente agente.** Léelo después de `00-overview.md`. Resume en qué quedó el
> proyecto, las decisiones que se tomaron con Vlad (que a veces cambian lo que dicen los specs
> numerados) y lo que hay que saber para trabajar sin romper nada.
> **Última actualización:** 11 oct 2026 · último commit en `master`: `91a67f6`.

## 1. Estado general

- Las **fases 0–6 están construidas** y desplegadas en Railway (backend FastAPI + Postgres,
  frontend React/Vite PWA). Ver `00-overview §8`.
- Se trabaja **directo sobre `master`**: cada push despliega a producción (Railway). Vlad prueba
  en producción y pide ajustes de UX/negocio.
- Facturama está en **sandbox** (`FACTURAMA_ENV=sandbox`). Nada de lo timbrado tiene validez
  fiscal. El timbrado real requiere credenciales de producción de Facturama.
- Correos en **modo prueba** (`EMAIL_MODO_PRUEBA=true`, ver §4): ningún correo sale a clientes.

## 2. Decisiones de negocio vigentes (11 oct 2026)

Estas mandan sobre los specs numerados cuando difieran.

**Servicio y viajes**
- Todo servicio tiene **un solo origen y al menos un destino**. En el formulario de Nuevo
  servicio ya no hay pestañas de tipo: se muestran "Origen" + "Destino 1" y el botón
  "+ Destino". Internamente el origen es un viaje `recoleccion` y cada destino un `entrega`.
- Validación en servidor: no se permite un segundo viaje con origen (alta, agregar viaje,
  cambiar tipo). Un origen agregado después se reordena al principio (Carta Porte).
- **CP por viaje**: cada origen/destino puede llevar un CP distinto al del lugar
  (`viaje.origen_cp` / `viaje.destino_cp`). En la Carta Porte se resuelven estado/municipio/
  localidad de ese CP vía Facturama y se omiten calle/número/colonia.
- **Km sugerido** = `lugar.distancia_km` (confirmado) del lugar del viaje: el destino; en una
  recolección, el origen. Sin dato → **70 km con etiqueta "No confirmado"**. El km se edita en
  Catálogos → Lugares. Los km del Excel de Carta Porte se cargaron con la migración `0010`
  (`backend/alembic/data/km_lugares.json`). Mejora pendiente en `specs/IDEAS-FUTURAS.md`.
- Un viaje **terminado** se puede quitar (borra sus mercancías y acuses en BD; los archivos de
  R2 se conservan).

**Operador (PWA)**
- El acuse/folio **solo se pide en entregas**, nunca en recolecciones.
- Acuse escaneado = **un solo PDF** (validado por firma `%PDF` en servidor; subir otro
  reemplaza el anterior). Checklist obligatorio antes de subir: claro, escaneado (no foto),
  corresponde a {DESTINO}, sellado o firmado.
- Al operador no se le muestra `lugar.referencia` si contiene correos (en algunos lugares la
  referencia se sembró con correos del Excel; conviene limpiarla en Catálogos).
- Carga de gasolina: el tercer valor (litros/precio/importe) se calcula y recalcula; si el
  operador lo corrige queda manual. El servidor **ya no rechaza** si litros × precio ≠ importe.

**Facturación**
- Concepto autogenerado (sintaxis acordada):
  ```
  UNIDAD: 1.0 TON          <- capacidad de carga de la unidad (kg/1000, 1 decimal); sin capacidad usa peso bruto
  ORIGEN: CHEMITAL DE MEXICO
  DESTINO: ALIMENTOS PAR   <- varios destinos separados por " / "
  FECHA: 11 OCT 26
  REF: 5151, 5152          <- solo clientes con requiere_folio_concepto (Chemital)
  ```
- **Folio por destino**: es la referencia del acuse (`Acuse.tipo=referencia`) de cada viaje con
  destino. Se edita en Facturar → Concepto (`PUT /viajes/{id}/folio`). Validación: falta folio
  en algún destino = error. `servicio.folio_cliente` quedó como respaldo para servicios viejos.
- Pantalla **Facturar** editable: CP, hora programada y km por ubicación; cambiar/quitar/agregar
  origen y destinos; mercancías (cambiar, cantidad, peso, quitar, agregar); unidad y operador;
  uso CFDI y método de pago. Datos fiscales del receptor se editan en la ficha del cliente.
- **Timbrado anticipado** con dos modos (`servicio.timbrado_modo`): `precio` o `cero`
  ("Timbrar con $0 y cancelar": subtotal simbólico $0.10, se descarga PDF/XML y se cancela solo
  con motivo 02). Si el servicio no tiene mercancías se agrega 1 kg de "Preservativos de
  alimentos" (12164501 / X4G, del catálogo del cliente o se crea ahí).
- Total con IVA (y retención 4% si es persona moral) visible bajo cualquier subtotal.
- **Desglose de precio** (sección en Facturar): monto por destino (`viaje.monto_desglose`,
  `PUT /servicios/{id}/desglose-precio`). No va al CFDI. Si se captura, debe cubrir todos los
  destinos y sumar el subtotal (error de validación); sin capturar con varios destinos = warning.
  Con un solo destino sin monto, ese destino se lleva todo el subtotal. Se puede corregir con
  factura vigente si cuadra con el subtotal timbrado.
- **Texto del correo por cliente** (`cliente.plantilla_correo`, editable en la ficha del cliente):
  marcadores `{folio} {dia} {mes} {anio}` (fecha del servicio) `{operador} {unidad} {origen}
  {destinos}`. Sin plantilla = "Buen día, envío la factura #{folio}, correspondiente al día {dia}
  de {mes} del {anio}." (el de Parautos). La migración `0011` cargó los de Aerzen, Chemital,
  Farmabiot y Lesaffre. Debajo del texto va la tabla del desglose (si está completo).
- Correo de factura: XML + PDF + **un solo PDF de evidencia** con todos los acuses unidos
  (`pypdf`), nombre `FACT #<folio>-<NOMBRE COMERCIAL>_EVIDENCIA.pdf`.

**Otra razón social del mismo cliente** (`cliente.hereda_de_id`, "Usa los lugares y mercancías de"
en la ficha del cliente): AERZEN RENTAL MEXICO usa los lugares (incluido el origen predeterminado) y
las mercancías de AERZEN, en vivo; si no tiene texto de correo propio usa el de AERZEN. Sus datos
fiscales son propios. Un solo nivel. La migración `0014` los ligó por RFC.

**Re-escaneo del acuse** (`viaje.reescaneo_*`, migración `0015`): desde Facturar o el detalle del
servicio un admin pide "Solicitar re-escaneo" (con motivo); el operador puede "No pude escanear el
acuse" (con advertencia) y la entrega queda igual. La etiqueta aparece en la lista (filtro "Acuses
pendientes / re-escaneo", que también usa el dashboard), **bloquea el timbrado** y se quita sola al
subir un escaneo nuevo. `POST/DELETE /viajes/{id}/reescaneo`. El buscador de servicios (`q`) y los
filtros `acuses_pendientes` / `inspeccion_fallas` ya funcionan (antes se ignoraban).

**Catálogos y Carta Porte (11 oct 2026, prueba de punta a punta)**
- RFC de lugar `XEXX010101000` (extranjeros) **no se acepta**: el transporte es nacional y el SAT lo
  rechaza. La migración `0012` pasó los 3 lugares que lo traían a `XAXX010101000`.
- Lugar nuevo: al escribir el CP se llena solo el estado (`GET /catalogos/codigos-postales/{cp}`, vía
  Facturama). La colonia solo se manda a la Carta Porte si es clave SAT de 4 dígitos.
- Mercancía: casilla "Declarar material peligroso: No" para claves de `c_ClaveProdServCP` que lo exigen
  (p. ej. medicamentos 51111617). Se copia al viaje como el resto de las claves (`0013`).
- **Hora de México en todo lo fiscal**: la fecha/hora real de la Carta Porte (`terminado_at`, en UTC)
  se convierte a hora de México (`app/core/tiempo.py`); los meses del dashboard, filtros por mes y
  "hoy" de los formularios también. Antes, después de las 18:00 todo caía en el día siguiente.
- Si el REP falla al timbrar en "Aplicar y generar REP", el pago queda aplicado y la respuesta es OK con
  `rep_error` (antes respondía error y el admin podía capturar el pago dos veces).
- Los errores de Facturama traen el detalle de `ModelState` y una pista de dónde corregir.

## 3. Pendientes conocidos

- ✅ Datos fiscales de clientes: Vlad corrigió razón social/CP de Aerzen, Lesaffre, Parautos y
  Farmabiot (11 oct 2026). Los 6 clientes (incluido AERZEN RENTAL) timbran en sandbox con CSD real.
- FARMABIOT sigue sin lugares ni mercancías en producción (se dan de alta desde la app).

- **Cancelación en el sandbox no funciona**: Facturama responde 500 ("Ups! Ocurrió un problema
  al cancelar…") con cualquier motivo/ruta. Probablemente porque el sandbox no registra en el
  SAT. Por eso "$0 y cancelar" deja la factura timbrada y avisa. Solo se podrá validar en
  producción (o preguntando a soporte de Facturama).
- Timbrado **real** aún no probado (sandbox sí timbra con el CSD real de Vlad).
- Error común al timbrar: `RFCFigura no se encuentra en l_RFC` → el RFC del operador del
  servicio no está inscrito en el SAT; se corrige en Catálogos → Operadores.
- No hay **bitácora de auditoría** (quién borró/archivó qué). Ofrecida a Vlad, no pedida aún.
- Detalles de nombres que Vlad puede querer ajustar: cliente en el nombre de la evidencia
  (hoy nombre comercial), folio con o sin serie.
- Specs numerados no se actualizaron con todas las decisiones de §2 (sí `04` para el concepto).

## 4. Variables de entorno relevantes (backend)

Secretos solo en Railway / `backend/.env` (gitignored). **Nunca** en el chat ni en el repo.

| Variable | Notas |
|---|---|
| `FACTURAMA_USER`, `FACTURAMA_PASSWORD`, `FACTURAMA_ENV` | Hoy `sandbox`. Las credenciales de sandbox dan 401 en producción. |
| `EMISOR_RFC`, `EMISOR_NOMBRE`, `EMISOR_LUGAR_EXPEDICION` | Datos del emisor (régimen 612). |
| `EMAIL_MODO_PRUEBA` | Default `true` en código. Con `true` todo correo va a `EMAIL_PRUEBA_DESTINO` (o `EMAIL_REPLY_TO`) con "[PRUEBA]". Poner `false` solo al facturar de verdad. |
| `EMAIL_PRUEBA_DESTINO` | Buzón de pruebas (opcional). |
| `R2_*` | Cloudflare R2. Las URLs firmadas usan **SigV4** (R2 rechaza SigV2). |
| `RESEND_API_KEY` | Envío de correo. |

## 5. Entorno local (PC de Vlad "Cristi", Windows)

- Instalados: Node 24 LTS y Python 3.12 (winget). `backend/.venv` creado; `frontend/node_modules` instalado.
- `backend/.env` existe con credenciales de **sandbox** y otras copiadas de Railway; su
  `DATABASE_URL` es un placeholder de Railway (`${{Postgres.DATABASE_URL}}`), no sirve local.
- No hay Docker. Para correr local se usó **SQLite** con un script en el scratchpad que fija
  `DATABASE_URL=sqlite:///…`, hace `SQLModel.metadata.create_all` (importando `app.main`
  primero para registrar todos los modelos), siembra un admin de prueba y arranca uvicorn.
  Para no tocar recursos reales se vaciaron `R2_*` y `RESEND_API_KEY` por variable de entorno.
- **Tests del backend**: con `backend/.env` presente fallan 2 tests que asumen "sin
  credenciales de Facturama". Correrlos con el `.env` apartado:
  `Rename-Item .env .env.aside; pytest; Rename-Item .env.aside .env`. Último resultado: todo verde.
- Frontend: `npm run build` (= `tsc -b && vite build`) y `npx vitest run`. No hay ESLint configurado.
- Las líneas de los archivos están mezcladas LF/CRLF (`core.autocrlf=true`): al editar con
  regex, normaliza `\r\n`.

## 6. Trampas que ya mordieron

- **La PWA servía la versión vieja** tras cada deploy. Desde `34720e1` la app muestra
  "Hay una versión nueva — Actualizar" (`frontend/src/app/UpdatePrompt.tsx`,
  `registerType: "prompt"`). Si Vlad reporta "no cambió", primero: deploy terminado + Ctrl+Shift+R.
- El sandbox de Facturama valida estricto con CSD real: nombre del receptor = RFC, `RFCFigura`
  en l_RFC. Para pruebas usar el receptor ficticio del SAT `EKU9003173C9` / `ESCUELA KEMPER URGATE` / CP 42501.
- `.misc/` (gitignored) tiene el Excel `CartaPorte.xlsx`; no hay `.misc/PENDIENTES-VLAD.md` en esta PC.

## 7. Migraciones agregadas en esta sesión

`0008` servicio.timbrado_modo · `0009` lugar.distancia_km/km_confirmado + viaje.origen_cp/destino_cp ·
`0010` carga de km por destino desde `alembic/data/km_lugares.json` · `0011` viaje.monto_desglose +
cliente.plantilla_correo (con los textos por cliente) · `0012` RFC XEXX → XAXX en lugares ·
`0013` mercancía.declarar_material_peligroso (y su copia en viaje_mercancia) · `0014`
cliente.hereda_de_id (AERZEN RENTAL → AERZEN) y nombres de clientes sin espacios sobrantes. · `0015`
viaje.reescaneo_motivo/_solicitado_at/_solicitado_por.

## 8. Cómo se probó de punta a punta sin tocar producción

Base SQLite local con los catálogos **copiados de producción por API (solo GET)**, sandbox de Facturama
(el mismo de producción), R2 simulado en disco y correo en modo prueba forzado; la UI se recorrió con
Playwright como admin (1280 px) y como operador (390 px). Así se pueden crear servicios y timbrar sin
dejar datos de prueba en la base real.
