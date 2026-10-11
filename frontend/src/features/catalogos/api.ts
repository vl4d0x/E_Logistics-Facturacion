// Hooks de datos de catálogos — TanStack Query sobre `api` (`lib/api.ts`).
// Un mismo patrón para los 4 catálogos "completos" (unidad/operador/cliente + uso +
// delete inteligente + restaurar, `03-api-contract §5`); lugares y mercancías llevan
// su propio set porque su forma de listar es distinta (sin paginación / anidadas).
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import type {
  AccesoOperador,
  Cliente,
  ClientePayload,
  DeleteResultOut,
  Lugar,
  LugarPayload,
  Mercancia,
  MercanciaPayload,
  Operador,
  OperadorPayload,
  Page,
  Unidad,
  UnidadPayload,
  UsoOut,
  UsuarioAdmin,
} from "./types";

export type ActivoFiltro = "true" | "false" | "todos";

function toastError(err: unknown, fallback: string) {
  const message = err instanceof ApiError ? err.message : fallback;
  notifications.show({ color: "red", title: "No se pudo completar", message });
}

function listParams(activo: ActivoFiltro, q: string): string {
  const params = new URLSearchParams();
  if (activo !== "todos") params.set("activo", activo);
  if (q) params.set("q", q);
  params.set("size", "200");
  return params.toString();
}

/** Factory: un set de hooks CRUD + uso + delete inteligente + restaurar por catálogo. */
function makeCatalogHooks<TOut, TPayload>(basePath: string, queryKey: string) {
  function useList(activo: ActivoFiltro, q: string) {
    return useQuery({
      queryKey: [queryKey, "list", activo, q],
      queryFn: () => api.get<Page<TOut>>(`${basePath}?${listParams(activo, q)}`),
    });
  }

  function useCreate() {
    const client = useQueryClient();
    return useMutation({
      mutationFn: (payload: TPayload) => api.post<TOut>(basePath, payload),
      onSuccess: () => {
        client.invalidateQueries({ queryKey: [queryKey] });
        notifications.show({ color: "green", message: "Guardado" });
      },
      onError: (err) => toastError(err, "No se pudo crear el registro"),
    });
  }

  function useUpdate() {
    const client = useQueryClient();
    return useMutation({
      mutationFn: ({ id, payload }: { id: string; payload: Partial<TPayload> }) =>
        api.patch<TOut>(`${basePath}/${id}`, payload),
      onSuccess: () => {
        client.invalidateQueries({ queryKey: [queryKey] });
        notifications.show({ color: "green", message: "Guardado" });
      },
      onError: (err) => toastError(err, "No se pudo guardar el cambio"),
    });
  }

  function useGet(id: string | null) {
    return useQuery({
      queryKey: [queryKey, "detail", id],
      queryFn: () => api.get<TOut>(`${basePath}/${id}`),
      enabled: id !== null,
    });
  }

  function useUso(id: string | null) {
    return useQuery({
      queryKey: [queryKey, "uso", id],
      queryFn: () => api.get<UsoOut>(`${basePath}/${id}/uso`),
      enabled: id !== null,
    });
  }

  function useDelete() {
    const client = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => api.delete<DeleteResultOut>(`${basePath}/${id}`),
      onSuccess: (result) => {
        client.invalidateQueries({ queryKey: [queryKey] });
        notifications.show({
          color: "green",
          message: result.resultado === "eliminado" ? "Eliminado" : "Archivado",
        });
      },
      onError: (err) => toastError(err, "No se pudo eliminar"),
    });
  }

  function useRestore() {
    const client = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => api.post<TOut>(`${basePath}/${id}/restaurar`),
      onSuccess: () => {
        client.invalidateQueries({ queryKey: [queryKey] });
        notifications.show({ color: "green", message: "Restaurado" });
      },
      onError: (err) => toastError(err, "No se pudo restaurar"),
    });
  }

  return { useList, useGet, useCreate, useUpdate, useUso, useDelete, useRestore };
}

export const unidadesApi = makeCatalogHooks<Unidad, UnidadPayload>("/api/v1/catalogos/unidades", "unidades");
export const operadoresApi = makeCatalogHooks<Operador, OperadorPayload>(
  "/api/v1/catalogos/operadores",
  "operadores",
);
export const clientesApi = makeCatalogHooks<Cliente, ClientePayload>(
  "/api/v1/catalogos/clientes",
  "clientes",
);

// --- Mercancías (anidadas en cliente, sin paginación) ------------------------
export function useMercancias(clienteId: string | null) {
  return useQuery({
    queryKey: ["mercancias", clienteId],
    queryFn: () => api.get<Mercancia[]>(`/api/v1/catalogos/clientes/${clienteId}/mercancias`),
    enabled: clienteId !== null,
  });
}

export function useMercanciaUso(id: string | null) {
  return useQuery({
    queryKey: ["mercancias", "uso", id],
    queryFn: () => api.get<UsoOut>(`/api/v1/catalogos/mercancias/${id}/uso`),
    enabled: id !== null,
  });
}

export function useCreateMercancia(clienteId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: MercanciaPayload) =>
      api.post<Mercancia>(`/api/v1/catalogos/clientes/${clienteId}/mercancias`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["mercancias", clienteId] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo crear la mercancía"),
  });
}

export function useUpdateMercancia(clienteId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<MercanciaPayload> }) =>
      api.patch<Mercancia>(`/api/v1/catalogos/mercancias/${id}`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["mercancias", clienteId] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo guardar el cambio"),
  });
}

export function useDeleteMercancia(clienteId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<DeleteResultOut>(`/api/v1/catalogos/mercancias/${id}`),
    onSuccess: (result) => {
      client.invalidateQueries({ queryKey: ["mercancias", clienteId] });
      notifications.show({
        color: "green",
        message: result.resultado === "eliminado" ? "Eliminado" : "Archivado",
      });
    },
    onError: (err) => toastError(err, "No se pudo eliminar"),
  });
}

export function useRestoreMercancia(clienteId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Mercancia>(`/api/v1/catalogos/mercancias/${id}/restaurar`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["mercancias", clienteId] });
      notifications.show({ color: "green", message: "Restaurado" });
    },
    onError: (err) => toastError(err, "No se pudo restaurar"),
  });
}

// --- Lugares (lista global, filtrable por cliente; sin paginación) ----------
export function useLugares(clienteId: string | null, q: string, incluirGlobales = true) {
  const params = new URLSearchParams();
  if (clienteId) {
    params.set("cliente_id", clienteId);
    params.set("incluir_globales", String(incluirGlobales));
  }
  if (q) params.set("q", q);
  return useQuery({
    queryKey: ["lugares", clienteId, q, incluirGlobales],
    queryFn: () => api.get<Lugar[]>(`/api/v1/catalogos/lugares?${params.toString()}`),
  });
}

export function useLugarUso(id: string | null) {
  return useQuery({
    queryKey: ["lugares", "uso", id],
    queryFn: () => api.get<UsoOut>(`/api/v1/catalogos/lugares/${id}/uso`),
    enabled: id !== null,
  });
}

export function useCreateLugar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: LugarPayload) => api.post<Lugar>("/api/v1/catalogos/lugares", payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["lugares"] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo crear el lugar"),
  });
}

export function useUpdateLugar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<LugarPayload> }) =>
      api.patch<Lugar>(`/api/v1/catalogos/lugares/${id}`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["lugares"] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo guardar el cambio"),
  });
}

export function useDeleteLugar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<DeleteResultOut>(`/api/v1/catalogos/lugares/${id}`),
    onSuccess: (result) => {
      client.invalidateQueries({ queryKey: ["lugares"] });
      notifications.show({
        color: "green",
        message: result.resultado === "eliminado" ? "Eliminado" : "Archivado",
      });
    },
    onError: (err) => toastError(err, "No se pudo eliminar"),
  });
}

export function useRestoreLugar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Lugar>(`/api/v1/catalogos/lugares/${id}/restaurar`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["lugares"] });
      notifications.show({ color: "green", message: "Restaurado" });
    },
    onError: (err) => toastError(err, "No se pudo restaurar"),
  });
}

// --- Acceso del operador a la app -------------------------------------------
export function useAccesoOperador(operadorId: string) {
  return useQuery({
    queryKey: ["operadores", operadorId, "acceso"],
    queryFn: async () => {
      try {
        return await api.get<AccesoOperador>(`/api/v1/catalogos/operadores/${operadorId}/acceso`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useCrearAcceso(operadorId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password_temporal: string }) =>
      api.post<AccesoOperador>(`/api/v1/catalogos/operadores/${operadorId}/acceso`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["operadores", operadorId, "acceso"] });
      notifications.show({ color: "green", message: "Acceso creado" });
    },
    onError: (err) => toastError(err, "No se pudo dar de alta el acceso"),
  });
}

export function useActualizarAcceso(operadorId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email?: string; password_temporal?: string; activo?: boolean }) =>
      api.patch<AccesoOperador>(`/api/v1/catalogos/operadores/${operadorId}/acceso`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["operadores", operadorId, "acceso"] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo actualizar el acceso"),
  });
}

// --- Usuarios administradores ------------------------------------------------
export function useAdmins() {
  return useQuery({
    queryKey: ["usuarios-admin"],
    queryFn: () => api.get<UsuarioAdmin[]>("/api/v1/usuarios?rol=admin"),
  });
}

export function useCrearAdmin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: { nombre: string; email: string; password_temporal: string }) =>
      api.post<UsuarioAdmin>("/api/v1/usuarios", payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["usuarios-admin"] });
      notifications.show({ color: "green", message: "Administrador creado" });
    },
    onError: (err) => toastError(err, "No se pudo crear el administrador"),
  });
}

export function useActualizarAdmin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: { nombre?: string; email?: string; password_temporal?: string; activo?: boolean };
    }) => api.patch<UsuarioAdmin>(`/api/v1/usuarios/${id}`, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["usuarios-admin"] });
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo guardar el cambio"),
  });
}

export interface ImportarKmResultado {
  hojas: { hoja: string; cliente: string; actualizados: number; sin_km: number; sin_lugar: string[] }[];
  hojas_sin_cliente: string[];
}

/** Sube el Excel de Carta Porte para cargar el km de cada destino (`importar_km.py`). */
export function useImportarKm() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return api.post<ImportarKmResultado>("/api/v1/catalogos/lugares/importar-km", form);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["lugares"] }),
    onError: (err) => toastError(err, "No se pudo importar el Excel"),
  });
}
