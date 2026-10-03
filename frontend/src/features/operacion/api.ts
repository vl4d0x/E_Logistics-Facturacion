// Hooks de datos de operación en campo — TanStack Query sobre `api`.
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import type { ServicioDetalle } from "../servicios/types";
import type { CerrarServicioPayload, IniciarServicioPayload, TerminarViajeOperadorPayload } from "./types";

function toastError(err: unknown, fallback: string) {
  const message = err instanceof ApiError ? err.message : fallback;
  notifications.show({ color: "red", title: "No se pudo completar", message });
}

export function useMisServicios() {
  return useQuery({
    queryKey: ["operador", "servicios"],
    queryFn: () => api.get<ServicioDetalle[]>("/api/v1/operador/servicios"),
  });
}

export function useServicioOperador(id: string | null) {
  const { data } = useMisServicios();
  return { data: data?.find((s) => s.id === id) ?? null };
}

function invalidar(client: ReturnType<typeof useQueryClient>) {
  client.invalidateQueries({ queryKey: ["operador", "servicios"] });
}

export function useIniciarServicio(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: IniciarServicioPayload) =>
      api.post<ServicioDetalle>(`/api/v1/operador/servicios/${servicioId}/iniciar`, payload),
    onSuccess: () => {
      invalidar(client);
      notifications.show({ color: "green", message: "Servicio iniciado" });
    },
    onError: (err) => toastError(err, "No se pudo iniciar el servicio"),
  });
}

export function useTerminarViajeOperador(_servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, payload }: { viajeId: string; payload: TerminarViajeOperadorPayload }) =>
      api.post(`/api/v1/operador/viajes/${viajeId}/terminar`, payload),
    onSuccess: () => {
      invalidar(client);
      notifications.show({ color: "green", message: "Viaje terminado" });
    },
    onError: (err) => toastError(err, "No se pudo terminar el viaje"),
  });
}

export function useAgregarAcuseOperador(_servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({
      viajeId,
      file,
      clientActionId,
    }: {
      viajeId: string;
      file: File;
      clientActionId: string;
    }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("client_action_id", clientActionId);
      return api.post(`/api/v1/operador/viajes/${viajeId}/acuses`, form);
    },
    onSuccess: () => invalidar(client),
    onError: (err) => toastError(err, "No se pudo subir el acuse"),
  });
}

export function useCerrarServicio(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: CerrarServicioPayload) =>
      api.post<ServicioDetalle>(`/api/v1/operador/servicios/${servicioId}/cerrar`, payload),
    onSuccess: () => {
      invalidar(client);
      notifications.show({ color: "green", message: "Servicio terminado" });
    },
    onError: (err) => toastError(err, "No se pudo cerrar el servicio"),
  });
}

export function useSubirTicket() {
  return useMutation({
    mutationFn: async ({ cargaId, file }: { cargaId: string; file: File }) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<{ ticket_url: string }>(`/api/v1/operador/cargas/${cargaId}/ticket`, form);
    },
    onError: (err) => toastError(err, "No se pudo subir el ticket"),
  });
}
