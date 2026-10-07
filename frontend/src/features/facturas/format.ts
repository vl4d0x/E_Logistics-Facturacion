export const ESTADO_FACTURA: Record<string, { label: string; color: string }> = {
  timbrada: { label: "Timbrada", color: "green" },
  cancelacion_pendiente: { label: "Cancelación en espera", color: "yellow" },
  cancelada: { label: "Cancelada", color: "gray" },
  error: { label: "Error", color: "red" },
};

export const pesos = (v: string) =>
  Number(v).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
