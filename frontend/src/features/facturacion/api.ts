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

export interface FacturarResultado {
  factura: { id: string; uuid_fiscal: string | null; estado: string; total: string };
  cancelada_automaticamente: boolean;
  cancelacion_error: string | null;
  archivos_guardados: boolean;
}

export function useFacturar(servicioId: string) {
  return useMutation({
    mutationFn: (totalEsperado: string) =>
      api.post<FacturarResultado>(`/api/v1/servicios/${servicioId}/facturar`, { total_esperado: totalEsperado }),
  });
}

export interface MercanciaItemIn {
  mercancia_frecuente_id: string;
  cantidad: number;
  peso_kg: number;
}

/** Reemplaza las mercancías de un viaje (`PUT /viajes/{id}/mercancias`) y refresca Facturar. */
export function useGuardarMercancias(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, items }: { viajeId: string; items: MercanciaItemIn[] }) =>
      api.put(`/api/v1/viajes/${viajeId}/mercancias`, items),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKey(servicioId) }),
    onError: (err) => toastError(err, "No se pudo guardar la mercancía"),
  });
}

/** Fija o corrige el folio del cliente de un viaje (se imprime en el concepto). */
export function useGuardarFolio(_servicioId?: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, folio }: { viajeId: string; folio: string }) =>
      api.put(`/api/v1/viajes/${viajeId}/folio`, { folio }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["servicios"] }),
    onError: (err) => toastError(err, "No se pudo guardar el folio"),
  });
}

/** Monto de cada destino del desglose de precio (`PUT /servicios/{id}/desglose-precio`). */
export function useGuardarDesglose(servicioId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (items: { viaje_id: string; monto: number | null }[]) =>
      api.put<FacturacionDetalle>(`/api/v1/servicios/${servicioId}/desglose-precio`, items),
    onSuccess: (data) => client.setQueryData(queryKey(servicioId), data),
    onError: (err) => toastError(err, "No se pudo guardar el desglose"),
  });
}
