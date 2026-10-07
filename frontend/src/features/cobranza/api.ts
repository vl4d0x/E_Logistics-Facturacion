// Fase 5 — cobranza y REP (`03-api-contract §11`).
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";

export interface ClienteCobranza {
  cliente: { id: string; nombre_comercial: string };
  saldo: string;
  facturas_abiertas: number;
  saldo_vencido: string;
  factura_mas_antigua: string | null;
}

export interface FacturaCobranza {
  id: string;
  folio: string;
  uuid_fiscal: string | null;
  cliente_nombre: string;
  fecha_emision: string | null;
  servicio: { id: string; numero: number; ruta_resumen: string };
  total: string;
  saldo_insoluto: string;
  estado_cobro: "pendiente" | "parcial" | "pagada";
  dias_transcurridos: number;
  vencida: boolean;
}

export interface FacturaCandidato {
  factura_id: string;
  folio: string;
  fecha_emision: string | null;
  total: string;
  saldo: string;
  servicio: { id: string; numero: number; fecha: string | null; ruta_resumen: string };
}

export interface Candidato {
  factura_ids: string[];
  facturas: FacturaCandidato[];
  aplicaciones: { factura_id: string; monto: string }[];
  suma: string;
  etiquetas: string[];
  explicacion: string;
  diferencia: string | null;
  factura_parcial_id: string | null;
}

export interface Sugerencias {
  objetivo: string;
  saldo_total_cliente: string;
  exactas: Candidato[];
  total_exactas: number;
  ambigua: boolean;
  nota_montos_iguales: boolean;
  aproximadas: Candidato[];
  fifo_parcial: Candidato | null;
  excede_saldo: string | null;
  busqueda_completa: boolean;
  facturas_consideradas: number;
}

export interface Rep {
  id: string;
  pago_id: string;
  estado: "timbrado" | "cancelacion_pendiente" | "cancelado" | "error";
  uuid_fiscal: string | null;
  serie: string | null;
  folio: string | null;
  fecha_emision: string | null;
  pdf_url: string | null;
  xml_url: string | null;
  error_detalle: string | null;
  enviado_at: string | null;
}

export interface PagoResumen {
  id: string;
  cliente: { id: string; nombre_comercial: string };
  fecha_pago: string;
  monto: string;
  forma_pago: string;
  num_operacion: string | null;
  estado: "registrado" | "aplicado" | "rep_emitido";
  notas: string | null;
  vence_rep: string;
  rep_pendiente: boolean;
  dias_para_vencer: number | null;
  rep_vigente: Rep | null;
  acciones_permitidas: string[];
}

export interface PagoDetalle extends PagoResumen {
  aplicaciones: {
    factura_id: string;
    folio: string;
    monto: string;
    num_parcialidad: number;
    saldo_anterior: string;
    saldo_insoluto: string;
  }[];
  reps: Rep[];
  tiene_comprobante: boolean;
}

export interface PagoPayload {
  cliente_id: string;
  fecha_pago: string;
  monto: string;
  forma_pago: string;
  num_operacion?: string;
  notas?: string;
  aplicaciones?: { factura_id: string; monto: string }[];
  emitir_rep?: boolean;
}

const toastError = (title: string) => (err: unknown) =>
  notifications.show({
    color: "red",
    title,
    message: err instanceof ApiError ? err.message : "Error inesperado",
  });

export const useCobranzaClientes = () =>
  useQuery({ queryKey: ["cobranza", "clientes"], queryFn: () => api.get<ClienteCobranza[]>("/api/v1/cobranza/clientes") });

export function useCobranzaFacturas(clienteId: string | null, estados: string, mes?: string | null, anio?: string | null) {
  const params = new URLSearchParams({ estado_cobro: estados });
  if (clienteId) params.set("cliente_id", clienteId);
  if (mes) params.set("mes_emision", mes);
  if (anio) params.set("anio", anio);
  return useQuery({
    queryKey: ["cobranza", "facturas", clienteId, estados, mes, anio],
    queryFn: () => api.get<FacturaCobranza[]>(`/api/v1/cobranza/facturas?${params}`),
  });
}

export function useSugerencias(clienteId: string | null, monto: number | null) {
  return useQuery({
    queryKey: ["cobranza", "sugerencias", clienteId, monto],
    enabled: !!clienteId && !!monto && monto > 0,
    queryFn: () =>
      api.post<Sugerencias>("/api/v1/cobranza/sugerencias", { cliente_id: clienteId, monto: (monto as number).toFixed(2) }),
  });
}

export const usePagos = (soloPendientes = false) =>
  useQuery({
    queryKey: ["pagos", "list", soloPendientes],
    queryFn: () => api.get<PagoResumen[]>(`/api/v1/pagos${soloPendientes ? "?rep_pendiente=true" : ""}`),
  });

export const usePago = (id: string) =>
  useQuery({ queryKey: ["pagos", "detail", id], queryFn: () => api.get<PagoDetalle>(`/api/v1/pagos/${id}`) });

function useInvalidar() {
  const client = useQueryClient();
  return () => {
    client.invalidateQueries({ queryKey: ["cobranza"] });
    client.invalidateQueries({ queryKey: ["pagos"] });
    client.invalidateQueries({ queryKey: ["facturas"] });
  };
}

export function useCrearPago() {
  const invalidar = useInvalidar();
  return useMutation({
    mutationFn: (payload: PagoPayload) => api.post<PagoDetalle>("/api/v1/pagos", payload),
    onSuccess: () => {
      invalidar();
      notifications.show({ color: "green", message: "Pago registrado" });
    },
    onError: toastError("No se pudo registrar el pago"),
  });
}

function usePost<TBody = undefined>(path: (id: string) => string, mensaje: string, fallo: string) {
  const invalidar = useInvalidar();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body?: TBody }) => api.post<unknown>(path(id), body),
    onSuccess: () => {
      invalidar();
      notifications.show({ color: "green", message: mensaje });
    },
    onError: toastError(fallo),
  });
}

export const useGenerarRep = () => usePost((id) => `/api/v1/pagos/${id}/rep`, "REP generado", "No se pudo generar el REP");
export const useRevertirPago = () => usePost((id) => `/api/v1/pagos/${id}/revertir`, "Pago revertido", "No se pudo revertir");
export const useEnviarRep = () =>
  usePost<{ to?: string[] }>((id) => `/api/v1/reps/${id}/enviar`, "REP enviado", "No se pudo enviar el REP");
export const useCancelarRep = () =>
  usePost<{ motivo: string }>((id) => `/api/v1/reps/${id}/cancelar`, "Cancelación solicitada", "No se pudo cancelar el REP");
export const useActualizarEstatusRep = () =>
  usePost((id) => `/api/v1/reps/${id}/actualizar-estatus`, "Estatus actualizado", "No se pudo actualizar el estatus");

export const centavos = (v: string | number) => Math.round(Number(v) * 100);
export const pesos = (v: string | number) =>
  Number(v).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
