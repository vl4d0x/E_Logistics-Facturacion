// Tipos de operación en campo — reflejan `backend/app/modules/operacion/schemas.py`.

export interface Checklist {
  unidad_limpia: boolean;
  fumigacion_vigente: boolean;
  botiquin: boolean;
  casco_chaleco: boolean;
  aceite_ok: boolean;
  anticongelante_ok: boolean;
  neumaticos_ok: boolean;
  extintor_ok: boolean;
}

export const ETIQUETAS_CHECKLIST: Record<keyof Checklist, string> = {
  unidad_limpia: "Unidad limpia",
  fumigacion_vigente: "Certificado de fumigación vigente",
  botiquin: "Botiquín en unidad",
  casco_chaleco: "Casco y chaleco en unidad",
  aceite_ok: "Nivel de aceite óptimo",
  anticongelante_ok: "Nivel de anticongelante óptimo",
  neumaticos_ok: "Neumáticos en buen estado",
  extintor_ok: "Carga de extintor óptima",
};

export interface LecturaMedidor {
  tipo: "aguja" | "barras";
  octavos?: number;
  barras?: number;
  total?: number;
}

export interface IniciarServicioPayload {
  client_action_id: string;
  realizada_at: string;
  checklist: Checklist;
  observaciones?: string | null;
  lectura_medidor: LecturaMedidor;
  odometro_km?: number | null;
}

export interface TerminarViajeOperadorPayload {
  client_action_id: string;
  terminado_at: string;
  hora_llegada?: string | null;
  notas?: string | null;
  mercancias?: { mercancia_frecuente_id: string; cantidad: number; peso_kg: number }[];
  referencia_acuse?: string | null;
}

export interface KmPorViaje {
  viaje_id: string;
  km: number;
}

export interface CargaPayload {
  id: string;
  litros: number;
  precio_litro: number;
  importe: number;
  tipo_combustible?: string | null;
  cargada_at: string;
}

export interface CerrarServicioPayload {
  client_action_id: string;
  cerrado_at: string;
  km_por_viaje: KmPorViaje[];
  lectura_medidor: LecturaMedidor;
  odometro_km?: number | null;
  observaciones?: string | null;
  cargo_combustible: boolean;
  cargas: CargaPayload[];
}

export interface Inspeccion {
  todo_ok: boolean;
  fallas: string[];
  observaciones: string | null;
  nivel_combustible: number;
  lectura_medidor: LecturaMedidor;
  odometro_km: number | null;
  realizada_at: string;
}

export interface Cierre {
  nivel_combustible: number;
  lectura_medidor: LecturaMedidor;
  odometro_km: number | null;
  cargo_combustible: boolean;
  observaciones: string | null;
  cerrado_at: string;
}

export interface MercanciaClienteResumen {
  id: string;
  nombre_humano: string;
  unidad_desc: string | null;
  peso_kg_sugerido: number | null;
}

export interface CargaDraft {
  id: string;
  litros: number | null;
  precioLitro: number | null;
  importe: number | null;
  ticket: File | null;
}

export function nuevaCargaDraft(): CargaDraft {
  return { id: crypto.randomUUID(), litros: null, precioLitro: null, importe: null, ticket: null };
}

export interface CargaOut {
  id: string;
  litros: number;
  precio_litro: number;
  importe: number;
  tipo_combustible: string | null;
  ticket_url: string | null;
  cargada_at: string;
}
