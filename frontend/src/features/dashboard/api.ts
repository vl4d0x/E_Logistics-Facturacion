// Fase 6 — dashboard (`03-api-contract §12`).
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";

export interface Pendientes {
  por_facturar: number;
  por_facturar_anticipados: number;
  acuses_faltantes: number;
  inspecciones_con_fallas: number;
  costos_pendientes: boolean;
  rep_por_emitir: { pagos: number; monto: string; vence: string | null };
  actualizado_at: string;
}

export interface Mes {
  mes: string; // "2026-10"
  facturado: string;
  cobrado: string;
  por_cobrar: string;
}

export interface Ingresos {
  periodo: Mes;
  meses_previos: Mes[];
  por_mes: Mes[];
  totales_anio: { facturado: string; cobrado: string; por_cobrar: string };
  actualizado_at: string;
}

export interface PorCobrar {
  total_clientes: number;
  items: { cliente: { id: string; nombre_comercial: string }; saldo: string; facturas_abiertas: number }[];
  actualizado_at: string;
}

export interface EnEspera {
  total: number;
  items: {
    tipo: "factura" | "rep";
    id: string;
    factura_id?: string;
    pago_id?: string;
    folio: string;
    cliente: string;
    total: string;
    solicitada_at: string | null;
  }[];
  actualizado_at: string;
}

export const usePendientes = () =>
  useQuery({ queryKey: ["dashboard", "pendientes"], queryFn: () => api.get<Pendientes>("/api/v1/dashboard/pendientes") });

export const useIngresos = (anio: number, mes: number) =>
  useQuery({
    queryKey: ["dashboard", "ingresos", anio, mes],
    queryFn: () => api.get<Ingresos>(`/api/v1/dashboard/ingresos?anio=${anio}&mes=${mes}`),
  });

export const usePorCobrar = (anio: string) =>
  useQuery({
    queryKey: ["dashboard", "por-cobrar", anio],
    queryFn: () => api.get<PorCobrar>(`/api/v1/dashboard/por-cobrar?anio=${anio}`),
  });

export const useEnEspera = () =>
  useQuery({
    queryKey: ["dashboard", "en-espera"],
    queryFn: () => api.get<EnEspera>("/api/v1/dashboard/cancelaciones-en-espera"),
  });

export const COBRADO = "#2f6fdd"; // azul y rojo validados con scripts/validate_palette.js (CVD y contraste)
export const POR_COBRAR = "#e0353b";

export const mesLabel = (mes: string) =>
  new Date(`${mes}-01T12:00:00`).toLocaleDateString("es-MX", { month: "short", year: "numeric" });
export const mesCorto = (mes: string) =>
  new Date(`${mes}-01T12:00:00`).toLocaleDateString("es-MX", { month: "short" }).replace(".", "");
export const pesos = (v: string | number) =>
  Number(v).toLocaleString("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
export const horaLocal = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
