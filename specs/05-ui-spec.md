# 05 · UI spec

> **Fuente de verdad para el código de UI.** El lienzo de Claude Design es la referencia **visual** (para humanos); este documento es lo que un agente sigue para construir. Si algo aquí choca con el lienzo, este documento manda (el lienzo puede tener aproximaciones). Objetivo: que cualquier agente construya pantallas **consistentes entre fases** — mismos colores, tipos, espaciados y componentes.
>
> **No reinventes componentes base**: usa Mantine con el tema de §4. Componín pantallas con esos componentes; no inventes tu propio sistema.

## 1. Principios

- Minimalista, limpio, denso pero respirable. Superficies planas, sin gradientes ni sombras dramáticas.
- Una acción primaria (roja) por vista; el resto son secundarias/ghost.
- El color comunica estado, pero **nunca solo**: el estado también va en texto (badge con palabra).
- El admin es de escritorio (sidebar + main); el operador es móvil, dedos, offline.

## 2. Tokens de color

> 🔴 **INFO REQUERIDA (Vlad)** — el rojo base es `#E0353B` (tomado de los mockups). Si tu logo usa otro hex, pásalo y se reemplaza aquí y en el tema de Mantine; es el único cambio para reclavar la marca.

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

**Semánticos (estado)** — cada uno con texto y fondo suave
| Estado | Texto | Fondo | Uso |
|---|---|---|---|
| success | `#1E9C63` | `#E7F4EC` | listo, validación OK, facturado |
| warning | `#C07E0A` | `#FBF0D9` | sin acuse, warnings de validación, borrador |
| info | `#2E6FD6` | `#E9F0FC` | listo para facturar, informativo |
| danger | `#E0353B` | `#FCECEC` | errores, cancelar |

Texto sobre fondo de color: usar siempre el color "texto" de su misma familia, nunca negro puro. Contraste mínimo 4.5:1 (3:1 en ≥24px).

## 3. Tipografía, spacing, radios, sombra

- **Familia**: `Plus Jakarta Sans` (Google Fonts) para todo; fallback `system-ui, sans-serif`. (Si prefieres una sola familia del sistema para acelerar, es aceptable, pero mantén una sola.)
- **Escala** (font-size / weight):
  - `display` 28 / 700 — números grandes del dashboard
  - `h1` 22 / 700 · `h2` 18 / 600 · `h3` 16 / 600
  - `body` 14 / 400 (base) · `sm` 13 / 400 · `xs` 12 / 500 (etiquetas, uppercase)
  - Enfatiza con peso o color, no con tamaños nuevos.
- **Spacing** (px): 4, 8, 12, 16, 20, 24, 32. Padding de tarjeta: 16–20. Gap de grid: 12–16.
- **Radios**: control/input/botón `10px`; tarjeta `14px`; pill `20–40px`.
- **Sombra**: casi nada. Tarjetas usan borde 1px `--el-line`, no sombra. Solo el marco tipo navegador o menús flotantes llevan sombra suave (`0 20px 40px rgba(20,20,20,.08)`).
- **Iconos**: una sola librería (Tabler icons, que Mantine ya integra). Tamaño 16–20px inline, 24px máx.

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
  // superficies/neutros van como CSS vars (§2), porque los grises de Mantine no matchean los tonos cálidos
});
```
Además, declara las CSS custom properties de §2 en `:root` (un `theme.css`) y úsalas para fondos, bordes y texto. Mantine primary = rojo de marca; superficies/líneas/texto = las `--el-*`. Colores semánticos: define `green`/`yellow`/`blue` de Mantine cercanos o usa las `--el-*` semánticas directamente en badges.

> Si el equipo eligiera shadcn/ui en vez de Mantine, mapea estos mismos tokens a las CSS vars de shadcn (`--primary`, `--background`, `--border`, etc.). El set de tokens no cambia.

## 5. Inventario de componentes

Construir estos como wrappers finos sobre Mantine, reutilizados en todas las fases:

- **Button**: `primary` (relleno rojo, 1 por vista), `secondary` (outline `--el-line`), `ghost` (texto), `danger` (rojo, para cancelar). Alto 36–46px, radio 10, peso 600.
- **IconButton**: 38px cuadrado, outline, para acciones sueltas (campana, menú de fila).
- **Card**: fondo `--el-surface`, borde 1px `--el-line`, radio 14, padding 16–20.
- **MetricCard**: etiqueta 13 muted arriba, número `display` abajo, delta opcional (badge success/warning). Para el dashboard.
- **DataTable / RowList**: filas con borde inferior `--el-line-2`, no tarjetas separadas. Soporta **encabezado de grupo por fecha** (fila `--el-surface-2`, texto xs uppercase muted). Menú `...` por fila.
- **FormField**: label 13/600 muted + control + help/`error` (13, `--el-red`) debajo. Inputs 44px alto en móvil, 40 en escritorio.
- **Select / Combobox**: para catálogos (unidad por apodo, cliente, operador, mercancía). Buscable.
- **SegmentedControl**: para el tipo de viaje (recolección / entrega / ambas).
- **StatusBadge**: pill con texto + color. Mapea:
  - servicio: `borrador`→warning, `listo`→info, `facturado`→success, `cancelado`→neutral gris.
  - acuse en viaje: escaneo→ícono clip success; referencia→folio faint; ninguno→sin marca.
- **Sidebar** (admin): logo (cuadro rojo "E" + "Elogistics"), items con ícono + label, item activo con fondo `--el-red-tint` y texto `--el-red-hover`, chip de usuario abajo.
- **Topbar** (admin): título + subtítulo a la izquierda, acciones a la derecha (primario "Registrar viaje").
- **Timeline** (ruta del servicio): nodo origen relleno rojo, destinos con anillo; label + subtexto por nodo.
- **ValidationItem**: ícono check (success) / triángulo (warning) / círculo x (danger) + texto. Para el panel pre-timbrado.
- **EmptyState**, **Toast/Notification**, **ConfirmDialog** (para acciones destructivas: desagrupar, cancelar factura), **FileDrop/CameraCapture** (operador).
- **OfflineBanner / PendingBadge** (operador): indica sin conexión y "N por sincronizar".

## 6. Patrones (estados que los agentes suelen olvidar)

- **Carga**: skeletons en tablas/tarjetas, no spinners a pantalla completa. Botones muestran estado loading al enviar.
- **Vacío**: título + una línea + acción. Ej. "Sin viajes sin agrupar" + "Registra un viaje". Nunca una pantalla en blanco.
- **Error**: mensaje en español, qué pasó + qué hacer, con botón de reintento. Errores de formulario junto al campo (`422` del backend → mapear `details[].field`).
- **Confirmación**: acciones irreversibles o fiscales (desagrupar, **cancelar factura**, desactivar catálogo) piden confirmación con `ConfirmDialog`.
- **Éxito**: toast breve ("Factura timbrada", "Viaje cerrado"); no bloquear con modales de éxito.
- **Dinero**: siempre `$1,848.00` con separador de miles y 2 decimales.
- **Fechas**: `11 ago 2026` en UI; horas en 24h locales.

## 7. Layout admin y pantallas

**Estructura**: `Sidebar` (224px fijo) + `Main` (Topbar 74px + contenido con scroll). Contenido en `--el-bg`, tarjetas en `--el-surface`.

- **Dashboard** (`/admin`): sección "Ingresos" (3 MetricCards: mes / trimestre / año + MetricCard con mini-gráfica de ingresos por mes) → sección "Pendientes" (4 tiles: sin agrupar, listos, sin acuse, por cobrar PPD) → lista "Servicios listos para facturar" con botón Facturar por fila.
- **Registrar viaje** (`/admin/viajes/nuevo`): dos columnas. Izquierda: formulario (SegmentedControl tipo; Select cliente/unidad-por-apodo/operador; fecha; origen/destino según tipo; subtotal opcional con borde punteado). Derecha: panel "Se llenará solo en la Carta Porte" (chips read-only: placa, config, permiso, licencia, póliza) + nota de que la mercancía la captura el operador. Acciones abajo: Cancelar (secondary) / Registrar (primary).
- **Agrupar y facturar** (`/admin/servicios/nuevo`): dos columnas. Izquierda: viajes sin agrupar **agrupados por fecha**, seleccionables (check). Derecha: servicio en construcción — Timeline de ruta, campo subtotal, panel de validación (ValidationItems), desglose subtotal/IVA/retención/total, botón "Generar factura" (primary, deshabilitado si hay errores de validación).
- **Servicios** (`/admin/servicios`): buscador + filtros (cliente, fecha, estado) + tabs de estado con conteos; DataTable **agrupada por fecha** con columnas cliente/ruta/viajes/total/estado + menú `...`; paginación.
- **Detalle de factura** (`/admin/facturas/:id`): datos del CFDI (UUID, folio, montos), enlaces a PDF/XML/acuse, acciones Enviar por correo y Cancelar (danger, con ConfirmDialog + motivo).
- **Catálogos** (`/admin/catalogos`): 4 sub-vistas (unidades, operadores, clientes, mercancías) con DataTable + formulario en modal/drawer.

## 8. Layout operador (PWA, móvil, offline)

- **Mis viajes** (`/operador`): lista vertical de cards de viaje asignado; cada card: cliente, unidad (apodo), origen/destino, y qué exige el cierre. Badge "pendiente de sincronizar" si aplica. `OfflineBanner` arriba cuando no hay señal.
- **Cerrar viaje** (`/operador/viajes/:id/cerrar`): botón grande "Servicio terminado"; según cliente/tipo: selector de mercancía(s) + kg, y **CameraCapture** (modo escaneo) / campo referencia (modo referencia) / nada (modo ninguno). Campos opcionales hora/notas. Botón de confirmar ancho, tap target ≥44px.
- **Responsive**: diseñar a 390×844 (móvil) primero. Tap targets ≥44px. Inputs 44px+. Sin sidebar; navegación simple (header + back). Nada de tablas densas: cards apiladas.
- **Offline UX**: al cerrar sin señal, feedback inmediato ("Guardado, se enviará al reconectar") y el viaje muestra estado pendiente hasta que sincroniza.

## 9. Accesibilidad y misc

- Usar `<button>`, `<a>`, `<label>+<input>` reales; nada de `onClick` en divs.
- `aria-label` en botones de solo ícono.
- Contraste según §2. No depender solo del color para estado.
- Foco visible en todos los controles.
- Textos de UI en español, sentence case (no Title Case, no MAYÚSCULAS salvo etiquetas xs).

## 10. Definición de terminado (para el agente de UI de cada fase)
- [ ] Usa el tema de Mantine de §4 y las CSS vars de §2 (sin hex sueltos en componentes).
- [ ] Reutiliza el inventario de §5; no crea componentes base nuevos.
- [ ] Toda pantalla tiene estados de carga, vacío y error (§6).
- [ ] Layout coincide con §7/§8 y con el lienzo aprobado.
- [ ] Operador cumple tap targets y offline UX.
- [ ] Accesibilidad de §9.
