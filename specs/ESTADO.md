# Estado del proyecto y guía para continuar

> **Para el siguiente agente.** Léelo después de `00-overview.md`. Resume en qué quedó el
> proyecto, las decisiones que se tomaron con Vlad (que a veces cambian lo que dicen los specs
> numerados) y lo que hay que saber para trabajar sin romper nada.
> **Última actualización:** 3 nov 2026 (noche) · Facturar con Excel, avisos de REF, importación del
> Facturador Electrónico, dashboard con centavos (migraciones `0016`–`0017`, último commit `63d6a12`).

## 1. Estado general

- Las **fases 0–6 están construidas** y desplegadas en Railway (backend FastAPI + Postgres,
  frontend React/Vite PWA). Ver `00-overview §8`.
- Se trabaja **directo sobre `master`**: cada push despliega a producción (Railway). Vlad prueba
  en producción y pide ajustes de UX/negocio.
- ⚠️ **Facturama ya está en PRODUCCIÓN** (`FACTURAMA_ENV=production` en Railway desde el 3 nov
  2026): **todo lo que se timbre desde la app en producción es una factura real ante el SAT y
  gasta folios pagados**. Todavía **no se ha hecho ninguna prueba** en producción. Ver §1.1.
- Correos en **modo prueba** (`EMAIL_MODO_PRUEBA=true`, ver §4): ningún correo sale a clientes.

## 1.1 Paso de Facturama a producción (en curso, 3 nov 2026)

**Hecho por Vlad (fuera del repo):**
- Creó la cuenta de **producción** de Facturama y compró lo necesario (módulo API, que es
  anual, y folios de API de prepago). **No compró el Complemento Carta Porte** ($1,400 pago
  único, publicado en la página de planes): Facturama no aclara si hace falta para timbrar Carta
  Porte por **API Web**. Si el primer timbrado real falla por un complemento no contratado, esa es
  la causa: Vlad tendría que comprarlo en su perfil de Facturama, no hay que cambiar código.
- Puso en Railway (servicio backend `E_Logistics-Facturacion`) `FACTURAMA_ENV=production` +
  `FACTURAMA_USER`/`FACTURAMA_PASSWORD` de producción. Ya estaban bien y no cambiaron:
  `FACTURAMA_SERIE=ELG`, `EMISOR_RFC=ZACE880207MC7`, `EMISOR_NOMBRE=ENRIQUE JAVIER ZAMORA
  CALLEJA`, `EMISOR_REGIMEN_FISCAL=612`, `EMISOR_LUGAR_EXPEDICION=52176`.
- `backend/.env` **local se queda en sandbox** a propósito (las pruebas locales no deben gastar
  folios ni timbrar facturas reales).

**Pendiente, en este orden:**
1. **Sin confirmar**: si en la cuenta de producción de Facturama están el perfil fiscal (nombre
   idéntico a `EMISOR_NOMBRE`, régimen 612, CP 52176), el **CSD** subido y la serie **`ELG`**
   registrada en la sucursal. Sin la serie: *"El atributo 'Serie' debe existir en la sucursal"*.
2. ~~Limpiar los datos de prueba~~: **Vlad decidió no hacerla** (3 nov 2026). La base de
   producción conserva los servicios, facturas y pagos timbrados en el **sandbox**, mezclados con
   los reales. Esas facturas viejas no existen en la cuenta de producción de Facturama: cancelarlas,
   descargarlas de nuevo o generarles un REP desde la app fallará (Facturama no las encuentra).
   No corras `limpiar_operacion` sin que Vlad lo pida.
3. **Primera factura real de bajo monto** a un cliente de confianza (el receptor ficticio
   `EKU9003173C9` ya no sirve en producción). Validar el UUID en verificacfdi.facturaelectronica.sat.gob.mx.
4. **Probar la cancelación** (motivo 02 + refacturar): nunca se pudo verificar porque el sandbox
   respondía 500. Revisar si la respuesta trae `Status: canceled|pending` como dice la doc.
5. **Probar un REP** registrando un pago de esa factura.
6. Solo después: `EMAIL_MODO_PRUEBA=false` (revisar antes correos y texto de correo de cada cliente).

**Lo que puede hacer fallar el timbrado real:** la licencia de Felipe está vacía (bloquea a
propósito); el régimen fiscal y el uso CFDI de Aerzen, Lesaffre, Parautos y Farmabiot siguen en
601/G03 por defecto y el SAT los rechaza si no coinciden con la Constancia del cliente; el RFC de un
operador que no esté en l_RFC.

**Costos (páginas públicas de Facturama, nov 2026):** módulo API $1,650/año (API Web y
Multiemisor); folios de API $0.50 c/u (1–10k), vigencia de 1 año; los "folios web" **no** sirven
para la API. Unos 2 folios por servicio: factura + REP (todas son PPD).

## 1.2 Pendientes inmediatos (al cierre del 3 nov 2026)

Todo lo de abajo ya está en `master` y desplegado por push; **nada de esto se probó en producción** (solo en
local con Postgres en Docker y el sandbox de Facturama).

1. **Confirmar el deploy** de `0016`/`0017` (Railway corre `alembic upgrade head` en el pre-deploy). El agente
   no pudo leer Railway (el permiso de la CLI fue denegado) ni encontró la URL del backend en el repo.
2. **Importar en producción el reporte del Facturador** (Facturas → "Importar del Facturador",
   `.misc/Emision_ZACE880207MC7_20230529_20261103.xlsx`). Lo hace Vlad desde la pantalla. En local dio 3,377
   facturas: 3,153 vigentes (3,064 pagadas, 89 con saldo = **$600,830.86**, de ellos 2023 $108,584.00) y 224
   canceladas. **Cuadra al centavo con el dashboard de Facturador.com** por año (2024 por cobrar $12,096.00,
   2025 $128,469.74, 2026 $351,681.12) y en el top por cliente de 2026.
3. **Completar CP y régimen fiscal** de los clientes que crea la importación (en local fueron 17: SAFMEX,
   FORTA LAB, SUSTAINABLE TOMORROW, ALIANZAS AGSL, A.N.A. Seguros, Seguros SURA, etc.). Sin eso el REP responde
   "Completa el código postal y el régimen fiscal…". AERZEN RENTAL ya existe en producción y debería ligarse solo.
4. **Primer REP real** de monto bajo (tampoco se ha probado en producción) y validar su UUID en el SAT.
5. Vlad preguntó qué hacer con las 89 facturas con saldo del Facturador (algunas de 2023): **sin respuesta aún**.
   Opciones que se le ofrecieron: dejarlas, o marcarlas cobradas/incobrables (no existe esa función todavía).
6. Pendientes anteriores que siguen: §1.1 pasos 1, 4, 5 y 6 (serie/CSD en Facturama producción, cancelación,
   REP, quitar `EMAIL_MODO_PRUEBA`). Parece que ya se timbró la primera factura real: `.misc/factura.xml` es
   `Serie="ELG" Folio="1"` del 3 nov 2026 16:02 (no confirmado con Vlad).

**Reglas de operación que se le explicaron a Vlad** (que no se pierdan):
- Desde ahora **cada pago se registra solo en la app nueva**; un REP del mismo pago en los dos sistemas
  duplicaría el comprobante ante el SAT.
- Si hace REP en el Facturador después de bajar el reporte, **re-importar antes** de registrar pagos aquí.
- Los REP hechos aquí no aparecen en Facturador.com: ahí esas facturas seguirán "por cobrar". La app nueva es
  la que lleva la cuenta buena.

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
- **Asunto del correo de factura** (Vlad, 3 nov 2026), igual para todos: `FACT#<serie><folio> ELOGISTICS-<NOMBRE COMERCIAL>` (p. ej. `FACT#ELG4 ELOGISTICS-CHEMITAL`)
  (`facturas.asunto_factura`).
- **Fotos de evidencia** (`foto_evidencia`, migración `0018`; `servicios/fotos.py`): opcionales, para **cualquier
  cliente** (no dependen de `modo_acuse` ni cuentan como acuse). Se eligen en Facturar con Excel ("Fotos de
  evidencia (opcional)", se suben al crear el servicio) y se ven/agregan/quitan en la pantalla Facturar. El
  navegador las reduce a ≤1600 px JPEG antes de subirlas (HEIC que el navegador no lea va tal cual); máx. 10 por
  servicio y 10 MB c/u. Van al correo de la factura como `FACT #<folio>-<CLIENTE>_EVIDENCIA_FOTO_<n>.jpg`.
- **Todo correo (facturas y REP) lleva copia (CC) a `EMAIL_COPIA`** (default `e_logistics@outlook.com`; no se
  duplica si ya es destinatario).
- **"Enviar todas"** (Facturar con Excel y Facturas; `GET /facturas/envio-pendiente`,
  `POST /facturas/enviar-pendientes`): muestra la lista con a quién va cada una, se pueden desmarcar, y envía
  cada factura a los `emails_facturacion` de su cliente. Solo toma facturas de la app, vigentes, sin
  `enviado_at`, que no sean de "Timbrar con $0" y **timbradas desde el 3 nov 2026**
  (`facturas.ENVIO_EN_BLOQUE_DESDE`, para no mandar las del sandbox que siguen en la base de producción). Nunca
  dos veces: cada factura se bloquea con `FOR UPDATE SKIP LOCKED` y se revisa `enviado_at` ya bloqueada
  (probado en Postgres local con dos peticiones simultáneas). Un fallo no detiene las demás.
- **En modo prueba ya no se marca `enviado_at`** (el cliente no la recibió): la factura sigue "Sin enviar" y el
  detalle dice "Solo se envió de prueba a …".

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

**28 oct 2026**
- **Mensaje para WhatsApp** con botón de copiar, al crear el servicio y desde su detalle
  (`features/servicios/components/MensajeWhatsappModal.tsx`, `mensajeWhatsapp.ts`). Operador,
  acompañantes, unidad y, por destino, kg y hora de cita (opcionales) se precargan y se editan.
- `backend/scripts/limpiar_operacion.py`: borra servicios, viajes, facturas, pagos, REP y lo que
  cuelga de ellos, en una sola transacción. No toca catálogos, usuarios, configuración, R2 ni
  Facturama. Sin `--confirmar` solo cuenta.

**3 nov 2026 — Facturar con Excel** (`/admin/facturar-excel`, menú "Facturar con Excel")
- Vlad sube su `REGISTROS ELOGISTICS 2024.xlsx` **una vez**; se guarda en la base (`registro_excel`, bytea)
  hasta que suba otro. Se lee la primera hoja cuyo encabezado trae FECHA, CLIENTE, DESTINO y FACTURA
  (hoy `Hoja1`; columnas por nombre, no por posición).
- Escribe el **número de fila** y la app propone cliente, operador, unidad (por placa; **"KICKS" = SAVEIRO
  BLANCA**, regla fija en `matching.UNIDAD_ALIAS_FIJOS`), fecha, subtotal, origen (el predeterminado del
  cliente si el Excel dice el nombre del cliente) y destinos. Solo se captura por destino la REF o el escaneo
  PDF, los kg (si las notas dicen "820KG" se precargan) y la mercancía.
- Búsqueda de destinos (`app/modules/registro_excel/matching.py`, funciones puras con pruebas): IDF para que
  palabras comunes pesen poco, ciudades/notas pegadas ("TEPOTZOTLAN, QUALTIA", "(TIRO EN FALSO)") no son otro
  destino, la celda se parte en varios destinos con la combinación que mejor encaja. Lo que el admin elige
  se **recuerda** (`registro_excel_alias`) para la siguiente vez.
- Destino que no está en el catálogo: se da de alta en los lugares del cliente con **RFC XAXX010101000,
  estado MEX, CP 50000 (editable) y 70 km**.
- **Regla de negocio: SAFMEX se factura a LESAFFRE** (Vlad, 3 nov 2026). Si la columna CLIENTE del Excel dice
  "SAFMEX" (también "SAFMEX BERTHA"), el cliente es LESAFFRE (`LMA200417HY5`) siempre, por encima de lo
  recordado (`matching.CLIENTE_ALIAS_FIJOS`), y un origen "SAFMEX" es el origen predeterminado de Lesaffre.
  **Jamás se timbra al RFC de SAFMEX (`SAF810323HF8`)**: `catalogos/reglas.RFC_NO_FACTURABLES` → error
  `rfc_no_facturable` en la validación (bloquea Facturar desde cualquier camino) y 422 al crear desde el Excel.
  Las facturas viejas a SAFMEX del Facturador sí pueden recibir su REP.
- "**No tiene REF / escaneo**" por destino (`viaje.sin_acuse`): no se exige acuse y en el concepto no se
  pone nada en la REF (si ningún destino tiene REF, no va el renglón). También se marca desde Facturar →
  Acuses (`PUT /viajes/{id}/sin-acuse`).
- El servicio se crea **terminado** (salida 9:00 y una hora por destino, hora de México; si es de hoy,
  termina antes de ahora) y lleva a Facturar. Una fila no se puede usar dos veces (409).
- "**Descargar con facturas**": copia del Excel con el folio de la factura vigente escrito en la columna
  FACTURA de las filas facturadas aquí. Se edita el XML de la hoja dentro del .xlsx (openpyxl perdía
  dibujos y comentarios al guardar); nunca sobrescribe una celda con dato. Al subir un Excel nuevo, la liga
  fila→servicio se reubica por huella (fecha+cliente+destino) si se insertaron filas.
- Probado en local con Postgres 16 en Docker (migración sube/baja/sube), catálogos sembrados de los YAML,
  R2 simulado en disco y Playwright a 1280 y 390 px. **No se probó en producción.**

**3 nov 2026 — Avisos de REF repetida y servicios cercanos** (errores comunes con Chemital; solo avisan,
no bloquean). Lógica en `app/modules/servicios/referencias.py`:
- **REF repetida**: la misma REF en otro servicio del mismo cliente (sin cancelados; "05151" = "5151").
  Avisa en la app del operador al escribir el folio (`GET /operador/viajes/{id}/referencia-repetida`), en
  Facturar con Excel al escribir la REF (también si se repite entre destinos de la misma fila), en Facturar
  junto a cada folio (`concepto.folios[].repetida_en`) y como warning `ref_repetida` de la validación.
- **Servicios cercanos**: en Facturar con Excel, lista de servicios del mismo cliente a ±3 días de la fecha
  (con REF, destinos y factura) — `GET /clientes/{id}/servicios-cercanos?fecha=`.

**3 nov 2026 — Facturas del Facturador Electrónico (app anterior)** (migración `0017`)
- Facturas → "Importar del Facturador": sube el reporte de emisión (`Emision_<RFC>_<desde>_<hasta>.xlsx`).
  Se importan las de tipo **Ingreso** como facturas con `origen="facturador"` y **sin servicio**
  (`factura.servicio_id` ahora es opcional; todas llevan `factura.cliente_id`). Idempotente por UUID: subir un
  reporte más nuevo actualiza estatus y lo cobrado. Las timbradas en esta app no se tocan.
- Lo cobrado sale de la columna "Estatus pago (MXN)" = monto ya pagado con REP del Facturador
  (`factura.pagado_externo`; coincide con el total en 3,064 de 3,139 vigentes). Saldo = total − pagado en el
  Facturador − aplicado en la app. Si ya tenía cobros, el siguiente REP es la parcialidad 2
  (`parcialidades_externas`) y sus impuestos se calculan proporcionales.
- Los REP del Facturador no se importan (el reporte no trae sus montos ni a qué facturas pagan).
- En la lista y el detalle llevan la etiqueta **facturadorelectronico**; su PDF/XML, correo y cancelación se
  hacen en el Facturador (aquí responden 409). Cobranza, conciliación, REP (también mezclando facturas de ambos
  sistemas en un mismo pago) y dashboard las cuentan igual que las de la app. Probado: REP mixto timbrado en
  el sandbox.
- Dashboard: todos los montos con dos decimales (pedido de Vlad para cuadrar con Facturador.com).
- Un RFC que no está en Clientes se da de alta con la razón social del reporte y **CP/régimen fiscal vacíos**;
  el REP avisa que hay que completarlos. En local se crearon 17 (SAFMEX, FORTA LAB, SUSTAINABLE…).

**11 nov 2026 — Editar servicio** (`/admin/servicios/:id/editar`, menú ⋮ del detalle → "Editar")
- Reutiliza `ServicioFormPage` en modo edición (cliente fijo). Guarda en este orden: `PATCH /servicios/{id}`
  (cabecera), `DELETE` de viajes quitados, `PATCH /viajes/{id}` solo de los campos que cambiaron
  (`cambiosDeViaje` en `api.ts`), `POST` de destinos nuevos. Un viaje guardado conserva su km al abrir (solo se
  sugiere si cambias el lugar). No aparece "Editar" con servicio cancelado o con factura vigente (`409` por API).
- Pruebas: `test_editar_servicio_completo_como_lo_hace_la_pantalla` (backend), `edicion.test.ts` (frontend) y
  recorrido con Playwright en local (SQLite + Vite): editar notas/unidad/precio/destino y agregar destino.

**11 nov 2026 — Terminar servicios en bloque** (Servicios → botón "Seleccionar")
- En la lista se marcan varios servicios (programados/en curso; "seleccionar todos los visibles") y "Terminar en
  nombre del operador (N)" llama a `POST /servicios/terminar-en-bloque {servicio_ids}`: termina todos los viajes
  pendientes de cada uno (sin acuse ni folio, quedan "acuses pendientes") y marca el servicio terminado (pasa a
  "Por facturar"). Cada servicio va aparte: uno cancelado/facturado/ya terminado falla con su motivo y los demás
  siguen. Prueba: `test_terminar_en_bloque_sin_acuse_y_con_fallos_aislados` + recorrido con Playwright.

**11 nov 2026 — Factura sin Carta Porte** (`servicio.sin_carta_porte`, migración `0019`)
- Casilla "Factura sin Carta Porte" en Facturar con Excel (oculta mercancía/kg; el servicio se crea sin mercancías) y
  interruptor del mismo nombre arriba de la pantalla Facturar (`PATCH /servicios/{id}/facturacion
  {sin_carta_porte}`; oculta la sección Mercancías). Solo aplica mientras no haya factura vigente.
- Efecto: `validar.REGLAS_SOLO_CARTA_PORTE` se omiten (mercancías, km, horas, unidad/operador completos, lugares,
  inspección…); `construir_payload_cfdi(con_carta_porte=False)` manda el CFDI de ingreso **sin `Complemento`** y no
  resuelve ubicaciones en Facturama. Sigue pidiendo subtotal, REF/acuse según el cliente, receptor completo y desglose.
  Unidad y operador siguen siendo obligatorios del servicio (el concepto lleva "UNIDAD: x TON").
- Duplicar un servicio **no** copia la casilla (queda con Carta Porte). Pruebas:
  `test_fila_sin_carta_porte_factura_sin_complemento` + recorrido con Playwright.

**11 nov 2026 — Historial de movimientos** (menú "Historial", `/admin/historial`; tabla `movimiento`, migración `0020`)
- Registra **desde el 11 nov 2026** (no hay relleno de días anteriores) lo que hace cada admin: **Facturó**
  (`POST /servicios/{id}/facturar`), **Envió factura** (una o "Enviar todas"; en modo prueba la descripción dice
  "MODO PRUEBA"), **Canceló factura** y **Canceló servicio**. Solo se anota lo que sí se hizo (errores no) y repetir
  una cancelación no duplica. Si falla el registro, la acción no se rompe (`historial.service.registrar` solo loguea).
- Cada fila: hora de México, admin, tipo, descripción con enlace a la factura/servicio. Filtros: admin, tipo, fechas;
  50 por página. `GET /historial`, `GET /historial/filtros`. `servicio_id`/`factura_id` no son FK a propósito.
- Para sumar otro tipo de movimiento: constante en `historial/models.py` (+ `ETIQUETAS`) y llamar a `registrar` en el
  router de la acción (ahí está el usuario). Los timbrados "con $0 y cancelar" cuentan como un solo "Facturó".
- Pruebas: `tests/test_historial.py`; Playwright local en escritorio y 390 px.

## 3. Pendientes conocidos

- ✅ Datos fiscales de clientes: Vlad corrigió razón social/CP de Aerzen, Lesaffre, Parautos y
  Farmabiot (11 oct 2026). Los 6 clientes (incluido AERZEN RENTAL) timbran en sandbox con CSD real.
- FARMABIOT sigue sin lugares ni mercancías en producción (se dan de alta desde la app).

- **Cancelación en el sandbox no funciona**: Facturama responde 500 ("Ups! Ocurrió un problema
  al cancelar…") con cualquier motivo/ruta. Probablemente porque el sandbox no registra en el
  SAT. Por eso "$0 y cancelar" deja la factura timbrada y avisa. Ya se puede validar en
  producción (§1.1 paso 4).
- Timbrado **real** aún no probado: producción ya está configurada, pero falta la primera factura (§1.1).
- Columnas del Excel de export que pide el contador: siguen provisionales.
- 🔐 Vlad debería rotar la API key de Resend y la contraseña de la llave del CSD (aparecieron en
  una conversación con Claude). No es urgente para el paso a producción.
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
| `FACTURAMA_USER`, `FACTURAMA_PASSWORD`, `FACTURAMA_ENV` | **Railway: `production`** (desde el 3 nov 2026), con las credenciales de la cuenta de producción. `backend/.env` local: `sandbox`. Las credenciales de un ambiente dan 401 en el otro. |
| `FACTURAMA_SERIE` | `ELG` (tiene que estar registrada en la sucursal de Facturama). El folio lo asigna Facturama; la app no lo manda. |
| `EMISOR_REGIMEN_FISCAL` | `612`. |
| `EMISOR_RFC`, `EMISOR_NOMBRE`, `EMISOR_LUGAR_EXPEDICION` | Datos del emisor (régimen 612). |
| `EMAIL_MODO_PRUEBA` | Default `true` en código. Con `true` todo correo va a `EMAIL_PRUEBA_DESTINO` (o `EMAIL_REPLY_TO`) con "[PRUEBA]". Poner `false` solo al facturar de verdad. |
| `EMAIL_PRUEBA_DESTINO` | Buzón de pruebas (opcional). |
| `EMAIL_COPIA` | CC de todo correo. Default `e_logistics@outlook.com`; vacío = sin copia. |
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

## 5.1 Entorno local (PC Linux de Vlad, la de este agente del 3 nov)

- `backend/.venv` con **Python 3.14**; `frontend/node_modules` instalado; **hay Docker** con la imagen
  `postgres:16` (también `redis:7` y `seaweedfs`, sin usar). LibreOffice instalado (útil para abrir .xlsx).
- `backend/.env` está en **sandbox** y su `DATABASE_URL` es el placeholder de Railway: para importar `app.main`
  a mano usa `DATABASE_URL=sqlite://`. Tests: `mv .env .env.aside && pytest; mv .env.aside .env` (182 verdes).
- **Las migraciones solo corren en Postgres** (usan `ARRAY`); en SQLite falla `alembic upgrade`. Receta usada:
  `docker run -d --rm --name elog-mig-test -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:16`, luego
  `DATABASE_URL=postgresql+psycopg://postgres:test@localhost:55432/postgres alembic upgrade head`,
  `python -m scripts.seed_catalogos ../.misc/catalogos-fase1.yaml ../.misc/lugares-fase1.yaml` y un admin de
  prueba creado con `hash_password`. `--rm`: al hacer `docker stop` la base se borra.
- Backend local: un script (en el scratchpad, no en el repo) que fija ese `DATABASE_URL`, vacía `R2_*` y
  `RESEND_API_KEY`, pone `EMAIL_MODO_PRUEBA=true`, `CORS_ORIGINS=http://localhost:5174`, reemplaza
  `storage.subir_archivo/leer_archivo/url_firmada/eliminar_archivo` (y `servicios.router.subir_archivo`) por
  versiones en disco con una ruta `/__r2/{key}` para servirlas, y arranca uvicorn en el 8001. Facturama queda
  en sandbox (del `.env`).
- Frontend local: `VITE_API_URL=http://localhost:8001 frontend/node_modules/.bin/vite <ruta>/frontend --port 5174`.
- Recorridos con Playwright (`require("…/frontend/node_modules/playwright")`) a 1280 y 390 px.

## 6. Trampas que ya mordieron

- **La PWA servía la versión vieja** tras cada deploy. Desde `34720e1` la app muestra
  "Hay una versión nueva — Actualizar" (`frontend/src/app/UpdatePrompt.tsx`,
  `registerType: "prompt"`). Si Vlad reporta "no cambió", primero: deploy terminado + Ctrl+Shift+R.
- El sandbox de Facturama valida estricto con CSD real: nombre del receptor = RFC, `RFCFigura`
  en l_RFC. Para pruebas usar el receptor ficticio del SAT `EKU9003173C9` / `ESCUELA KEMPER URGATE` / CP 42501.
- `.misc/` (gitignored) tiene el Excel `CartaPorte.xlsx`; no hay `.misc/PENDIENTES-VLAD.md` en esta PC.
  En la PC Linux sí hay `PENDIENTES-VLAD.md`, `DatosCartaPorte.xlsx`, `REGISTROS ELOGISTICS 2024.xlsx`
  (registro de servicios, hoja `Hoja1`), `Emision_ZACE880207MC7_….xlsx` (reporte del Facturador) y `factura.xml`.
- **openpyxl pierde dibujos, comentarios y otras partes al re-guardar un .xlsx**: por eso "Descargar con
  facturas" edita el XML de la hoja dentro del zip (`registro_excel/excel.py`). No cambiarlo a `wb.save()`.
- `npx vite` lanzado desde otra carpeta **descarga otro Vite** y sirve 404: usar el binario de
  `frontend/node_modules/.bin/vite` con la ruta del proyecto.
- `pkill -f <algo>` dentro de un comando que contiene ese mismo texto mata al propio shell (exit 144).
- **Para confirmar un deploy** sirve el MCP de Railway (`list-deployments`, solo lectura): proyecto
  `dynamic-connection` (`ab76d72f-1b02-4b11-8a40-54d7d635a996`), un deploy por servicio (backend y frontend) por commit.
- `railway domain` está bloqueado por el clasificador de permisos (puede crear un dominio). No hay URL del
  backend en el repo: pedírsela a Vlad si hace falta verificar `/health`.
- En la búsqueda de destinos, unir dos palabras ("THYSSEN"+"KRUPP") con la regla de prefijo daba falsos
  positivos ("DISTRIBUIDORA MARGA" → VASSA DIVASSA): la unión solo acepta coincidencia exacta o casi exacta.
  El script de prueba con los destinos reales del Excel está descrito en `test_registro_excel.py`.
- **URLs**: backend `https://api.elogistics.sbs` (también `elogistics-facturacion-production.up.railway.app`),
  frontend `https://elogistics.sbs` (también `fearless-energy-production-d98b.up.railway.app`).
- **"No puedo iniciar sesión / el frontend se ve sin datos" (4 nov 2026)**: no era producción (Railway
  online, sin errores). La red donde estaba Vlad (IP pública `201.168.166.154`) tiene un **FortiGate** con
  filtro web que marca `elogistics.sbs`, `api.elogistics.sbs` y el dominio `.up.railway.app` del backend como
  **"Malicious Websites"** (en HTTPS re-firma el certificado con su CA → error de TLS; en HTTP devuelve
  "¡Página web bloqueada!"). La PWA carga desde caché, pero ninguna llamada a la API llega a Railway. Cómo
  detectarlo: los logs HTTP del backend no muestran peticiones de Vlad y
  `curl http://api.elogistics.sbs/health` devuelve la página de bloqueo. Desde otra red (p.ej. datos del
  celular) funciona.

## 7. Migraciones agregadas en esta sesión

`0008` servicio.timbrado_modo · `0009` lugar.distancia_km/km_confirmado + viaje.origen_cp/destino_cp ·
`0010` carga de km por destino desde `alembic/data/km_lugares.json` · `0011` viaje.monto_desglose +
cliente.plantilla_correo (con los textos por cliente) · `0012` RFC XEXX → XAXX en lugares ·
`0013` mercancía.declarar_material_peligroso (y su copia en viaje_mercancia) · `0014`
cliente.hereda_de_id (AERZEN RENTAL → AERZEN) y nombres de clientes sin espacios sobrantes. · `0015`
viaje.reescaneo_motivo/_solicitado_at/_solicitado_por. · `0016` Facturar con Excel (registro_excel*,
viaje.sin_acuse). · `0017` factura sin servicio: cliente_id, origen, pagado_externo, parcialidades_externas. ·
`0018` foto_evidencia (fotos opcionales del servicio para el correo). · `0019` servicio.sin_carta_porte · `0020` movimiento (historial).

## 8. Cómo se probó de punta a punta sin tocar producción

Base SQLite local con los catálogos **copiados de producción por API (solo GET)**, sandbox de Facturama
(el mismo de producción), R2 simulado en disco y correo en modo prueba forzado; la UI se recorrió con
Playwright como admin (1280 px) y como operador (390 px). Así se pueden crear servicios y timbrar sin
dejar datos de prueba en la base real.

Desde el 3 nov (PC Linux) se hace igual pero con **Postgres 16 en Docker** (§5.1), que también prueba las
migraciones (subir, bajar y volver a subir `0016`/`0017`, con una factura existente para el relleno de
`cliente_id`). El REP mixto (factura del Facturador + factura de la app) se timbró de verdad en el sandbox.
