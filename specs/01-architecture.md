# 01 · Architecture (v2)

> Decisiones de arquitectura ya tomadas. Un agente que implementa **no reabre estas decisiones**; las sigue. Si algo choca con la realidad al codear, detente y reporta; no improvises otra arquitectura.
> v2 no cambia el stack de v1: agrega módulos (operación en campo, precios, cobranza/REP, dashboard) y amplía el offline del operador.
> v2.1 no cambia la arquitectura: el timbrado anticipado vive en `facturacion/` como un segundo modo de validación (`04 §5`), y el estado del servicio se separa en operativo y de facturación (`02 §4`).

## 1. Principios

- **Monolito modular**: un backend, un frontend, una base de datos.
- **Rápido y funcional** sobre "escalable" (volumen en `00 §1`). Nada de Redis, Celery, colas ni brokers.
- **Rebanadas verticales**: cada feature entrega DB + API + UI de punta a punta.
- **Lo fiscal pesado lo hace Facturama** (XML, sellado, timbrado, validación de catálogos SAT, cancelación). Nosotros: captura, mapeo, validación de negocio, conciliación.
- **Idempotencia donde el offline lo exige** (§6) y donde un doble clic sería caro (timbrar, emitir REP).
- **Sin trabajos en segundo plano**: lo que dependa de un estado externo (p. ej. estatus de una cancelación) se consulta **bajo demanda** (§7).

## 2. Stack

| Capa | Tecnología | Notas |
|------|-----------|-------|
| Backend | **Python 3.12 + FastAPI** | API REST. |
| ORM / modelos | **SQLModel** + **Alembic** | Migración por cada cambio de modelo. |
| Base de datos | **PostgreSQL 16** | Railway. |
| Auth | **JWT** (access + refresh), `passlib[bcrypt]`, `python-jose` | Roles en columna. |
| Frontend | **React 18 + TypeScript + Vite** | Una SPA (admin + operador por rol). |
| UI kit | **Mantine** + **@mantine/charts** (Recharts) + **@mantine/dates** + Tabler icons | No mezclar con otro kit. |
| Estado servidor | **TanStack Query** | Cache, reintentos, invalidación; `persistQueryClient` para offline del operador. |
| PWA / offline | **vite-plugin-pwa** (Workbox) + **IndexedDB** (`idb` o Dexie) | Solo rutas de operador. |
| Timbrado | **Facturama** (API REST) | CFDI I (ingreso + Carta Porte), CFDI P (REP), cancelación y consulta de estatus. Sandbox primero. |
| Archivos | **Cloudflare R2** (`boto3`) | Acuses, tickets de gasolina, comprobantes bancarios, PDF/XML. |
| Correo | **Resend** | Factura y REP con adjuntos. |
| Excel | **openpyxl** | Export. |
| Hosting | **Railway** | Backend + Postgres; frontend estático (Railway o Cloudflare Pages). |
| Tests | **pytest**, **Vitest + Testing Library** | Criterios de aceptación = casos de prueba. |

## 3. Estructura del repositorio

```
elogistics/
├── specs/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # config, db, security, deps (Fase 0)
│   │   ├── modules/
│   │   │   ├── auth/             # Fase 0
│   │   │   ├── catalogos/        # unidad, operador (+acceso), cliente, mercancía, lugar, usuarios admin
│   │   │   ├── servicios/        # servicio, viaje, viaje_mercancia, acuse (lado admin)
│   │   │   ├── operacion/        # endpoints del operador: inspección, terminar viaje, cierre, cargas
│   │   │   ├── precios/          # sugeridor, tarifas pactadas, configuración de precios
│   │   │   ├── facturacion/      # borrador de factura, validación, CFDI ingreso, envío, cancelación
│   │   │   ├── cobranza/         # pagos, conciliación (algoritmo), aplicaciones, REP
│   │   │   └── dashboard/        # agregados y export xlsx
│   │   └── integrations/
│   │       ├── facturama.py
│   │       ├── storage.py
│   │       └── email.py
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                  # router, layouts, providers
│   │   ├── lib/                  # api client, auth, offline queue, money/tax utils
│   │   ├── features/
│   │   │   ├── auth/ catalogos/ servicios/ operacion/ facturacion/ cobranza/ dashboard/
│   │   ├── components/           # inventario de 05-ui-spec §5
│   │   └── routes/
│   │       ├── admin/
│   │       └── operador/
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml
└── README.md
```

**Cada módulo backend** sigue el patrón: `models.py` (tablas) · `schemas.py` (DTOs) · `service.py` (lógica, funciones que reciben `session`) · `router.py` (endpoints delgados). Lógica pura y crítica en archivos propios y testeables sin DB ni red:
- `facturacion/taxes.py` — `calcular_impuestos`, `subtotal_desde_total`.
- `facturacion/payload.py` — servicio → payload Facturama.
- `cobranza/conciliacion.py` — algoritmo de `06 §3`.
- `cobranza/rep_payload.py` — pago → payload REP.
- `precios/sugeridor.py` — reglas de `07`.

## 4. Frontend: una app, dos experiencias

- Tras login, el rol decide el árbol de rutas: `admin` → `/admin/*` (escritorio con sidebar; **tablet y teléfono con menú en cajón**, `05 §3.1`); `operador` → `/operador/*` (móvil, PWA, offline).
- El service worker y el offline solo aplican al operador. El admin es online.
- Diseño: `05-ui-spec` es la fuente de verdad. **Todo el frontend es responsivo** (desktop, tablet y teléfono): los estilos y patrones compartidos viven en `frontend/src/app/responsive.css`.

## 5. Auth

- Login con **email + contraseña** (bcrypt). Para operadores sin correo, el admin puede asignar un identificador tipo usuario en el mismo campo de login (no se valida formato de correo para `rol=operador`).
- **JWT**: access ~30 min, refresh ~30 días.
- `require_role("admin")` protege lo administrativo; el operador solo accede a `/operador/*` y únicamente a **sus** servicios.
- **No hay auto-registro**: el admin crea accesos desde la UI (Fase 1). El seed solo crea el primer admin.

## 6. Offline del operador (decisión clave, ampliada en v2)

Estrategia simple: **cola de escritura unidireccional con idempotencia**.

1. **Acciones offline** (todas idempotentes por `client_action_id`, UUID v4 generado en el teléfono):
   - `iniciar` servicio (inspección de salida),
   - `terminar` viaje (mercancías, folio, hora),
   - `acuse` (foto, multipart),
   - `cerrar` servicio (km por viaje, nivel de gasolina, odómetro, cargas),
   - `ticket` de carga de gasolina (foto, multipart).
   Las cargas de combustible llevan **id generado en el teléfono** para que el ticket se pueda subir después referenciándolas.
2. **Cola en IndexedDB**: payload + archivos como Blob. La UI marca "pendiente de sincronizar".
3. **Replay FIFO** al evento `online` y al abrir la app. Errores de red → reintentar con backoff. Errores de negocio (`4xx` distinto de 408/429) → la cola **se detiene en esa acción** y la UI se la muestra al operador ("No se pudo enviar: el admin quitó este viaje"); las siguientes esperan.
4. **El servidor deduplica**: si el `client_action_id` ya se procesó, responde `200` con el estado actual.
5. **Lectura offline**: `GET /operador/servicios` devuelve todo lo necesario para trabajar sin red (viajes, lugares, mercancías del cliente, modo de acuse, tipo de medidor de la unidad) y se persiste con `persistQueryClient` + Workbox.
6. **Fotos**: compresión en cliente (lado mayor ≤ 2000 px, JPEG ~0.8), multipart al backend → R2. Sin presigned upload en MVP.

No hay CRDTs ni sync bidireccional: un operador escribe sobre su propio servicio; el admin puede editar el servicio, y los conflictos se resuelven con el error de negocio del punto 3.

## 7. Estados externos sin workers

- **Cancelaciones en espera** (aceptación del receptor) y **REP en cancelación**: el backend consulta a Facturama el estatus **cuando alguien mira** (detalle de factura, lista "en espera", widget del dashboard) y con un botón "Actualizar", con *throttle* de 5 min por documento.
- Cada respuesta de dashboard lleva `actualizado_at` (la UI muestra "Actualizado a las 10:04" + botón de refrescar, como el dashboard de referencia).
- Si más adelante se necesita, un Railway Cron puede llamar `POST /internal/sync` con un secreto. No en MVP.

## 8. Variables de entorno

Backend (`.env`):
```
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=...
JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=30
FACTURAMA_ENV=sandbox                 # sandbox | production
FACTURAMA_USER=...
FACTURAMA_PASSWORD=...
EMISOR_RFC=...                        # datos del emisor como config (04 §1)
EMISOR_NOMBRE=...
EMISOR_REGIMEN=612
EMISOR_CP=...
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=elogistics
RESEND_API_KEY=...
EMAIL_FROM="Elogistics <facturacion@dominio.mx>"
CORS_ORIGINS=https://app.dominio.mx,http://localhost:5173
```
Frontend: `VITE_API_URL=...`

Parámetros de negocio que el admin ajusta (precios, tolerancias) **no** van en env: viven en la tabla `configuracion` (`02 §3.19`) editable desde la UI.

> 🔴 **INFO REQUERIDA (Vlad)** — valores reales de los secretos: Facturama sandbox, R2, Resend + remitente verificado, dominio de producción para CORS, y datos del emisor (`04 §1`).

## 9. Convenciones

- **Timezone**: UTC en DB; presentar en `America/Mexico_City`. Fechas fiscales y agrupaciones por mes del dashboard en hora local de México.
- **Dinero**: `Decimal` (nunca float), 2 decimales, `ROUND_HALF_UP`, `NUMERIC(12,2)`. En JSON, string (`"1650.00"`). En el algoritmo de conciliación, **centavos enteros**.
- **IDs**: UUID. Los servicios además tienen `numero` secuencial legible (`#128`).
- **Nombres**: código en inglés; dominio en español (`servicio`, `viaje`, `lugar`).
- **API**: `/api/v1`, JSON snake_case, envelope de error (`03 §2`).
- **Commits** convencionales; una rama por fase/historia.
- **Migraciones**: Alembic siempre; nunca editar la DB a mano.

## 10. Deploy (Railway)

Sin cambios respecto a Fase 0: backend con `alembic upgrade head` como release command, Postgres del plugin, frontend estático con `VITE_API_URL`. Sandbox de Facturama en dev/staging; producción cuando el flujo esté validado.

## 11. Qué NO hacer (guardarraíles)

- No agregar infraestructura (Redis, Kafka, Celery, Elasticsearch) ni otro lenguaje/servicio.
- No hardcodear catálogos del SAT (claves de producto, unidades, config vehicular, CP, municipios): se guardan en nuestros catálogos de negocio y Facturama los valida.
- No inventar campos fiscales: seguir `04`, `06` y la doc vigente de Facturama.
- No romper la idempotencia de las acciones del operador ni del timbrado/REP.
- No usar `float` para dinero ni para la conciliación.
- No crear pantallas solo para escritorio: toda UI nueva cumple `05 §3.1` (390/820/1280 px, sin scroll horizontal de la página).
