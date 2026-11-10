// H4.8-H4.10 — lista, detalle, descarga, correo y cancelación de facturas.
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ApiError } from "../../lib/api";
import { getAccessToken } from "../../lib/auth";

export interface FacturaResumen {
  id: string;
  origen: "app" | "facturador";
  servicio_id: string | null; // null en las importadas del Facturador Electrónico
  servicio_numero: number | null;
  cliente_id: string;
  cliente_nombre: string;
  estado: "timbrada" | "cancelacion_pendiente" | "cancelada" | "error";
  estado_cobro: "pendiente" | "parcial" | "pagada";
  serie: string | null;
  folio: string | null;
  uuid_fiscal: string | null;
  fecha_emision: string | null;
  subtotal: string;
  total: string;
  saldo_insoluto: string;
  enviado_at: string | null;
  envio_error: string | null;
}

export interface FacturaDetalle extends FacturaResumen {
  iva_trasladado: string;
  iva_retenido: string;
  archivos_guardados: boolean;
  error_detalle: string | null;
  motivo_cancelacion: string | null;
  cancelacion_solicitada_at: string | null;
  cancelada_at: string | null;
  envio_destinatarios: string[] | null;
  emails_cliente: string[];
  ejercicio_anterior: boolean;
  receptor_nombre: string;
  metodo_pago: string;
  pagado_externo: string;
}

export interface ResultadoImportacion {
  creadas: number;
  actualizadas: number;
  de_la_app: number;
  ignoradas: number;
  clientes_creados: string[];
  vigentes: number;
  canceladas: number;
  pagadas: number;
  con_saldo: number;
  saldo_total: string;
}

export function useImportarFacturador() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<ResultadoImportacion>("/api/v1/facturas/importar-facturador", form);
    },
    onSuccess: () => {
      for (const k of ["facturas", "cobranza", "dashboard", "clientes"]) client.invalidateQueries({ queryKey: [k] });
    },
    onError: toastError("No se pudo importar el reporte"),
  });
}

export interface FacturasFiltros {
  estado: string;
  mes: string;
  origen?: string;
  desde?: string;
  hasta?: string;
}

const toastError = (title: string) => (err: unknown) =>
  notifications.show({
    color: "red",
    title,
    message: err instanceof ApiError ? err.message : "Error inesperado",
    // Lo que responde Facturama (cancelar, timbrar) hay que poder leerlo: no se cierra solo.
    autoClose: err instanceof ApiError && err.code === "facturama_error" ? false : 6000,
  });

export function useFacturas(filtros: FacturasFiltros) {
  const params = new URLSearchParams();
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.mes) params.set("mes", filtros.mes);
  if (filtros.origen) params.set("origen", filtros.origen);
  if (filtros.desde) params.set("desde", filtros.desde);
  if (filtros.hasta) params.set("hasta", filtros.hasta);
  return useQuery({
    queryKey: ["facturas", "list", filtros],
    queryFn: () => api.get<FacturaResumen[]>(`/api/v1/facturas?${params}`),
  });
}

export function useFactura(id: string) {
  return useQuery({
    queryKey: ["facturas", "detail", id],
    queryFn: () => api.get<FacturaDetalle>(`/api/v1/facturas/${id}`),
  });
}

function useAccionFactura<TBody>(id: string, accion: string, mensaje: string, fallo: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: TBody) => api.post<FacturaDetalle>(`/api/v1/facturas/${id}/${accion}`, body),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["facturas"] });
      client.invalidateQueries({ queryKey: ["servicios"] });
      notifications.show({ color: "green", message: mensaje });
    },
    onError: toastError(fallo),
  });
}

export const useCancelarFactura = (id: string) =>
  useAccionFactura<{ motivo: string }>(id, "cancelar", "Cancelación solicitada", "No se pudo cancelar");
export const useActualizarEstatus = (id: string) =>
  useAccionFactura<undefined>(id, "actualizar-estatus", "Estatus actualizado", "No se pudo actualizar el estatus");
export const useEnviarFactura = (id: string) =>
  useAccionFactura<{ to?: string[] }>(id, "enviar", "Correo enviado", "No se pudo enviar el correo");

async function pedirArchivo(id: string, formato: "pdf" | "xml") {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  return fetch(`${base}/api/v1/facturas/${id}/descargar?formato=${formato}`, {
    headers: { Authorization: `Bearer ${getAccessToken()}` },
  });
}

/** PDF de la factura como URL local (blob) para mostrarlo incrustado; se libera al salir. */
export function usePdfFactura(id: string, habilitado: boolean) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!habilitado) return;
    let vigente = true;
    let creada: string | null = null;
    setError(false);
    pedirArchivo(id, "pdf")
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status));
        const blob = new Blob([await res.blob()], { type: "application/pdf" });
        creada = URL.createObjectURL(blob);
        if (vigente) setUrl(creada);
      })
      .catch(() => vigente && setError(true));
    return () => {
      vigente = false;
      if (creada) URL.revokeObjectURL(creada);
    };
  }, [id, habilitado]);
  return { url, error };
}

/** Descarga con el token (el endpoint exige Bearer, no sirve un `<a href>`). */
export async function descargarFactura(id: string, formato: "pdf" | "xml") {
  const res = await pedirArchivo(id, formato);
  if (!res.ok) {
    toastError("No se pudo descargar")(new ApiError("internal_error", "No se pudo descargar el archivo", res.status));
    return;
  }
  const nombre = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? `factura.${formato}`;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

// --- "Enviar todas": facturas timbradas aquí que todavía no le llegan al cliente ---------------

export interface FacturaPorEnviar extends FacturaResumen {
  destinatarios: string[];
  motivo_no_enviable: string | null;
}

export interface EnvioPendiente {
  modo_prueba: boolean;
  destino_prueba: string | null;
  copia: string | null;
  facturas: FacturaPorEnviar[];
}

export interface ResultadoEnvio {
  enviadas: { id: string; folio: string; destinatarios: string[] }[];
  omitidas: { id: string; folio: string | null; motivo: string }[];
  fallidas: { id: string; folio: string; error: string }[];
}

export function useEnvioPendiente(enabled = true) {
  return useQuery({
    queryKey: ["facturas", "envio-pendiente"],
    queryFn: () => api.get<EnvioPendiente>("/api/v1/facturas/envio-pendiente"),
    enabled,
  });
}

export function useEnviarPendientes() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => api.post<ResultadoEnvio>("/api/v1/facturas/enviar-pendientes", { ids }),
    onSettled: () => {
      client.invalidateQueries({ queryKey: ["facturas"] });
      client.invalidateQueries({ queryKey: ["servicios"] });
    },
    onError: toastError("No se pudieron enviar las facturas"),
  });
}
