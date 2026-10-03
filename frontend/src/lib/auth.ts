/**
 * Sesión del usuario: guarda los tokens y notifica a quien esté escuchando.
 *
 * Nota de diseño: guardamos access+refresh en localStorage. Es una herramienta
 * interna de bajo volumen (ver `00-overview §1`), no un SaaS público; el trade-off
 * de XSS-vs-simplicidad se acepta para el MVP (`01-architecture §5` deja la puerta
 * abierta a httpOnly cookie si hiciera falta más adelante).
 */
export type Rol = "admin" | "operador";

export interface SessionUser {
  id: string;
  nombre: string;
  email: string;
  rol: Rol;
  operador_id: string | null;
}

interface StoredSession {
  access_token: string;
  refresh_token: string;
  user: SessionUser;
}

const STORAGE_KEY = "elogistics.session";

type Listener = () => void;
const listeners = new Set<Listener>();

function notify() {
  for (const l of listeners) l();
}

export function subscribeSession(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// `useAuth` lee `getCurrentUser` vía `useSyncExternalStore`, que exige que el
// snapshot sea referencialmente estable mientras nada cambió — si no, React entra
// en loop infinito de renders ("Maximum update depth exceeded", solo visible en un
// navegador real, no en los tests con jsdom) y la pantalla de admin queda en blanco
// apenas hay sesión. Por eso se cachea en memoria en vez de volver a `JSON.parse`
// el localStorage en cada llamada.
let cachedSession: StoredSession | null | undefined;

function readSession(): StoredSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    return null;
  }
}

export function getSession(): StoredSession | null {
  if (cachedSession === undefined) {
    cachedSession = readSession();
  }
  return cachedSession;
}

export function setSession(session: StoredSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  cachedSession = session;
  notify();
}

export function setAccessToken(accessToken: string): void {
  const current = getSession();
  if (!current) return;
  const updated = { ...current, access_token: accessToken };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  cachedSession = updated;
  notify();
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
  cachedSession = null;
  notify();
}

export function getAccessToken(): string | null {
  return getSession()?.access_token ?? null;
}

export function getRefreshToken(): string | null {
  return getSession()?.refresh_token ?? null;
}

export function getCurrentUser(): SessionUser | null {
  return getSession()?.user ?? null;
}
