// Historial de movimientos de los admins (facturar, enviar factura, cancelar).
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";

export interface Movimiento {
  id: string;
  created_at: string;
  usuario: { id: string; nombre: string };
  tipo: string;
  etiqueta: string;
  descripcion: string;
  servicio_id: string | null;
  factura_id: string | null;
}

export interface FiltrosHistorial {
  usuario_id: string;
  tipo: string;
  desde: string;
  hasta: string;
  page: number;
}

export const TAMANO_PAGINA = 50;

export function useHistorial(f: FiltrosHistorial) {
  const params = new URLSearchParams({ page: String(f.page), size: String(TAMANO_PAGINA) });
  if (f.usuario_id) params.set("usuario_id", f.usuario_id);
  if (f.tipo) params.set("tipo", f.tipo);
  if (f.desde) params.set("desde", f.desde);
  if (f.hasta) params.set("hasta", f.hasta);
  return useQuery({
    queryKey: ["historial", f],
    queryFn: () => api.get<{ items: Movimiento[]; total: number }>(`/api/v1/historial?${params}`),
    placeholderData: keepPreviousData,
  });
}

export function useFiltrosHistorial() {
  return useQuery({
    queryKey: ["historial", "filtros"],
    queryFn: () =>
      api.get<{ admins: { id: string; nombre: string }[]; tipos: { value: string; label: string }[] }>(
        "/api/v1/historial/filtros",
      ),
  });
}
