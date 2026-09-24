# 01 · Architecture

> Decisiones de arquitectura ya tomadas. Un agente que implementa **no reabre estas decisiones**; las sigue. Si algo aquí choca con la realidad al codear, deténte y reporta, no improvises otra arquitectura.

## 1. Principios

- **Monolito modular**, no microservicios. Un backend, un frontend, una base de datos.
- **Rápido y funcional** sobre "escalable". Volumen bajo (ver `00-overview §1`). Nada de Redis, Celery, colas ni brokers.
- **Rebanadas verticales**: cada feature entrega DB + API + UI que funciona de punta a punta.
- **Lo fiscal pesado lo hace Facturama** (XML, sellado, timbrado, validación de catálogos SAT). Nosotros: captura, mapeo y validación de negocio.
- **Idempotencia donde el offline lo exige** (ver §6).

## 2. Stack

| Capa | Tecnología | Notas |
|------|-----------|-------|
| Backend | **Python 3.12 + FastAPI** | API REST. |
| ORM / modelos | **SQLModel** + **Alembic** | SQLModel = Pydantic + SQLAlchemy. Alembic para migraciones. |
| Base de datos | **PostgreSQL 16** | Provista por Railway. |
| Auth | **JWT** (access + refresh), `passlib[bcrypt]`, `python-jose` | Roles en columna. Sin proveedor externo. |
| Frontend | **React 18 + TypeScript + Vite** | Una sola app (admin + operador por rutas/rol). |
| UI kit | **Mantine** (o shadcn/ui) | No diseñar componentes base desde cero. Elegir uno y no mezclar. |
| Estado servidor | **TanStack Query** | Cache, reintentos, invalidación. |
| PWA / offline | **vite-plugin-pwa** (Workbox) + **IndexedDB** (`idb` o Dexie) | Solo rutas de operador. |
| Timbrado | **Facturama** (API REST) | Sandbox primero, prod por env. |
| Almacenamiento archivos | **Cloudflare R2** (S3-compatible, `boto3`) | Acuses escaneados, PDF, XML. |
| Correo | **Resend** (API) | Envío con adjuntos. |
| Hosting | **Railway** | Backend + Postgres. Frontend estático (Railway o Cloudflare Pages). |
| Tests | **pytest** (backend), **Vitest + Testing Library** (frontend) | Criterios de aceptación de cada feature-spec = casos de prueba. |

Versiones exactas se fijan en `pyproject.toml` / `package.json` en Fase 0; usa las estables al momento de crear el repo.

## 3. Estructura del repositorio (monorepo)

```
elogistics/
├── specs/                      # estos documentos
├── backend/
│   ├── app/
│   │   ├── main.py             # crea FastAPI, monta routers, CORS
│   │   ├── core/
│   │   │   ├── config.py       # Settings (pydantic-settings), lee env
│   │   │   ├── db.py           # engine, session, get_session dep
│   │   │   ├── security.py     # hash, verify, JWT encode/decode
│   │   │   └── deps.py         # get_current_user, require_role(...)
│   │   ├── modules/
│   │   │   ├── auth/           # models, schemas, router, service
│   │   │   ├── catalogos/      # unidad, operador, cliente, mercancia
│   │   │   ├── viajes/
│   │   │   ├── servicios/
│   │   │   ├── facturacion/    # integración Facturama + mapeo CFDI
│   │   │   └── entrega/        # correo, dashboard, export xlsx
│   │   └── integrations/
│   │       ├── facturama.py    # cliente HTTP de Facturama
│   │       ├── storage.py      # R2 (subir/descargar/presign)
│   │       └── email.py        # Resend
│   ├── alembic/                # migraciones
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app/                # router, layout, providers (Query, auth)
│   │   ├── lib/                # api client, auth, offline queue
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── catalogos/
│   │   │   ├── viajes/
│   │   │   ├── servicios/
│   │   │   ├── facturacion/
│   │   │   └── dashboard/
│   │   ├── components/         # UI compartida
│   │   └── routes/
│   │       ├── admin/          # panel escritorio
│   │       └── operador/       # PWA, offline
│   ├── vite.config.ts          # + vite-plugin-pwa
│   └── package.json
├── docker-compose.yml          # Postgres local para desarrollo
└── README.md
```

**Cada módulo backend** sigue el mismo patrón de 4 archivos:
- `models.py` — tablas SQLModel.
- `schemas.py` — DTOs de entrada/salida (Pydantic).
- `service.py` — lógica de negocio (funciones puras que reciben `session`).
- `router.py` — endpoints FastAPI que llaman al service.

Los routers **no** contienen lógica de negocio; delegan en `service.py`. Esto mantiene los endpoints delgados y testeables.

## 4. Frontend: una app, dos experiencias

- **Una sola SPA React**. Tras login, el rol decide el árbol de rutas:
  - `admin` → `/routes/admin/*` (dashboard, viajes, servicios, catálogos, facturas). Layout de escritorio con sidebar.
  - `operador` → `/routes/operador/*` (mis viajes, cerrar viaje). Layout móvil, instalable como PWA, offline.
- El **service worker y el offline solo importan para el operador**. El admin es online normal.
- Diseño visual: seguir el panel ya aprobado en Claude Design (rojo Elogistics `#E0353B`, tipografía limpia, minimalista). Ese diseño es la referencia de UI.

## 5. Auth

- Login con **email + contraseña**. Contraseñas con **bcrypt**.
- **JWT**: access token (~30 min) + refresh token (~30 días, para que el operador en campo no re-loguee seguido). Refresh guardado en `httpOnly` cookie o en almacenamiento seguro del cliente.
- Usuario tiene `rol ∈ {admin, operador}`. Dependencia `require_role("admin")` protege endpoints de admin.
- Usuarios se crean por seed / por un admin; **no hay auto-registro público**.

> 🔴 **INFO REQUERIDA (Vlad)** — la lista de **usuarios iniciales** para el seed: nombre, email y rol (admin/operador) de cada uno, y qué ficha de operador del catálogo corresponde a cada usuario operador.
- Todos los endpoints excepto `/auth/login` y `/health` requieren token.

## 6. Sincronización offline (operador) — decisión clave

El operador cierra viajes en campo, potencialmente sin señal. Estrategia **simple y robusta**:

1. **IDs generados en cliente**: las acciones offline usan un **UUID v4 generado en el teléfono** como clave de idempotencia (`client_action_id`). El servidor deduplica por ese id → reenviar la misma acción no la duplica.
2. **Cola de mutaciones en IndexedDB**: cuando el operador cierra un viaje sin conexión, la app guarda la mutación (payload + foto como Blob) en una cola local y marca el viaje como "pendiente de sincronizar" en la UI.
3. **Replay al reconectar**: un listener de `online` (y un intento al reabrir la app) reproduce la cola contra la API en orden. El endpoint de cierre es **idempotente** (ver `03-api-contract`): si ya se procesó ese `client_action_id`, responde 200 con el estado actual.
4. **Fotos**: se suben al reconectar. Flujo MVP: la foto viaja al backend (multipart) y el backend la guarda en R2. (Optimización futura: presigned upload directo a R2; no en MVP.)
5. **Lectura offline**: los viajes asignados se cachean (Workbox + Query persist) para que el operador los vea sin señal. La escritura es lo que se encola.

**No** construimos CRDTs ni sync bidireccional complejo. Es una cola de escritura unidireccional con idempotencia. Suficiente para el caso (un operador cierra sus propios viajes; no hay edición concurrente del mismo registro).

## 7. Variables de entorno

Backend (`.env`):
```
DATABASE_URL=postgresql+psycopg://...        # Railway lo inyecta
JWT_SECRET=...
JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=30
FACTURAMA_ENV=sandbox                          # sandbox | production
FACTURAMA_USER=...
FACTURAMA_PASSWORD=...                          # Basic Auth de Facturama
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=elogistics
RESEND_API_KEY=...
EMAIL_FROM="Elogistics <facturacion@dominio.mx>"
CORS_ORIGINS=https://app.dominio.mx,http://localhost:5173
```
Frontend (`.env`): `VITE_API_URL=...`

Nunca commitear secretos. En Railway se configuran como variables del servicio.

> 🔴 **INFO REQUERIDA (Vlad)** — los valores reales de estos secretos y config: credenciales de **Facturama sandbox** (`FACTURAMA_USER`, `FACTURAMA_PASSWORD`), bucket y llaves de **Cloudflare R2**, API key de **Resend** y el correo/dominio remitente (`EMAIL_FROM`), y el dominio de producción para `CORS_ORIGINS`. Pídelos antes de integrar; en local usa un `.env` de desarrollo con datos de prueba.

## 8. Convenciones

- **Timezone**: guardar todo en UTC en la DB; presentar en `America/Mexico_City`. Las fechas fiscales del CFDI se calculan en hora local de México (el SAT lo exige).
- **Dinero**: `Decimal` en backend (nunca float), 2 decimales, MXN. En columnas `NUMERIC(12,2)`.
- **IDs**: `UUID` como PK en todas las tablas (facilita el offline y evita filtrar volumen).
- **Nombres**: código y comentarios en inglés; UI y textos de dominio en español. Los nombres de entidades de dominio (`viaje`, `servicio`) se mantienen en español para no traducir el dominio fiscal mexicano.
- **API**: prefijo `/api/v1`. JSON. snake_case en JSON. Errores con envelope estándar (`03-api-contract §2`).
- **Commits**: convencionales (`feat:`, `fix:`…). Una rama por feature-spec.
- **Migraciones**: cada cambio de modelo genera una migración Alembic; nunca editar la DB a mano.

## 9. Deploy (Railway)

- Servicio **backend**: build con `pip install`, arranca `uvicorn app.main:app`. Corre `alembic upgrade head` en el release.
- **Postgres**: plugin de Railway; `DATABASE_URL` inyectado.
- **Frontend**: build estático (`vite build`) servido por Railway static o Cloudflare Pages. `VITE_API_URL` apunta al backend.
- **Migraciones en deploy**: `alembic upgrade head` como release command, antes de arrancar el server.
- Sandbox de Facturama en el entorno de staging/dev; producción solo cuando el flujo esté validado.

## 10. Qué NO hacer (guardarraíles para agentes)

- No agregar dependencias de infra (Redis, Kafka, Celery, Elasticsearch).
- No introducir un segundo lenguaje/servicio.
- No hardcodear catálogos del SAT (claves de producto, unidades, config vehicular): esos los valida Facturama y se guardan mapeados en nuestros catálogos de negocio.
- No inventar campos fiscales: seguir `04-facturacion-cfdi` y la doc de Facturama.
- No romper la idempotencia del cierre de viaje.
