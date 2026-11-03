// Facturar con el Excel de registros: archivo vigente, filas, propuesta y alta del servicio.
import { notifications } from "@mantine/notifications";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import { getAccessToken } from "../../lib/auth";
import type { ServicioDetalle } from "../servicios/types";

export interface RegistroResumen {
  nombre_archivo: string;
  hoja: string;
  total_filas: number;
  ultima_fila: number;
  subido_at: string;
  enlaces_reubicados?: number;
}

export interface DatosFila {
  fecha: string | null;
  cliente: string | null;
  operador: string | null;
  unidad: string | null;
  origen: string | null;
  destino: string | null;
  subtotal: number | string | null;
  total: number | string | null;
  factura: number | string | null;
  ref: string | number | null;
  notas: string | null;
}

export interface ServicioDeFila {
  servicio_id: string;
  numero: number;
  estado: string;
  factura_folio: string | null;
  factura_id: string | null;
}

export interface FilaResumen {
  fila: number;
  datos: DatosFila;
  servicio: ServicioDeFila | null;
}

export type Confianza = "alta" | "media" | "ninguna";

export interface Elegido {
  id: string;
  nombre: string;
  score: number;
  confianza: Confianza;
  fuente: string;
}

export interface LugarCorto {
  id: string;
  nombre: string;
  codigo_postal: string;
}

export interface PropuestaLugar {
  texto: string;
  lugar: LugarCorto | null;
  score: number;
  confianza: Confianza;
  fuente: "recordado" | "parecido" | "predeterminado" | null;
  candidatos: (LugarCorto & { score: number })[];
  distancia_km: number;
  km_confirmado: boolean;
}

export interface Propuesta extends FilaResumen {
  registro: RegistroResumen;
  cliente: Elegido | null;
  modo_acuse: "escaneo" | "referencia" | "ninguno" | null;
  requiere_folio: boolean | null;
  operador: Elegido | null;
  unidad: Elegido | null;
  fecha: string | null;
  subtotal: string | null;
  origen: PropuestaLugar | null;
  destinos: PropuestaLugar[] | null;
  kg_sugerido: number | null;
  mercancia_sugerida_id: string | null;
  avisos: string[];
  lugar_generico: { rfc: string; estado: string; distancia_km: number };
}

export interface LugarElegidoIn {
  texto_excel: string | null;
  lugar_id?: string | null;
  nuevo?: { nombre: string; codigo_postal: string } | null;
}

export interface DestinoIn extends LugarElegidoIn {
  folio: string | null;
  sin_acuse: boolean;
  distancia_km: number | null;
  mercancias: { mercancia_frecuente_id: string; peso_kg: number; cantidad: number }[];
}

export interface CrearDesdeFilaIn {
  cliente_id: string;
  unidad_id: string;
  operador_id: string;
  fecha: string;
  subtotal: number | null;
  origen: LugarElegidoIn;
  destinos: DestinoIn[];
}

const BASE = "/api/v1/registro-excel";

function toastError(err: unknown, fallback: string) {
  notifications.show({ color: "red", title: "No se pudo completar", message: err instanceof ApiError ? err.message : fallback });
}

export function useRegistro() {
  return useQuery({
    queryKey: ["registro-excel"],
    queryFn: () => api.get<{ registro: RegistroResumen | null }>(BASE).then((r) => r.registro),
  });
}

export function useSubirRegistro() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<{ registro: RegistroResumen }>(BASE, form).then((r) => r.registro);
    },
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ["registro-excel"] });
      notifications.show({ color: "green", message: `Excel cargado: ${r.total_filas.toLocaleString("es-MX")} filas` });
    },
    onError: (err) => toastError(err, "No se pudo subir el Excel"),
  });
}

export function useFilasRecientes(enabled: boolean, pendientes: boolean) {
  return useQuery({
    queryKey: ["registro-excel", "filas", pendientes],
    queryFn: () => api.get<{ items: FilaResumen[] }>(`${BASE}/filas?pendientes=${pendientes}&limite=15`).then((r) => r.items),
    enabled,
  });
}

export function usePropuesta(fila: number | null, clienteId: string | null) {
  return useQuery({
    queryKey: ["registro-excel", "fila", fila, clienteId],
    queryFn: () => api.get<Propuesta>(`${BASE}/filas/${fila}${clienteId ? `?cliente_id=${clienteId}` : ""}`),
    enabled: fila !== null,
    retry: false,
    placeholderData: keepPreviousData,
  });
}

export function useCrearDesdeFila(fila: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: CrearDesdeFilaIn) => api.post<ServicioDetalle>(`${BASE}/filas/${fila}/servicio`, body),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["registro-excel"] });
      client.invalidateQueries({ queryKey: ["servicios"] });
      client.invalidateQueries({ queryKey: ["lugares"] });
    },
    onError: (err) => toastError(err, "No se pudo crear el servicio"),
  });
}

/** Descarga la copia del Excel con el número de factura escrito en la columna FACTURA. */
export async function descargarRegistro(): Promise<number | null> {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${base}${BASE}/descargar`, { headers: { Authorization: `Bearer ${getAccessToken()}` } });
  if (!res.ok) {
    notifications.show({ color: "red", title: "No se pudo descargar", message: "El servidor rechazó la descarga." });
    return null;
  }
  const disposition = res.headers.get("content-disposition") ?? "";
  const utf8 = /filename\*=UTF-8''([^;]+)/.exec(disposition)?.[1];
  const nombre = utf8 ? decodeURIComponent(utf8) : (/filename="([^"]+)"/.exec(disposition)?.[1] ?? "registros.xlsx");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
  return Number(res.headers.get("x-facturas-escritas") ?? 0);
}

export function useSinAcuse() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ viajeId, sinAcuse }: { viajeId: string; sinAcuse: boolean }) =>
      api.put(`/api/v1/viajes/${viajeId}/sin-acuse`, { sin_acuse: sinAcuse }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["servicios"] });
      client.invalidateQueries({ queryKey: ["facturacion"] });
    },
    onError: (err) => toastError(err, "No se pudo guardar"),
  });
}
