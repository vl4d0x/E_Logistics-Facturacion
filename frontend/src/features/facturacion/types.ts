// Tipos de la pantalla "Facturar" — reflejan `backend/app/modules/facturacion/schemas.py`
// (`03-api-contract §9`).
import type { RegimenReceptor } from "../catalogos/types";

export interface Receptor {
  razon_social: string;
  rfc: string;
  cp_fiscal: string;
  regimen_fiscal: string;
  regimen_receptor: RegimenReceptor;
  uso_cfdi: string;
  metodo_pago: string;
  forma_pago: string;
}

export interface Concepto {
  clave_prod_serv: string;
  clave_unidad: string;
  descripcion: string;
  descripcion_autogenerada: boolean;
  requiere_folio: boolean;
  folio_cliente: string | null;
}

export interface Ubicacion {
  id_ubicacion: string;
  tipo: "Origen" | "Destino";
  viaje_id: string;
  lugar: {
    id?: string;
    nombre?: string;
    calle?: string | null;
    num_exterior?: string | null;
    colonia?: string | null;
    municipio?: string | null;
    estado?: string | null;
    pais?: string | null;
    codigo_postal?: string | null;
  };
  fecha_hora: string | null;
  fecha_hora_fuente: "real" | "programada";
  distancia_km: number | null;
  km_reportado: number | null;
}

export interface MercanciaFacturar {
  viaje_id: string;
  descripcion: string;
  bienes_transp: string;
  clave_unidad: string;
  cantidad: string; // Decimal serializado como string, p.ej. "1.0000000000"
  peso_kg: number;
}

export interface Autotransporte {
  apodo: string;
  placa: string;
  config_vehicular: string;
  peso_bruto_vehicular: number;
  perm_sct: string;
  num_permiso_sct: string;
  aseguradora: string | null;
  poliza: string | null;
}

export interface Figura {
  nombre: string;
  rfc: string;
  num_licencia: string;
}

export interface Montos {
  subtotal: string;
  iva_trasladado: string;
  iva_retenido: string;
  total: string;
}

export interface DesgloseLinea {
  concepto: string;
  monto: string;
}

export interface PrecioSugerido {
  monto: string | null;
  desglose: DesgloseLinea[];
  confianza: "alta" | "media" | "baja" | null;
  fuente: string | null;
  explicacion: string;
  referencias: number[];
  ultimos_precios_ruta: { fecha: string; subtotal: string }[];
  rango: [string, string] | null;
  configuracion_pendiente: boolean;
}

export interface AcuseFacturar {
  viaje_id: string;
  tipo: string;
  url: string | null;
  referencia: string | null;
  pagina: number;
}

export interface ValidacionCheck {
  regla: string;
  nivel: "ok" | "warning" | "error";
  mensaje: string;
  campo: string | null;
}

export interface Validacion {
  ok: boolean;
  checks: ValidacionCheck[];
  preview: Montos | null;
}

export interface FacturacionDetalle {
  modo: "normal" | "anticipado";
  servicio_id: string;
  receptor: Receptor;
  concepto: Concepto;
  ubicaciones: Ubicacion[];
  mercancias: MercanciaFacturar[];
  autotransporte: Autotransporte;
  figura: Figura;
  montos: Montos | null;
  precio_sugerido: PrecioSugerido;
  acuses: AcuseFacturar[];
  validacion: Validacion;
  facturama_configurado: boolean;
}

export interface FacturacionUpdate {
  subtotal?: number | null;
  descripcion_concepto?: string | null;
  folio_cliente?: string | null;
  uso_cfdi?: string;
  metodo_pago?: string;
}
