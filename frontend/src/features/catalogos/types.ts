// Tipos de catálogos — reflejan `backend/app/modules/catalogos/schemas.py` (`03-api-contract §5`).

export type TipoMedidor = "aguja" | "barras";
export type RegimenReceptor = "fisica" | "moral";
export type ModoAcuse = "escaneo" | "referencia" | "ninguno";
export type MetodoPago = "PUE" | "PPD";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface UsoOut {
  referencias: Record<string, number>;
  accion_al_eliminar: "archivar" | "eliminar";
  bloqueos: { servicio_id: string; numero: number; estado: string }[];
}

export interface DeleteResultOut {
  resultado: "eliminado" | "archivado";
}

// --- Unidad ---
export interface Unidad {
  id: string;
  apodo: string;
  placa: string;
  anio_modelo: number | null;
  config_vehicular: string;
  peso_bruto_vehicular: number;
  capacidad_carga_kg: number | null;
  perm_sct: string;
  num_permiso_sct: string;
  aseguradora_resp_civil: string | null;
  poliza_resp_civil: string | null;
  tipo_medidor: TipoMedidor;
  num_barras: number | null;
  capacidad_tanque_l: number | null;
  tipo_combustible: string | null;
  activo: boolean;
}

export type UnidadPayload = Omit<Unidad, "id" | "activo">;

// --- Operador ---
export interface Operador {
  id: string;
  nombre: string;
  rfc: string;
  num_licencia: string;
  telefono: string | null;
  activo: boolean;
}

export type OperadorPayload = Omit<Operador, "id" | "activo">;

export interface AccesoOperador {
  usuario_id: string;
  email: string;
  activo: boolean;
}

// --- Cliente ---
export interface Cliente {
  id: string;
  razon_social: string;
  nombre_comercial: string;
  rfc: string;
  cp_fiscal: string;
  regimen_fiscal: string;
  regimen_receptor: RegimenReceptor;
  uso_cfdi: string;
  metodo_pago_default: MetodoPago;
  modo_acuse: ModoAcuse;
  emails_facturacion: string[];
  dias_credito: number;
  activo: boolean;
}

export type ClientePayload = Omit<Cliente, "id" | "activo">;

// --- Mercancía frecuente ---
export interface Mercancia {
  id: string;
  cliente_id: string;
  nombre_humano: string;
  bienes_transp: string;
  clave_unidad: string;
  unidad_desc: string | null;
  peso_kg_sugerido: number | null;
  activo: boolean;
}

export type MercanciaPayload = Omit<Mercancia, "id" | "cliente_id" | "activo">;

// --- Lugar ---
export interface Lugar {
  id: string;
  cliente_id: string | null;
  nombre: string;
  rfc_remitente_destinatario: string;
  nombre_remitente_destinatario: string | null;
  calle: string | null;
  num_exterior: string | null;
  colonia: string | null;
  localidad: string | null;
  municipio: string | null;
  estado: string;
  pais: string;
  codigo_postal: string;
  referencia: string | null;
  es_origen_predeterminado: boolean;
  activo: boolean;
}

export type LugarPayload = Omit<Lugar, "id" | "activo">;

// --- Usuarios administradores ---
export interface UsuarioAdmin {
  id: string;
  nombre: string;
  email: string;
  activo: boolean;
}
