# Deploy a Railway (H0.4)

Este es un monorepo con **dos servicios Railway independientes** (backend y frontend), cada uno
con su `railway.json` (`backend/railway.json`, `frontend/railway.json`). El deploy real requiere
tu cuenta de Railway — estos pasos son para que tú (o quien tenga acceso) lo corra.

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
- **Root Directory**: `backend` (Settings del servicio → "Root Directory").
- Railway detecta `backend/railway.json` → build con Railpack, `preDeployCommand: alembic upgrade
  head`, `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
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
- **Root Directory**: `frontend`.
- Railway detecta `frontend/railway.json` → `npm run build`, sirve `dist/` con `serve` vía
  `npm run start`.
- Variable de entorno:
  ```
  VITE_API_URL=https://<dominio-del-backend>.up.railway.app
  ```

## 5. Verificar

- `GET https://<backend>/health` → `{"status":"ok"}`.
- Login end-to-end en `https://<frontend>` con el admin sembrado.

## Notas

- Las migraciones corren como `preDeployCommand` en cada deploy del backend — no hace falta
  correrlas a mano salvo la primera vez si el orden de creación de servicios lo requiere.
- Nunca pongas secretos en `railway.json` ni en el repo; siempre en las variables del servicio.
- Alternativa al frontend en Railway: Cloudflare Pages (`01-architecture §2`), apuntando el build
  a `frontend/`, comando `npm run build`, output `dist/`.
