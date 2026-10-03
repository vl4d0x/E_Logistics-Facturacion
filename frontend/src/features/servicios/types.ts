// Tipos de servicios/viajes — reflejan `backend/app/modules/servicios/schemas.py` (`03-api-contract §6`).
import type { CargaOut, Cierre, Inspeccion, MercanciaClienteResumen } from "../operacion/types";

export type EstadoServicio = "programado" | "en_curso" | "terminado" | "cancelado";
export type EstadoFacturacion = "pendiente" | "facturado";
export type TipoViaje = "recoleccion" | "entrega" | "recoleccion_entrega";
export type EstadoViaje = "pendiente" | "terminado";

export interface LugarResumen {
  id: string;
  nombre: string;
  codigo_postal: string;
  calle: string | null;
  num_exterior: string | null;
  colonia: string | null;
  municipio: string | null;
  estado: string | null;
  referencia: string | null;
  rfc_remitente_destinatario: string | null;
  nombre_remitente_destinatario: string | null;
}

export interface AcuseOut {
  id: string;
  tipo: string;
  url: string | null;
  mime: string | null;
  pagina: number;
  referencia: string | null;
  subido_at: string;
}

export interface ViajeMercanciaOut {
  id: string;
  mercancia_frecuente_id: string | null;
  descripcion: string;
  bienes_transp: string;
  clave_unidad: string;
  unidad_desc: string | null;
  cantidad: number;
  peso_kg: number;
}

export interface ViajeMercanciaIn {
  mercancia_frecuente_id: string;
  cantidad: number;
  peso_kg: number;
}

export interface ViajeIn {
  tipo: TipoViaje;
  fecha?: string | null;
  origen_lugar_id?: string | null;
  destino_lugar_id?: string | null;
  distancia_km?: number | null;
  notas_admin?: string | null;
  hora_salida_programada?: string | null;
  hora_llegada_programada?: string | null;
  mercancias?: ViajeMercanciaIn[] | null;
}

export interface ViajeOut {
  id: string;
  orden: number;
  tipo: TipoViaje;
  estado: EstadoViaje;
  fecha: string;
  origen: LugarResumen | null;
  destino: LugarResumen | null;
  hora_salida_programada: string | null;
  hora_llegada_programada: string | null;
  distancia_km: number | null;
  km_reportado: number | null;
  hora_llegada: string | null;
  terminado_at: string | null;
  notas_admin: string | null;
  notas_operador: string | null;
  mercancias: ViajeMercanciaOut[];
  acuses: AcuseOut[];
  acuse_requerido: boolean;
  acuse_completo: boolean;
}

export interface ServicioCreate {
  cliente_id: string;
  unidad_id: string;
  operador_id: string;
  fecha: string;
  subtotal?: number | null;
  notas?: string | null;
  timbrado_anticipado?: boolean;
  viajes: ViajeIn[];
}

export interface ServicioUpdate {
  unidad_id?: string;
  operador_id?: string;
  fecha?: string;
  subtotal?: number | null;
  notas?: string | null;
  timbrado_anticipado?: boolean;
}

export interface ServicioDetalle {
  id: string;
  numero: number;
  fecha: string;
  estado: EstadoServicio;
  estado_facturacion: EstadoFacturacion;
  timbrado_anticipado: boolean;
  cliente: { id: string; nombre_comercial: string; modo_acuse: string; regimen_receptor: string };
  unidad: { id: string; apodo: string; tipo_medidor: string; num_barras: number | null };
  operador: { id: string; nombre: string };
  subtotal: number | null;
  notas: string | null;
  viajes: ViajeOut[];
  factura_vigente: Record<string, unknown> | null;
  datos_fiscales_bloqueados: boolean;
  acciones_permitidas: string[];
  mercancias_cliente: MercanciaClienteResumen[] | null;
  inspeccion: Inspeccion | null;
  cierre: Cierre | null;
  cargas: CargaOut[];
  combustible_total: { litros: number; importe: number } | null;
}

export interface ServicioListItem {
  id: string;
  numero: number;
  fecha: string;
  estado: EstadoServicio;
  estado_facturacion: EstadoFacturacion;
  timbrado_anticipado: boolean;
  cliente: string;
  unidad_apodo: string;
  operador_nombre: string;
  ruta_resumen: string;
  viajes_total: number;
  viajes_terminados: number;
  acuses_requeridos: number;
  acuses_completos: number;
  subtotal: number | null;
}

export interface Conteos {
  programados: number;
  en_curso: number;
  por_facturar: number;
  facturados: number;
  cancelados: number;
}

export type Vista = "programados" | "en_curso" | "por_facturar" | "facturados" | "cancelados";
