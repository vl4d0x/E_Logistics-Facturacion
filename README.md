# Elogistics · Facturación CFDI + Carta Porte

Software interno para automatizar la facturación electrónica (CFDI 4.0 + Complemento Carta
Porte 3.1) de los servicios de transporte de Elogistics. Ver `specs/00-overview.md` para el
contexto completo — **léelo primero** si vas a trabajar en este repo.

## Specs

Todo el diseño (arquitectura, modelo de datos, contrato de API, mapeo fiscal, fases) vive en
`specs/`. Un agente o persona nueva debe leer `specs/00-overview.md` antes que nada.

- `specs/00-overview.md` — qué es, dominio, reglas de negocio, cuándo pedir info a Vlad.
- `specs/01-architecture.md` — decisiones técnicas ya tomadas (no reabrir).
- `specs/02-data-model.md` — tablas, enums, máquinas de estado.
- `specs/03-api-contract.md` — endpoints REST.
- `specs/04-facturacion-cfdi.md` — mapeo CFDI + Carta Porte (el spec más delicado).
- `specs/05-ui-spec.md` — fuente de verdad de UI (tema Mantine, tokens, componentes, layouts).
- `specs/fase-N-*.md` — historias de usuario por fase, en orden de construcción.

## Estructura

```
backend/    FastAPI + SQLModel + Alembic + Postgres
frontend/   React + Vite + TS + Mantine + TanStack Query + PWA (admin y operador)
docker-compose.yml   Postgres local
```

> `backend/pyproject.toml` es la fuente de verdad de dependencias (dev local: `pip install -e
> ".[dev]"`). `backend/requirements.txt` es un espejo solo para Railway/Railpack, que instala
> vía `pip install -r requirements.txt` y no lee `pyproject.toml` para esto — si agregas una
> dependencia de producción, actualiza ambos archivos.

## Desarrollo local

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # llena JWT_SECRET y, si aplica, SEED_ADMIN_*/FACTURAMA_*

docker compose -f ../docker-compose.yml up -d   # Postgres local
alembic upgrade head
python -m scripts.seed_admin                     # crea el admin (requiere SEED_ADMIN_* en .env)

uvicorn app.main:app --reload   # http://localhost:8000 — /health, /api/v1/auth/login
pytest
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev             # http://localhost:5173
npm test
npm run build            # valida también la config PWA (genera sw.js)
```

### Spike de Facturama (H0.5)

```bash
cd backend && source .venv/bin/activate
python -m scripts.spike_facturama   # requiere FACTURAMA_USER/PASSWORD en .env (sandbox)
```
Aprendizajes del mapeo real contra la API de Facturama: `backend/NOTES.md`.

## Deploy

Ver `DEPLOY.md`.

## Convenciones

Ver `specs/01-architecture.md §8`. Resumen: UTC en DB / hora México en UI, `Decimal` para dinero,
UUID como PK, código en inglés / dominio y UI en español, `/api/v1` como prefijo de API.

## 🔴 Info pendiente de Vlad

Estos bloques bloquean partes específicas (no todo el proyecto) hasta tener los datos reales.
Configúralos como variables de entorno (`backend/.env` local / Variables del servicio en Railway),
**nunca** los pegues en el chat con un agente ni los commitees.

**Ya resueltos** (Fase 0, sept 2026):
- ~~`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`~~ — admin creado y probado end-to-end en Railway.
- ~~`FACTURAMA_USER` / `FACTURAMA_PASSWORD`~~ — cuenta sandbox real, autenticación verificada.
- ~~`EMISOR_RFC` / `EMISOR_NOMBRE` / `EMISOR_LUGAR_EXPEDICION`~~ — confirmados y cargados también en
  el perfil fiscal de Facturama (`TaxEntity` + `BranchOffice` + `Serie`, ver `backend/NOTES.md`).

**Pendientes**:
- **CSD** (Certificado de Sello Digital, `.cer`+`.key`+contraseña) — sin esto el spike no puede
  timbrar de verdad (llega hasta "certificado vacío"). Se sube **directo en el panel de
  dev.facturama.mx**, nunca por chat ni al repo. Ver `backend/NOTES.md`.
- Datos reales de catálogos (unidades, operadores, clientes, mercancías) — Fase 1, el siguiente paso.
- `FormaPago` por defecto y si algún cliente usa PUE en vez de PPD (`04-facturacion-cfdi §7`).
- R2 (`R2_*`) y Resend (`RESEND_API_KEY`, `EMAIL_FROM`, plantilla de correo) — Fase 5.
- Un CFDI real (XML+PDF) de Elogistics como fixture de test — Fase 4.

Ver el detalle exacto de cada uno en el spec de su fase correspondiente.
