/**
 * Cliente HTTP: adjunta `Authorization: Bearer`, maneja 401 (refresh transparente
 * o logout) y parsea el envelope de error estándar (`03-api-contract §2`).
 */
import { clearSession, getAccessToken, getRefreshToken, setAccessToken } from "./auth";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface ApiErrorDetail {
  field: string;
  issue: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: ApiErrorDetail[];

  constructor(code: string, message: string, status: number, details: ApiErrorDetail[] = []) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const data = (await res.json()) as { access_token: string };
        setAccessToken(data.access_token);
        return data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Para reintentos internos tras un refresh; no lo uses desde afuera. */
  _isRetry?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, _isRetry, headers, ...rest } = options;
  const accessToken = getAccessToken();

  const isFormData = body instanceof FormData;

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  });

  if (response.status === 401 && !_isRetry && path !== "/api/v1/auth/login") {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, { ...options, _isRetry: true });
    }
    clearSession();
    throw new ApiError("unauthorized", "Sesión expirada", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const err = data?.error ?? { code: "internal_error", message: "Error inesperado" };
    throw new ApiError(err.code, err.message, response.status, err.details ?? []);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};
