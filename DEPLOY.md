# Deploy a Railway (H0.4)

Este es un monorepo con **dos servicios Railway independientes** (backend y frontend). El deploy
real requiere tu cuenta de Railway — estos pasos son para que tú (o quien tenga acceso) lo corra.

> ⚠️ **Gotcha real que ya nos pasó**: el **Root Directory** de un servicio **no** hace que Railway
> busque su `railway.json` dentro de esa carpeta — por defecto sigue buscándolo en la raíz del repo,
> y si no lo encuentra ahí, Railpack analiza la raíz completa (ve `backend/`, `frontend/`, `specs/`
> como carpetas sueltas) y falla con `Railpack could not determine how to build the app`. Además,
> Railway va a **deprecar Config-as-code (`railway.json`) el 2026-12-01**. Por eso, en vez de
> depender de `backend/railway.json`/`frontend/railway.json` (se dejan en el repo solo como
> referencia/backup), **configura Build/Start/Pre-Deploy directo en los campos del dashboard** —
> ver pasos 3 y 4.

## 1. Crear el proyecto

```bash
npm install -g @railway/cli   # o: brew install railway
railway login                  # abre el navegador
railway init                   # crea el proyecto Railway
```

## 2. Servicio Postgres

En el dashboard de Railway: **New → Database → PostgreSQL**. Railway inyecta `DATABASE_URL`
automáticamente a los servicios del mismo proyecto que la referencien.

## 3. Servicio backend

- **New → GitHub Repo** (o `railway up` desde `backend/`).
- **Settings → Source → Root Directory**: `backend`. Guarda.
- **Settings → Build/Deploy** (los nombres de sección varían un poco según la versión del
  dashboard, pero los campos son estos):
  - **Build Command**: vacío (Railpack detecta Python solo al ver `backend/pyproject.toml`).
  - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - **Pre-Deploy Command**: `alembic upgrade head`
- Variables de entorno del servicio (Settings → Variables) — ver `01-architecture §7`:
  ```
  DATABASE_URL=${{Postgres.DATABASE_URL}}   # referencia al plugin de Postgres
  JWT_SECRET=<genera uno fuerte>
  JWT_ACCESS_MINUTES=30
  JWT_REFRESH_DAYS=30
  FACTURAMA_ENV=sandbox
  FACTURAMA_USER=...
  FACTURAMA_PASSWORD=...
  CORS_ORIGINS=https://<dominio-del-frontend>
  SEED_ADMIN_NOMBRE=...
  SEED_ADMIN_EMAIL=...
  SEED_ADMIN_PASSWORD=...
  # R2 / Resend / Emisor: cuando toquen sus fases (ver README §Info pendiente)
  ```
- Tras el primer deploy, corre el seed del admin una vez:
  ```bash
  railway run --service backend python -m scripts.seed_admin
  ```

## 4. Servicio frontend

- **New → GitHub Repo** apuntando al mismo repo.
- **Settings → Source → Root Directory**: `frontend`. Guarda.
- **Settings → Build/Deploy**:
  - **Build Command**: `npm run build`
  - **Start Command**: `npm run start` (sirve `dist/` con `serve`, ver `frontend/package.json`)
- Variable de entorno:
  ```
  VITE_API_URL=https://<dominio-del-backend>.up.railway.app
  ```

## 5. Verificar

- `GET https://<backend>/health` → `{"status":"ok"}`.
- Login end-to-end en `https://<frontend>` con el admin sembrado.

## Notas

- Las migraciones corren como Pre-Deploy Command en cada deploy del backend — no hace falta
  correrlas a mano salvo la primera vez si el orden de creación de servicios lo requiere.
- Nunca pongas secretos en `railway.json` ni en el repo; siempre en las variables del servicio.
- Alternativa al frontend en Railway: Cloudflare Pages (`01-architecture §2`), apuntando el build
  a `frontend/`, comando `npm run build`, output `dist/`.

## Troubleshooting

**`Railpack could not determine how to build the app` y el log muestra `backend/`, `frontend/`,
`specs/` como carpetas sueltas en `./`** → el servicio está construyendo desde la raíz del repo,
no desde su Root Directory. Causa: el campo Root Directory no se guardó, o se guardó después de
disparar el deploy. Fix: confirma Root Directory en Settings → Source, y que Build/Start/Pre-Deploy
Command estén puestos directo en el dashboard (no dependas de `railway.json`, ver el aviso al
inicio de este documento) → Redeploy.
