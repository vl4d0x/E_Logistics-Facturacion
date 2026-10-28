// Mensaje para avisar del servicio por WhatsApp (formato que usa Vlad en el grupo de operadores):
//   @~Juan /juan pablo
//   Nissan gris
//   1. Alimentos finos mexiquenses Neza, 175 kg, cita 10:00
//   2. Adrian campos Iztapalapa, 425 kg
// Acompañantes, kg y hora de cita son opcionales: sin ellos la línea se arma igual.

export interface DestinoMensaje {
  nombre: string;
  kg: number | null;
  horaCita: string;
}

export interface DatosMensaje {
  operador: string;
  acompanantes: string;
  unidad: string;
  destinos: DestinoMensaje[];
}

export function armarMensajeWhatsapp({ operador, acompanantes, unidad, destinos }: DatosMensaje): string {
  const primera = `@~${operador.trim()}${acompanantes.trim() ? ` /${acompanantes.trim()}` : ""}`;
  const lineas = [primera];
  if (unidad.trim()) lineas.push(unidad.trim());
  destinos.forEach((d, i) => {
    const partes = [d.nombre.trim()];
    if (d.kg) partes.push(`${d.kg} kg`);
    if (d.horaCita.trim()) partes.push(`cita ${d.horaCita.trim()}`);
    lineas.push(`${i + 1}. ${partes.join(", ")}`);
  });
  return lineas.join("\n");
}
