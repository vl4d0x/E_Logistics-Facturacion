// Hooks de datos de servicios y viajes — TanStack Query sobre `api` (`lib/api.ts`).
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import type { Page } from "../catalogos/types";
import type {
  AcuseOut,
  Conteos,
  ServicioCreate,
  ServicioDetalle,
  ServicioListItem,
  ServicioUpdate,
  ViajeIn,
  ViajeMercanciaIn,
  ViajeOut,
  Vista,
} from "./types";

function toastError(err: unknown, fallback: string) {
  const message = err instanceof ApiError ? err.message : fallback;
  notifications.show({ color: "red", title: "No se pudo completar", message });
}

export interface FiltrosServicios {
  vista?: Vista;
  cliente_id?: string | null;
  operador_id?: string | null;
  unidad_id?: string | null;
  q?: string;
  acuses_pendientes?: boolean;
  inspeccion_fallas?: boolean;
  fecha_desde?: string;
  fecha_hasta?: string;
}

function buildParams(filtros: FiltrosServicios, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams(extra);
  if (filtros.vista) params.set("vista", filtros.vista);
  if (filtros.cliente_id) params.set("cliente_id", filtros.cliente_id);
  if (filtros.operador_id) params.set("operador_id", filtros.operador_id);
  if (filtros.unidad_id) params.set("unidad_id", filtros.unidad_id);
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.fecha_desde) params.set("fecha_desde", filtros.fecha_desde);
  if (filtros.fecha_hasta) params.set("fecha_hasta", filtros.fecha_hasta);
  if (filtros.acuses_pendientes) params.set("acuses_pendientes", "true");
  if (filtros.inspeccion_fallas) params.set("inspeccion_fallas", "true");
  return params.toString();
}

export function useServicios(filtros: FiltrosServicios) {
  return useQuery({
    queryKey: ["servicios", filtros],
    queryFn: () =>
      api.get<Page<ServicioListItem>>(`/api/v1/servicios?${buildParams(filtros, { size: "100" })}`),
  });
}

export function useConteosServicios(filtros: FiltrosServicios) {
  return useQuery({
    queryKey: ["servicios", "conteos", filtros],
    queryFn: () => api.get<Conteos>(`/api/v1/servicios/conteos?${buildParams(filtros)}`),
  });
}

export function useServicio(id: string | null) {
  return useQuery({
    queryKey: ["servicios", "detalle", id],
    queryFn: () => api.get<ServicioDetalle>(`/api/v1/servicios/${id}`),
    enabled: id !== null,
  });
}

function invalidarServicios(client: ReturnType<typeof useQueryClient>, id?: string) {
  client.invalidateQueries({ queryKey: ["servicios"] });
  if (id) client.invalidateQueries({ queryKey: ["servicios", "detalle", id] });
}

export function useCrearServicio() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ServicioCreate) =>
      api.post<ServicioDetalle>("/api/v1/servicios", payload),
    onSuccess: () => {
      invalidarServicios(client);
      notifications.show({ color: "green", message: "Servicio creado" });
    },
    onError: (err) => toastError(err, "No se pudo crear el servicio"),
  });
}

export function useEditarServicio(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ServicioUpdate) =>
      api.patch<ServicioDetalle>(`/api/v1/servicios/${id}`, payload),
    onSuccess: () => {
      invalidarServicios(client, id);
      notifications.show({ color: "green", message: "Guardado" });
    },
    onError: (err) => toastError(err, "No se pudo guardar el cambio"),
  });
}

/** Un viaje del formulario de edición: `key` es el id real si ya existía, o `nuevo-…`. */
export type ViajeEdicion = ViajeIn & { key: string };

const CAMPOS_VIAJE = [
  "tipo",
  "origen_lugar_id",
  "destino_lugar_id",
  "origen_cp",
  "destino_cp",
  "distancia_km",
  "notas_admin",
] as const;

/** Solo los campos del viaje que cambiaron respecto a como estaba guardado. */
export function cambiosDeViaje(actual: ViajeOut, nuevo: ViajeIn): Partial<ViajeIn> {
  const antes: ViajeIn = {
    tipo: actual.tipo,
    origen_lugar_id: actual.origen?.id ?? null,
    destino_lugar_id: actual.destino?.id ?? null,
    origen_cp: actual.origen_cp ?? null,
    destino_cp: actual.destino_cp ?? null,
    distancia_km: actual.distancia_km,
    notas_admin: actual.notas_admin ?? null,
  };
  const cambios: Record<string, unknown> = {};
  for (const campo of CAMPOS_VIAJE) {
    const a = antes[campo] ?? null;
    const n = (campo === "notas_admin" ? nuevo[campo] || null : nuevo[campo]) ?? null;
    if (a !== n) cambios[campo] = n;
  }
  return cambios as Partial<ViajeIn>;
}

/**
 * Guarda la edición completa: cabecera, viajes quitados, viajes modificados y viajes nuevos
 * (en ese orden, para que quitar un origen y poner otro no choque con "un solo origen").
 * Si algo falla se detiene y lo ya guardado se refleja al refrescar el detalle.
 */
export function useGuardarEdicionServicio(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({
      original,
      cabecera,
      viajes,
    }: {
      original: ServicioDetalle;
      cabecera: ServicioUpdate;
      viajes: ViajeEdicion[];
    }) => {
      const ids = new Set(viajes.map((v) => v.key));
      const quitados = original.viajes.filter((v) => !ids.has(v.id));
      const porId = new Map(original.viajes.map((v) => [v.id, v]));
      const modificados = viajes.flatMap((v) => {
        const previo = porId.get(v.key);
        if (!previo) return [];
        const cambios = cambiosDeViaje(previo, v);
        return Object.keys(cambios).length ? [{ id: v.key, cambios }] : [];
      });
      const nuevos = viajes.filter((v) => !porId.has(v.key));

      await api.patch(`/api/v1/servicios/${id}`, cabecera);
      for (const v of quitados) await api.delete<void>(`/api/v1/viajes/${v.id}`);
      for (const m of modificados) await api.patch(`/api/v1/viajes/${m.id}`, m.cambios);
      for (const { key: _key, ...payload } of nuevos) {
        await api.post(`/api/v1/servicios/${id}/viajes`, payload);
      }
    },
    onSuccess: () => notifications.show({ color: "green", message: "Servicio actualizado" }),
    onError: (err) => toastError(err, "No se pudo guardar el servicio"),
    onSettled: () => invalidarServicios(client, id),
  });
}

export function useDuplicarServicio(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (fecha: string) =>
      api.post<ServicioDetalle>(`/api/v1/servicios/${id}/duplicar`, { fecha }),
    onSuccess: () => {
      invalidarServicios(client);
      notifications.show({ color: "green", message: "Servicio duplicado" });
    },
    onError: (err) => toastError(err, "No se pudo duplicar"),
  });
}

export function useCancelarServicio(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (motivo: string) =>
      api.post<ServicioDetalle>(`/api/v1/servicios/${id}/cancelar`, { motivo }),
    onSuccess: () => {
      invalidarServicios(client, id);
      notifications.show({ color: "green", message: "Servicio cancelado" });
    },
    onError: (err) => toastError(err, "No se pudo cancelar"),
  });
}

export function useMarcarTerminado(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<ServicioDetalle>(`/api/v1/servicios/${id}/marcar-terminado`),
    onSuccess: () => {
      invalidarServicios(client, id);
      notifications.show({ color: "green", message: "Servicio marcado como terminado" });
    },
    onError: (err) => toastError(err, "No se pudo marcar como terminado"),
  });
}

// --- Viajes ------------------------------------------------------------------
export function useAgregarViaje(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ViajeIn) =>
      api.post<ViajeOut>(`/api/v1/servicios/${servicioId}/viajes`, payload),
    onSuccess: () => invalidarServicios(client, servicioId),
    onError: (err) => toastError(err, "No se pudo agregar el viaje"),
  });
}

export function useEditarViaje(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ViajeIn> }) =>
      api.patch<ViajeOut>(`/api/v1/viajes/${id}`, payload),
    onSuccess: () => invalidarServicios(client, servicioId),
    onError: (err) => toastError(err, "No se pudo guardar el viaje"),
  });
}

export function useEliminarViaje(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/v1/viajes/${id}`),
    onSuccess: () => invalidarServicios(client, servicioId),
    onError: (err) => toastError(err, "No se pudo quitar el viaje"),
  });
}

export function useTerminarViaje(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: { mercancias?: ViajeMercanciaIn[]; referencia_acuse?: string };
    }) => api.post<ViajeOut>(`/api/v1/viajes/${id}/terminar`, payload),
    onSuccess: () => {
      invalidarServicios(client, servicioId);
      notifications.show({ color: "green", message: "Viaje terminado" });
    },
    onError: (err) => toastError(err, "No se pudo terminar el viaje"),
  });
}

export function useReabrirViaje(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ViajeOut>(`/api/v1/viajes/${id}/reabrir`),
    onSuccess: () => {
      invalidarServicios(client, servicioId);
      notifications.show({ color: "green", message: "Viaje reabierto" });
    },
    onError: (err) => toastError(err, "No se pudo reabrir"),
  });
}

export function useAgregarAcuseReferencia(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, referencia }: { viajeId: string; referencia: string }) =>
      api.post<AcuseOut>(`/api/v1/viajes/${viajeId}/acuses`, { referencia }),
    onSuccess: () => {
      invalidarServicios(client, servicioId);
      notifications.show({ color: "green", message: "Folio guardado" });
    },
    onError: (err) => toastError(err, "No se pudo guardar el folio"),
  });
}

export function useAgregarAcuseArchivo(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ viajeId, file }: { viajeId: string; file: File }) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<AcuseOut>(`/api/v1/viajes/${viajeId}/acuses`, form);
    },
    onSuccess: () => {
      invalidarServicios(client, servicioId);
      notifications.show({ color: "green", message: "Acuse subido" });
    },
    onError: (err) => toastError(err, "No se pudo subir el acuse"),
  });
}

// Km sugerido para un destino: el del Excel de Carta Porte del cliente (confirmado) o 70 km
// "no confirmado". Ver `specs/IDEAS-FUTURAS.md`.
export async function fetchDistanciaSugerida(
  destinoId: string,
): Promise<{ km: number; confirmado: boolean } | null> {
  try {
    const res = await api.get<{ distancia_km: number | null; confirmado: boolean }>(
      `/api/v1/lugares/distancia-sugerida?destino_lugar_id=${destinoId}`,
    );
    return res.distancia_km == null ? null : { km: res.distancia_km, confirmado: res.confirmado };
  } catch {
    return null; // la sugerencia es solo una ayuda; nunca debe estorbar
  }
}

/** Marca la entrega para re-escaneo (el acuse falta o está mal tomado) o quita la marca. */
export function useReescaneo(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, motivo, quitar }: { viajeId: string; motivo?: string | null; quitar?: boolean }) =>
      quitar
        ? api.delete(`/api/v1/viajes/${viajeId}/reescaneo`)
        : api.post(`/api/v1/viajes/${viajeId}/reescaneo`, { motivo: motivo ?? null }),
    onSuccess: (_d, vars) => {
      invalidarServicios(client, servicioId);
      notifications.show({
        color: vars.quitar ? "gray" : "yellow",
        message: vars.quitar ? "Se quitó la solicitud de re-escaneo" : "Entrega marcada para re-escaneo",
      });
    },
    onError: (err) => toastError(err, "No se pudo actualizar el re-escaneo"),
  });
}
