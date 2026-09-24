# Fase 0 · Andamiaje

> **Objetivo**: dejar el esqueleto corriendo y desplegado en Railway, con login funcionando, para que las fases siguientes solo agreguen features. Más un spike que valida el mapeo de Facturama temprano.
> **Depende de**: nada (es la primera).
> **Entrega**: app desplegada en Railway con `/health` OK y login (admin) funcionando; script de spike que timbra un CFDI en el sandbox de Facturama.
> **Lee antes**: `01-architecture` (completo), `03-api-contract §3-4`.

## Historias de usuario

### H0.1 — Esqueleto backend
Como desarrollador, quiero un backend FastAPI con Postgres y migraciones, para construir módulos encima.
**Criterios de aceptación**
- Dado el repo con la estructura de `01-architecture §3`, cuando corro el backend local (con `docker-compose up` para Postgres), entonces `GET /health` responde `200 {status:"ok"}`.
- Alembic está configurado; `alembic upgrade head` crea el esquema vacío inicial.
- `core/config.py` lee todas las env vars de `01-architecture §7` vía pydantic-settings; falla al arrancar si falta una obligatoria.
- `core/db.py` expone `get_session` como dependencia de FastAPI.

### H0.2 — Auth funcional
Como usuario, quiero iniciar sesión con email y contraseña, para acceder según mi rol.
**Criterios de aceptación**
- Existe tabla `usuario` (`02-data-model §3.1`) y un comando/seed que crea un admin inicial (datos del bloque INFO REQUERIDA).
- `POST /auth/login` con credenciales válidas devuelve `access_token`, `refresh_token` y `user`; con inválidas, `401` con envelope de error.
- `POST /auth/refresh` renueva el access token.
- `GET /auth/me` devuelve el usuario autenticado; sin token válido, `401`.
- Contraseñas guardadas con bcrypt; nunca en texto plano; nunca en logs.
- `require_role("admin")` rechaza con `403` a un operador.

### H0.3 — Esqueleto frontend + shell PWA
Como usuario, quiero una app web que me deje iniciar sesión y me lleve a la vista de mi rol.
**Criterios de aceptación**
- App React+Vite+TS con Mantine (o shadcn) y TanStack Query configurados.
- Pantalla de login que consume `/auth/login` y guarda la sesión; logout la limpia.
- Tras login, `rol=admin` entra al layout de escritorio (sidebar); `rol=operador` al layout móvil. Rutas protegidas redirigen a login sin sesión.
- `vite-plugin-pwa` configurado: la app es instalable y carga un shell básico offline (sin features aún).
- El cliente de API adjunta `Authorization: Bearer` y maneja `401` (refresh o logout).

### H0.4 — Deploy a Railway
Como equipo, queremos la app desplegada, para probar cada fase en un entorno real.
**Criterios de aceptación**
- Backend desplegado en Railway con Postgres del plugin; `alembic upgrade head` corre en el release.
- Frontend desplegado (Railway static o Cloudflare Pages) apuntando al backend vía `VITE_API_URL`.
- `GET /health` responde en la URL pública; login funciona end-to-end en el entorno desplegado.
- Variables de entorno configuradas como secretos del servicio, no en el repo.

### H0.5 — Spike de Facturama (de-risk)
Como desarrollador, quiero validar el mapeo CFDI+Carta Porte contra el sandbox de Facturama antes de construir la Fase 4.
**Criterios de aceptación**
- Un script aislado (`backend/scripts/spike_facturama.py`) arma un CFDI 4.0 tipo Ingreso + Carta Porte 3.1 con datos **inventados pero válidos** y lo timbra en el sandbox de Facturama.
- El script imprime el UUID timbrado o el error del PAC de forma legible.
- Los nombres de campos JSON se toman de la doc vigente de Facturama (ver regla de oro en `04 §intro`), no inventados.
- El aprendizaje (estructura real del payload de Facturama) se anota en `04-facturacion-cfdi` o en un `NOTES.md` para la Fase 4.

## INFO REQUERIDA (Vlad)
> 🔴 Usuario(s) admin inicial(es) para el seed (email + contraseña temporal). Credenciales del **sandbox de Facturama** para el spike (H0.5).

## Casos borde
- Arranque sin env var obligatoria → error claro, no arranque silencioso.
- Token expirado → refresh transparente; refresh inválido → logout.
- Primer deploy sin datos → login del admin seed debe funcionar igual.

## Definición de terminado
- [ ] `/health` y login funcionan en local y en Railway.
- [ ] Migraciones aplican limpio desde cero.
- [ ] PWA instalable con shell offline.
- [ ] Spike timbra (o falla con mensaje claro) en sandbox.
- [ ] Tests: login OK/KO, protección por rol, refresh.
