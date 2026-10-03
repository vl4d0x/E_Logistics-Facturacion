// Hooks de datos de la pantalla "Facturar" — TanStack Query sobre `api`.
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import type { FacturacionDetalle, FacturacionUpdate } from "./types";

function toastError(err: unknown, fallback: string) {
  const message = err instanceof ApiError ? err.message : fallback;
  notifications.show({ color: "red", title: "No se pudo completar", message });
}

function queryKey(servicioId: string) {
  return ["servicios", servicioId, "facturacion"];
}

export function useFacturacionDetalle(servicioId: string) {
  return useQuery({
    queryKey: queryKey(servicioId),
    queryFn: () => api.get<FacturacionDetalle>(`/api/v1/servicios/${servicioId}/facturacion`),
  });
}

export function useActualizarFacturacion(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: FacturacionUpdate) =>
      api.patch<FacturacionDetalle>(`/api/v1/servicios/${servicioId}/facturacion`, body),
    onSuccess: (data) => {
      client.setQueryData(queryKey(servicioId), data);
    },
    onError: (err) => toastError(err, "No se pudo guardar el cambio"),
  });
}

export function useFacturar(servicioId: string) {
  return useMutation({
    mutationFn: (totalEsperado: string) =>
      api.post(`/api/v1/servicios/${servicioId}/facturar`, { total_esperado: totalEsperado }),
  });
}
