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

export function getSession(): StoredSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    return null;
  }
}

export function setSession(session: StoredSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  notify();
}

export function setAccessToken(accessToken: string): void {
  const current = getSession();
  if (!current) return;
  setSession({ ...current, access_token: accessToken });
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
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
