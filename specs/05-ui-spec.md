# 05 · UI spec (v2)

> **Fuente de verdad para el código de UI.** El lienzo de Claude Design es referencia visual para humanos; si algo choca, este documento manda. Objetivo: pantallas **consistentes entre fases**.
> **No reinventes componentes base**: Mantine con el tema de §4; compón pantallas con el inventario de §5.
> **v2**: nuevas pantallas (Nuevo servicio con viajes, Facturar, Cobranza, flujo del operador con inspección/cierre/gasolina, dashboard tipo referencia) y nuevos componentes (PriceField, AcuseViewer, FuelGauge, ReconciliationPanel, gráficas).
> **v2.1**: el campo de precio es el **subtotal sugerido, listo para modificar, con la suma que lo explica** y el total calculado debajo; casilla de **timbrado anticipado**; dos badges por servicio (operación y facturación); la conciliación muestra los servicios; **sin** tarjetas de combustible en el dashboard; aviso de costos pendientes (SetupReminder).

## 1. Principios

- Minimalista, limpio, denso pero respirable. Superficies planas.
- Una acción primaria (roja) por vista.
- El color comunica estado, pero **nunca solo**: siempre con texto.
- Admin: escritorio (≥1280 px ideal, usable desde 1024). Operador: móvil, dedos, offline.
- **Lo que más se edita va primero y más grande** (el precio en Facturar, el monto en Registrar pago).

## 2. Tokens de color

> 🔴 **INFO REQUERIDA (Vlad)** — el rojo base es `#E0353B`. Si el logo usa otro hex, se reemplaza aquí y en el tema.

**Marca / acento**
| Token | Hex | Uso |
|---|---|---|
| `--el-red` | `#E0353B` | acción primaria, acento, nav activa |
| `--el-red-hover` | `#B4272C` | hover/active de primario |
| `--el-red-tint` | `#FCECEC` | fondos suaves, nav activa, chips |

**Neutros / superficies** (tonos cálidos, NO grises puros de Mantine)
| Token | Hex | Uso |
|---|---|---|
| `--el-bg` | `#F5F5F2` | fondo de página |
| `--el-surface` | `#FFFFFF` | tarjetas, paneles, inputs |
| `--el-surface-2` | `#FAFAF8` | zonas sutiles (encabezados de grupo) |
| `--el-line` | `#E7E7E2` | bordes 1px |
| `--el-line-2` | `#EFEFEB` | divisores internos |
| `--el-ink` | `#181A1D` | texto primario |
| `--el-muted` | `#696D75` | texto secundario |
| `--el-faint` | `#9B9EA5` | texto terciario/placeholder |

**Semánticos**
| Estado | Texto | Fondo | Uso |
|---|---|---|---|
| success | `#1E9C63` | `#E7F4EC` | facturado, pagada, validación OK |
| warning | `#C07E0A` | `#FBF0D9` | por facturar, sin acuse, en espera, parcial, REP por vencer |
| info | `#2E6FD6` | `#E9F0FC` | en curso, cobrado (gráficas), informativo |
| danger | `#E0353B` | `#FCECEC` | errores, por cobrar (gráficas), vencido, cancelar |

**Gráficas** (mismo significado que el dashboard de referencia)
| Token | Hex | Serie |
|---|---|---|
| `--el-chart-cobrado` | `#2E6FD6` | Cobrado |
| `--el-chart-por-cobrar` | `#E0353B` | Por cobrar |
| `--el-chart-track` | `#EFEFEB` | fondo de donas / meses sin datos |

Texto sobre fondo de color: el color "texto" de su familia. Contraste ≥ 4.5:1 (3:1 en ≥ 24 px).

## 3. Tipografía, spacing, radios, sombra

- **Familia**: `Plus Jakarta Sans`; fallback `system-ui, sans-serif`. Números en tablas y montos con `font-variant-numeric: tabular-nums`.
- **Escala**: `display` 28/700 · `h1` 22/700 · `h2` 18/600 · `h3` 16/600 · `body` 14/400 · `sm` 13/400 · `xs` 12/500 uppercase (etiquetas y títulos de tarjeta del dashboard). Excepción: `price` 36/700 solo para el PriceField hero.
- **Spacing**: 4, 8, 12, 16, 20, 24, 32. Padding de tarjeta 16–20. Gap 12–16.
- **Radios**: control 10 · tarjeta 14 · pill 20–40.
- **Sombra**: casi nada; bordes 1px `--el-line`. Solo menús/drawers flotantes llevan `0 20px 40px rgba(20,20,20,.08)`.
- **Iconos**: Tabler, 16–20 px inline, 24 máx.

## 4. Tema de Mantine (copiar tal cual)

```ts
// theme.ts
import { createTheme, MantineColorsTuple } from '@mantine/core';

const red: MantineColorsTuple = [
  '#FDECEC', '#FAD4D5', '#F3A9AB', '#EC7E81', '#E75A5E',
  '#E44145', '#E0353B', '#B4272C', '#8E1E22', '#6B1518',
]; // primaryShade 6 = #E0353B

export const theme = createTheme({
  primaryColor: 'brandRed',
  primaryShade: 6,
  colors: { brandRed: red },
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  headings: { fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", fontWeight: '600' },
  defaultRadius: 10,
});
```
Las `--el-*` de §2 van en `theme.css` (`:root`) y se usan para fondos, bordes, texto y series de gráficas. Gráficas con **@mantine/charts** (`DonutChart`, `BarChart type="stacked"`), coloreadas con las variables de §2. Fechas con **@mantine/dates**.

## 5. Inventario de componentes

Wrappers finos sobre Mantine, reutilizados en todas las fases.

**Base (v1)**
- **Button**: `primary` (1 por vista), `secondary` (outline), `ghost`, `danger`. Alto 36–46, peso 600.
- **IconButton**: 38 px, outline, `aria-label` obligatorio.
- **Card**: `--el-surface`, borde 1px, radio 14, padding 16–20.
- **MetricCard**: etiqueta 13 muted + número `display` + delta opcional.
- **DataTable / RowList**: filas con divisor `--el-line-2`; **encabezado de grupo por fecha** (`--el-surface-2`, xs uppercase); menú `…` por fila; selección con checkbox opcional; columnas numéricas alineadas a la derecha.
- **FormField**: label 13/600 muted + control + ayuda/error (13, `--el-red`). Inputs 40 px escritorio, 44+ móvil.
- **Select / Combobox** buscables para catálogos.
- **SegmentedControl**: tipo de viaje, tipo de medidor, Sí/No.
- **StatusBadge** (pill texto + color):
  - servicio, operación (`estado`): "Programado" (neutral) · "En curso" (info) · "Terminado" (neutral) · "Cancelado" (neutral).
  - servicio, facturación (segundo badge, junto al de operación): "**Por facturar**" (warning) cuando ya se puede timbrar y no se ha hecho (terminado, o con timbrado anticipado) · "Facturado" (success) · sin badge mientras no toca. Los servicios con la casilla llevan además la etiqueta "Anticipada" (info).
  - factura: `timbrada` (success) · `cancelacion_pendiente` "**En espera**" (warning) · `cancelada` (neutral) · `error` (danger).
  - cobro: `pendiente` "Por cobrar" (danger) · `parcial` "Parcial" (warning) · `pagada` "Pagada" (success).
  - REP: "REP pendiente" (warning) · "REP vencido" (danger) · "REP emitido" (success).
- **Sidebar**, **Topbar**, **Timeline**, **ValidationItem**, **EmptyState**, **Toast**, **ConfirmDialog**, **FileDrop/CameraCapture**, **OfflineBanner/PendingBadge** (como v1).

**Nuevos en v2**
- **SmartDeleteDialog**: antes de "Eliminar" consulta `/uso`. Si no tiene referencias: "Se eliminará definitivamente". Si tiene: "Tiene 12 servicios y 9 facturas; se **archivará** (podrás restaurarlo)". Si hay servicios activos: lista con enlaces y botón deshabilitado.
- **LugarSelect**: combobox de lugares del cliente + globales (muestra nombre y CP); opción final "+ Nuevo lugar" abre un drawer con el formulario de lugar y regresa con el lugar seleccionado.
- **ViajeRow / ServiceBuilder**: lista ordenable (drag handle + flechas para accesibilidad) de viajes: número, SegmentedControl de tipo compacto, LugarSelect origen/destino según tipo, distancia km (con hint "última vez: 80 km"), notas, eliminar. Botones "+ Recolección" y "+ Entrega". Con **timbrado anticipado** activo, cada fila muestra además la **hora programada** (salida en orígenes, llegada en destinos) y, en las entregas, un bloque de **mercancías** (selector por nombre + cantidad + kg), marcados como "necesario para timbrar".
- **PriceField**: dos variantes. El campo **siempre es el subtotal**.
  - `hero` (Facturar): etiqueta "Subtotal", input `price` 36/700 con prefijo `$`. Llega **con el subtotal sugerido ya escrito y seleccionado** (o con el subtotal guardado, si el servicio ya tiene uno): teclear lo reemplaza. Autofocus; Enter guarda y lleva el foco al botón primario. Justo debajo, **SuggestionBreakdown** (por qué ese subtotal) y, debajo, **MoneyBreakdown** (el total se calcula solo). Enlace discreto "Capturar el total con IVA" para cuando el precio se pactó con impuestos (`04 §3.1`).
  - `compact` (Nuevo servicio): input normal con la sugerencia y su desglose en un popover; obligatorio si se marca el timbrado anticipado.
- **SuggestionBreakdown**: muestra la sugerencia como una **suma**: una línea por concepto del `desglose` (`07 §4.1`) con su monto a la derecha y, al pie, "= Subtotal sugerido **$1,650.00**" con su confianza (alta success, media info, baja neutral). Debajo, chips con los últimos precios de esa ruta (clic = usar ese precio). Si el admin ya cambió el subtotal, queda como referencia con el botón "Usar sugerido". Sin sugerencia: texto faint "Sin referencias para esta ruta". Si faltan costos por capturar, incluye el **SetupReminder**.
- **SetupReminder**: aviso ámbar, no bloqueante: "Aún no capturas tus costos y tarifas; la sugerencia solo usa el historial" + botón "Configurar" (→ Configuración → Precios y tarifas) + "No volver a mostrar". Visible mientras `GET /configuracion/pendientes` reporte faltantes (`07 §5`): en SuggestionBreakdown, en la cabecera de Configuración → Precios y tarifas y sobre los pendientes del dashboard.
- **MoneyBreakdown**: Subtotal / IVA 16% / Retención 4% (o "No aplica — persona física") / **Total**; números tabulares a la derecha; se recalcula al teclear (cálculo local idéntico al backend, `lib/money.ts`).
- **AcuseViewer**: pestañas por entrega ("Entrega 1 · Guadalupe Limón"); imagen con zoom (rueda/pinch), rotar 90°, abrir en pestaña nueva; PDF embebido; varias páginas con miniaturas. Modo referencia: folio grande editable. Sin acuse requerido: FileDrop "Sube el acuse" (admin). Sin acuse por modo `ninguno`: "Este cliente no requiere acuse". En timbrado anticipado, antes de que exista: "El acuse se agregará cuando termine el servicio".
- **ChecklistToggle**: fila con etiqueta + dos botones grandes **Sí / No** (≥ 44 px, ninguno preseleccionado). "No" pinta la fila en warning.
- **FuelGauge**: medidor de gasolina, modo `input` y `readonly`, según `unidad.tipo_medidor`:
  - `aguja`: semicírculo SVG de 180° con marcas en octavos (E, ¼, ½, ¾, F rotuladas), aguja. Entrada: tocar el arco (se ajusta al octavo más cercano), arrastrar la aguja, **o** botones `−` / `+` a los lados (un octavo por toque). Texto debajo: "½ tanque". Valor: `octavos` 0–8.
  - `barras`: N barras en fila (`unidad.num_barras`), como en el tablero. Tocar la barra k llena 1..k; botón "Vacío" para 0. Texto: "5 de 8 barras". Valor: `barras` 0–N.
  - Accesibilidad: `role="slider"` con `aria-valuemin/max/now/text` y flechas del teclado.
  - Emite `lectura_medidor` (`02 §3.11`); el nivel 0–1 lo calcula el backend.
- **OdometerInput**: numérico entero con teclado numérico (`inputmode="numeric"`), separador de miles al mostrar.
- **FuelLoadForm**: lista de cargas; cada carga con Litros, Precio por litro e Importe — **con dos cualquiera se calcula el tercero** (el campo calculado se marca "calculado"); si se capturan los tres y no cuadran (> $1.00) se avisa. Foto del ticket opcional (CameraCapture). "+ Agregar otra carga". Pie: total de litros y **total $**.
- **OperatorReportCard** (admin, solo lectura): inspección (8 ítems con ✓/✕, observaciones, FuelGauge readonly, odómetro, hora), cierre (km por viaje con total, odómetro y diferencia vs suma de km, FuelGauge readonly), cargas (tabla + miniaturas de ticket + total).
- **PaymentMeter**: barra fija al pie de Cobranza: "Pago $45,320.00 · Seleccionado $45,320.00 · Diferencia **$0.00** ✓". Diferencia ≠ 0 en warning con texto de qué falta o qué sobra.
- **ReconciliationSuggestions**: tarjetas de candidatos (`06 §3.7`): etiqueta (Exacta / Aproximada / FIFO parcial), explicación y la **lista de servicios que cubre** —una línea por factura: folio · servicio # · fecha · ruta · monto, con enlace al servicio— para corroborar antes de aplicar; botón "Usar". Banner ámbar si `ambigua`.
- **AgingBadge**: días desde emisión vs `dias_credito`: "Al corriente" (neutral), "Vence pronto" (warning, ≤ 5 días), "Vencida · 12 días" (danger).
- **DueBadge**: vencimiento del REP ("Vence 5 oct", warning ≤ 3 días, danger vencido).
- **Dashboard**: `DashCard` (título xs uppercase + `RefreshStamp` arriba a la derecha), `PeriodDonut`, `MonthlyStackedBars`, `TopBalanceList`, `CountTile`, `RefreshStamp` ("Actualizado a las 10:04" + ícono de refrescar). Detalle en §7.6.

## 6. Patrones (estados que se suelen olvidar)

- **Carga**: skeletons, no spinners a pantalla completa. Botones con estado loading.
- **Vacío**: título + una línea + acción ("Sin servicios por facturar" + "Ver servicios en curso").
- **Error**: en español, qué pasó + qué hacer + reintento. `422` → error junto al campo (`details[].field`). `409` con `reason` → mensaje específico (p. ej. "Este servicio ya está facturado").
- **Confirmación**: irreversibles o fiscales (timbrar, cancelar factura/REP, emitir REP, revertir un pago, eliminar/archivar, cancelar servicio) → `ConfirmDialog` que **repite los datos clave** (receptor y total al timbrar; cliente, monto y facturas al emitir REP).
- **Éxito**: toast breve; nunca modales de éxito.
- **Dinero**: `$1,848.00`. **Fechas**: `11 ago 2026`; horas 24 h locales.
- **Guardado**: formularios de sección con "Guardar/Cancelar"; el PriceField hero guarda al perder foco o con Enter (indicador sutil "Guardado"); si el admin no toca el sugerido, se guarda al timbrar o al "Guardar y salir".
- **Deep links**: los filtros de listados viven en la URL (`?tab=&cliente=&mes=`) para que el dashboard pueda enlazar y el admin pueda compartir/volver.

## 7. Admin — layout y pantallas

**Estructura**: Sidebar 224 px + Main (Topbar 74 px + contenido con scroll en `--el-bg`).
**Navegación**: Dashboard · Servicios · Facturas · Cobranza · Catálogos (Unidades, Operadores, Clientes, Lugares) · Configuración (Precios y tarifas, Usuarios).

### 7.1 Servicios
- **Lista** (`/admin/servicios`): buscador (número, cliente, lugar) + filtros (cliente, operador, unidad, fechas) + **tabs con conteo**: Todos · Programados · En curso · **Por facturar** · Facturados · Cancelados (las `vista` de `03 §6`; un servicio timbrado por anticipado puede aparecer a la vez en "En curso" y en "Facturados"). DataTable **agrupada por fecha**: #, cliente, ruta (origen → destinos), unidad · operador, viajes (2/3), acuses (1/2 con warning si faltan), total, estado (badge de operación + badge de facturación), menú `…` (Ver, Duplicar, Facturar, Cancelar). Primario: "Nuevo servicio". En la tab "Por facturar", cada fila tiene botón "Facturar".
- **Nuevo / editar servicio** (`/admin/servicios/nuevo`, `/admin/servicios/:id/editar`): dos columnas.
  - Izquierda: tarjeta "Datos del servicio" (Cliente, Fecha, **Unidad de registro** por apodo — con la ayuda "Si participan varias camionetas, elige la que quedará en el registro y en la factura" y aviso si ya tiene otro servicio ese día —, Operador, Notas para el operador). Tarjeta "Viajes" con **ServiceBuilder**; al elegir cliente se precarga "1 recolección en su origen predeterminado + 1 entrega vacía".
  - Derecha (sticky): Timeline de la ruta; "Se llenará solo en la Carta Porte" (chips de placa, config, permiso, póliza, licencia); "Qué se le pedirá al operador" (inspección, acuse según el cliente: escaneo / folio / nada); PriceField `compact` (opcional).
  - **Casilla "Timbrar antes del servicio"** (debajo del precio, **apagada por defecto**), con la ayuda "Para clientes que piden la Carta Porte antes del traslado". Al marcarla: el subtotal pasa a ser obligatorio; el ServiceBuilder muestra horas programadas y mercancías por entrega; aparece la nota "Si después cambia el precio, la ruta o la mercancía habrá que cancelar la factura".
  - Acciones: Cancelar / **Crear servicio**. Con la casilla marcada, el primario dice **"Crear y revisar para timbrar"** y lleva a la pantalla Facturar (§7.2) del servicio recién creado.
  - En edición, los viajes terminados muestran candado (reabrir desde el detalle). Con factura vigente, los datos fiscales aparecen en solo lectura con el motivo ("Facturado: cancela la factura para cambiarlo").
- **Detalle** (`/admin/servicios/:id`): encabezado (#, cliente, fecha, unidad, operador, badges) + **dos carriles de progreso**: Operación (Programado → En curso → Terminado) y Cobro (Por facturar → Facturado → Pagado). Secciones: Viajes (tarjeta por viaje con estado, mercancías, acuse: ver / subir / capturar folio, "Terminar en nombre del operador", "Reabrir"); **OperatorReportCard**; Factura vigente (UUID, estado, cobro, **Descargar PDF**, **Descargar XML**, Enviar). Acciones según `acciones_permitidas`: Editar, Duplicar, Marcar terminado, **Facturar** (primario cuando está por facturar), Cancelar servicio (danger).

### 7.2 Facturar (`/admin/servicios/:id/facturar`) — pantalla clave
Objetivo: revisar todo precargado, **ajustar el subtotal en segundos** y timbrar con confianza. Es la misma pantalla para el flujo normal y para el timbrado anticipado.

```
┌─ Facturar servicio #128 · Chemital  [Por facturar] ────────────────────────────────────────────────────────┐
│ IZQUIERDA (≈60%)                                         │ DERECHA sticky (≈40%)                           │
│ ┌ Subtotal ──────────────────────────────────────────┐   │ ┌ AcuseViewer ───────────────────────────────┐  │
│ │ $ 1,650.00      ← sugerido, ya seleccionado        │   │ │ [Entrega 1 · G. Limón] [Entrega 2 · …]     │  │
│ │ Por qué este subtotal                              │   │ │ (imagen con zoom / folio / subir)          │  │
│ │   Tarifa base                              $600.00 │   │ └────────────────────────────────────────────┘  │
│ │   80 km × $12.50                         $1,000.00 │   │ ┌ Resumen ───────────────────────────────────┐  │
│ │   Redondeo a $50                            $50.00 │   │ │ Total  $1,848.00                           │  │
│ │   = Subtotal sugerido · baja             $1,650.00 │   │ │ Validación: ✓ 11 · ⚠ 2 · ✕ 0  (expandir)   │  │
│ │ Últimos precios de esta ruta: aún no hay           │   │ │ [ Timbrar factura · $1,848.00 ]  (primario)│  │
│ │ ────────────────────────────────────────────────── │   │ │ Guardar y salir (secundario)               │  │
│ │ IVA 16%                                    $264.00 │   │ └────────────────────────────────────────────┘  │
│ │ Retención IVA 4%                           −$66.00 │   │                                                 │
│ │ Total (se calcula solo)                  $1,848.00 │   │                                                 │
│ └────────────────────────────────────────────────────┘   │                                                 │
│ ▸ Receptor y pago      CHEMITAL… · G03 · PPD · 99  ✎     │                                                 │
│ ▸ Concepto             FLETE UNIDAD SAVEIRO…  ✎ ↺        │                                                 │
│ ▸ Ruta y ubicaciones   Origen + 2 destinos · 160 km ✎    │                                                 │
│ ▸ Mercancías           3 partidas · 60 kg  ✎             │                                                 │
│ ▸ Unidad y operador    Saveiro Roja · Juan P. ✎          │                                                 │
└──────────────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```
- **Subtotal primero**: el campo tiene el foco al abrir y trae el **subtotal sugerido ya escrito y seleccionado** (o el guardado, si el servicio ya tiene precio): teclear lo reemplaza. Debajo va **la suma que explica el sugerido** (SuggestionBreakdown) y, debajo, IVA, retención y **total, que se recalculan con cada tecla**. El admin nunca calcula el total a mano.
- **Secciones colapsadas en modo lectura**: una línea con el resumen y lo importante; ✎ abre la edición de esa sección en el mismo lugar. Una sección con error de validación se abre sola y se resalta; clic en un check de validación lleva a su sección (`campo`).
  - Receptor y pago: datos fiscales del cliente (solo lectura + "Editar cliente" en drawer, afecta el catálogo); Uso CFDI, método y forma de pago editables para esta factura.
  - Concepto: textarea con la descripción; "Regenerar" vuelve a la autogenerada.
  - Ruta y ubicaciones: tabla por ubicación (tipo, lugar, CP, fecha/hora con su fuente real o programada, distancia para Carta Porte). Si el operador reportó otros km, chip "Operador: 95 km · usar".
  - Mercancías: filas editables (descripción, cantidad, kg); claves SAT visibles en gris; agregar/quitar.
  - Unidad y operador: chips de datos de Carta Porte de la unidad de registro; "Cambiar unidad/operador" (select) y "Editar en catálogo" (drawer).
- **Modo anticipado** (servicio con la casilla y aún no terminado): banner info arriba "Timbrado anticipado: se usan las fechas programadas y no se pide acuse"; "Ruta y ubicaciones" edita las horas programadas; "Mercancías" es obligatoria; en lugar del acuse, "El acuse se agregará cuando termine el servicio"; el badge del Topbar dice "Anticipada".
- **Timbrar**: deshabilitado si hay errores (tooltip con el primero). Al hacer clic: `ConfirmDialog` "Vas a timbrar una factura a **CHEMITAL DE MEXICO SA DE CV** por **$1,848.00** (PPD). Para corregirla después habrá que cancelarla ante el SAT." → envía `total_esperado`. En modo anticipado el diálogo añade: "El servicio aún no se realiza: si cambia el precio, la ruta o la mercancía habrá que cancelar esta factura."
- **Después de timbrar**: la tarjeta Resumen se convierte en "Factura timbrada": UUID (copiable), **Descargar PDF**, **Descargar XML** y primario **"Enviar a facturacion@cliente.com"** (destinatarios editables) → toast "Factura enviada".

### 7.3 Facturas
- **Lista** (`/admin/facturas`): filtros estado fiscal, estado de cobro, cliente, mes; columnas folio, cliente, servicio #, fecha, total, saldo, estado fiscal, cobro.
- **Detalle** (`/admin/facturas/:id`): datos del CFDI, **Descargar PDF** / **Descargar XML**, acuses, envío (estado, reenviar), cobro (aplicaciones y REP relacionados con enlaces), cancelación. "Cancelar factura" (danger) → diálogo con motivo (02/03/04) y explicación de la aceptación del receptor. Si está **En espera**: banner "Esperando aceptación del receptor desde 30 sep" + "Actualizar estatus". Si tiene REP vigente: el botón explica la secuencia (cancelar REP → revertir pago → cancelar factura) con enlaces.

### 7.4 Cobranza (`/admin/cobranza`) — generar REP rápido
Tabs: **Por cobrar** · **Pagadas** · **Pagos y REP**. Filtros en la URL (`?tab=&cliente=&mes=`).

**Por cobrar**:
```
┌ Clientes ───────────┐ ┌ Facturas por cobrar · Chemital ───────────────────────────┐ ┌ Registrar pago ────────────┐
│ Todos     $519,986  │ │ ☐ Folio  Emitida   Servicio      Total     Saldo   Edad   │ │ Monto  $ [ 45,320.00 ]     │
│ ▸Chemital $120,480  │ │ ☑ A-120  04 ago   #101 …        18,480.00 18,480  ⚠ 58d  │ │ Fecha  [30 sep 2026]       │
│  Parautos $115,292  │ │ ☑ A-121  08 ago   #104 …        13,420.00 13,420  ⚠ 54d  │ │ Forma  [03 Transferencia]  │
│  …                  │ │ ☑ A-124  15 ago   #109 …        13,420.00 13,420  ⚠ 47d  │ │ Ref.   [ ……… ]             │
│                     │ │ ☐ A-130  02 sep   #115 …         9,240.00  9,240     28d  │ │ Comprobante (opcional)     │
│                     │ │ …                                                         │ │ ── Sugerencias ──          │
│                     │ │                                                           │ │ ✓ Exacta · 3 más antiguas  │
│                     │ │                                                           │ │   A-120 · #101 · 04 ago    │
│                     │ │                                                           │ │   A-121 · #104 · 08 ago    │
│                     │ │                                                           │ │   A-124 · #109 · 15 ago    │
│                     │ │                                                           │ │                     [Usar] │
└─────────────────────┘ └───────────────────────────────────────────────────────────┘ └────────────────────────────┘
 PaymentMeter: Pago $45,320.00 · Seleccionado $45,320.00 · Diferencia $0.00 ✓      [Aplicar y generar REP]  (Solo aplicar)
```
- Lista de clientes ordenada por saldo (con "Todos"); al elegir uno, su tabla de facturas abiertas con AgingBadge.
- Panel "Registrar pago" fijo a la derecha (no modal: la tabla sigue visible y clicable). El **monto tiene el foco**; al teclearlo (debounce 300 ms) aparecen las sugerencias (`06 §3.7`); "Usar" marca las facturas en la tabla. Cada sugerencia —y siempre la **coincidencia exacta**— lista **los servicios que cubre** (folio, servicio #, fecha, ruta y monto) para corroborar antes de aplicar; clic en un servicio abre su detalle en otra pestaña. El admin puede marcar/desmarcar a mano; el PaymentMeter se actualiza en vivo.
- Si lo seleccionado excede el pago: el PaymentMeter ofrece "Aplicar $X como pago parcial a A-124" (elige cuál con un select).
- Primario **"Aplicar y generar REP"** (habilitado con diferencia $0.00) → ConfirmDialog con cliente, monto, facturas (con su servicio) y parcialidades → timbra → panel de éxito: UUID del REP, PDF/XML, "Enviar al cliente". Secundario "Solo aplicar" (REP después, antes del día 5).
- Atajo de teclado: `/` enfoca el monto; `Enter` en una sugerencia la usa.

**Pagadas**: facturas con `estado_cobro = pagada` (filtrable por mes y cliente) con enlace al REP.
**Pagos y REP**: pagos con cliente, fecha, monto, facturas, REP (DueBadge si pendiente), acciones (emitir REP, enviar, cancelar REP, revertir). Encabezado: "N REP por emitir · vence el 5 oct".

### 7.5 Catálogos y configuración
- **Catálogos** (`/admin/catalogos/:tipo`): DataTable + formulario en drawer. Filtro "Activos / Archivados". Menú por fila: Editar, Eliminar (SmartDeleteDialog), Restaurar (si archivado).
  - Unidades: incluye "Medidor de gasolina" (SegmentedControl aguja/barras + número de barras con **vista previa del FuelGauge**), capacidad del tanque, capacidad de carga; aviso fijo junto a "Peso bruto vehicular": "en **toneladas**".
  - Operadores: ficha + sección "Acceso a la app" (sin acceso → "Dar acceso" con usuario y contraseña temporal; con acceso → "Restablecer contraseña", "Desactivar acceso").
  - Clientes: ficha con tabs "Datos fiscales", "Mercancías", "Lugares", "Tarifas" (Fase 4).
  - Lugares: lista global con filtro por cliente; el formulario marca "Origen predeterminado del cliente".
- **Configuración**: "Precios y tarifas" (tarifa base, costo por km, redondeo y tarifas pactadas por cliente/destino; **SetupReminder** en la cabecera mientras falten; el "cargo por parada extra" aparece deshabilitado con la nota "Pendiente de definir", `07 §2.1`) y "Usuarios" (admins: alta, restablecer contraseña, desactivar).

### 7.6 Dashboard (`/admin`)
Réplica funcional de la parte de **ingresos** del dashboard de referencia (estructura y comportamiento), con el tema claro de §2. Cada tarjeta: título xs uppercase + `RefreshStamp`. **No hay tarjetas de egresos ni de combustible** (decisión de Vlad).

**Fila 0 · Pendientes** (4 `CountTile` clicables; si faltan costos por capturar, el SetupReminder va encima): Por facturar (con "N anticipadas" si las hay) → `/admin/servicios?vista=por_facturar` · Acuses faltantes → `/admin/servicios?acuses_pendientes=true` · REP por emitir (con "vence 5 oct") → `/admin/cobranza?tab=pagos&rep_pendiente=true` · Inspecciones con fallas → `/admin/servicios?inspeccion_fallas=true`.

**Fila 1 · Ingresos** (4 tarjetas, como la referencia):
1. **Ingresos por periodo** — `PeriodDonut`: dona grande del mes seleccionado (Cobrado azul / Por cobrar rojo, centro con el total facturado en pill oscura), etiqueta del mes debajo ("Oct 2026"), dos donas chicas a la derecha con los dos meses anteriores (clic en una la vuelve el mes seleccionado). Leyenda abajo con montos: ■ Cobrado $… · ■ Por cobrar $….
2. **Ingresos por mes** — `MonthlyStackedBars`: 12 meses del año (selector `‹ 2026 ›`), barra apilada Cobrado (azul) + Por cobrar (rojo) = Facturado. Pie con totales del año: Facturado · Cobrado · Por cobrar.
3. **Por cobrar** (en la referencia "Top por cobrar") — `TopBalanceList`: año arriba, top 5 clientes con saldo (número, nombre truncado, monto). Botón **"Ver todos (N clientes)"** que expande la tarjeta en su lugar (o abre un drawer si no cabe) con **todos** los clientes con saldo, ordenados, con scroll y total al pie; "Ver menos" la contrae. Selector de año con opción "Todos los años".
4. **En espera** — `CountTile` grande: número de cancelaciones esperando aceptación del receptor + "Solicitudes de cancelación".

**Interacción (mapa de clics)** — todo cursor pointer + tooltip con lo que abrirá ("Ver 12 facturas por cobrar de sep 2026 →"):
| Clic en | Abre |
|---|---|
| Segmento **Cobrado** (dona o barra, mes M) | `/admin/cobranza?tab=pagadas&mes=M` |
| Segmento **Por cobrar** (dona o barra, mes M) | `/admin/cobranza?tab=por_cobrar&mes=M` |
| Centro de la dona / barra completa | `/admin/facturas?mes_emision=M` |
| Cliente en Por cobrar | `/admin/cobranza?tab=por_cobrar&cliente=ID` |
| En espera | Drawer "Solicitudes en espera": facturas y REP en `cancelacion_pendiente`, con fecha de solicitud y enlace a su detalle |

Accesibilidad: los segmentos de gráfica no son enfocables con teclado, así que **las leyendas y totales son botones** que hacen lo mismo.

## 8. Operador — PWA (móvil, offline)

Diseño a 390×844 primero. Tap targets ≥ 44 px. Sin sidebar: header con título + back. Cards apiladas. `OfflineBanner` arriba cuando no hay señal; `PendingBadge` "N por sincronizar".

- **Mis servicios** (`/operador`): secciones "Hoy", "Próximos", "Terminados (7 días)". Card: #, cliente, unidad (apodo), ruta corta, estado ("Por iniciar", "En curso · viaje 2 de 3", "Terminado") y badge "pendiente de sincronizar" si aplica.
- **Servicio** (`/operador/servicios/:id`): stepper fijo arriba **1 Inspección → 2 Viajes → 3 Cierre**; cada paso solo se habilita cuando el anterior está hecho.
  1. **Inspección de salida**: 8 `ChecklistToggle` (Unidad limpia · Certificado de fumigación vigente · Botiquín en unidad · Casco y chaleco en unidad · Nivel de aceite óptimo · Nivel de anticongelante óptimo · Neumáticos en buen estado · Carga de extintor óptima) — sin respuesta por defecto; **Gasolina al salir** (`FuelGauge` de su unidad); Odómetro (opcional); Observaciones (opcional; si hubo algún "No", el placeholder invita a describirlo). Primario ancho **"Iniciar servicio"** (habilitado con los 8 respondidos y el medidor puesto).
  2. **Viajes**: lista en orden; el siguiente pendiente resaltado con su lugar, dirección/referencia y notas del admin. Botón "Terminar viaje" → pantalla **Terminar viaje** (`/operador/viajes/:id/terminar`): mercancías (selector por nombre + cantidad + kg, precargado con el peso sugerido) si es entrega — si el admin ya las capturó llegan precargadas, y si el servicio ya está facturado (timbrado anticipado) se muestran en **solo lectura**; acuse según el cliente — **escaneo**: CameraCapture (varias páginas), **referencia**: campo de folio grande, **ninguno**: nada; hora de llegada (precargada con la actual) y notas. Primario **"Viaje terminado"**.
  3. **Cierre del servicio**: **Km por viaje** (una fila por viaje: "Viaje 1 · Recolección · Planta Chemital [ __ ] km") con total; Odómetro al llegar (opcional; si hay ambos odómetros muestra "Recorrido según odómetro: 92 km"); **Gasolina al llegar** (`FuelGauge`); "¿Cargaste gasolina en este servicio?" Sí/No → `FuelLoadForm`; Observaciones. Primario **"Terminar servicio"**.
- **Offline UX**: cada envío da feedback inmediato ("Guardado, se enviará al reconectar") y avanza el flujo; si una acción encolada falla por una regla de negocio, aparece arriba un aviso rojo con el detalle y qué hacer ("El admin quitó este viaje. Avísale.").

## 9. Accesibilidad y misc

- Elementos reales (`<button>`, `<a>`, `<label>+<input>`); nada de `onClick` en `div`.
- `aria-label` en botones de solo ícono; FuelGauge como slider accesible.
- Contraste según §2; estado nunca solo por color.
- Foco visible; orden de foco lógico (en Facturar: precio → secciones → timbrar).
- Textos en español, sentence case (mayúsculas solo en etiquetas xs y títulos de tarjeta del dashboard).

## 10. Definición de terminado (UI de cada fase)
- [ ] Usa el tema de §4 y las variables de §2 (sin hex sueltos en componentes).
- [ ] Reutiliza el inventario de §5; un componente nuevo entra primero al inventario.
- [ ] Carga, vacío y error en toda pantalla (§6).
- [ ] Layout según §7/§8; filtros en la URL.
- [ ] Operador: tap targets, offline UX, FuelGauge en ambos modos.
- [ ] Accesibilidad de §9.
