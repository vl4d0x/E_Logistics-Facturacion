// Cálculo de impuestos — espejo de `backend/app/modules/facturacion/taxes.py`
// (`04-facturacion-cfdi §3-3.1`). El backend es la verdad; esto es solo para
// feedback instantáneo en la UI. Aritmética en centavos (enteros) para evitar
// errores de redondeo de punto flotante.
import type { RegimenReceptor } from "../features/catalogos/types";

export interface Montos {
  subtotal: number;
  ivaTrasladado: number;
  ivaRetenido: number;
  total: number;
}

function aCentavos(pesos: number): number {
  return Math.round(pesos * 100);
}

function aPesos(centavos: number): number {
  return centavos / 100;
}

function redondearHalfUp(centavos: number): number {
  return Math.floor(centavos + 0.5);
}

export function calcularImpuestos(subtotal: number, regimenReceptor: RegimenReceptor): Montos {
  const subtotalCent = aCentavos(subtotal);
  const ivaTrasladadoCent = redondearHalfUp(subtotalCent * 0.16);
  const ivaRetenidoCent = regimenReceptor === "moral" ? redondearHalfUp(subtotalCent * 0.04) : 0;
  const totalCent = subtotalCent + ivaTrasladadoCent - ivaRetenidoCent;
  return {
    subtotal: aPesos(subtotalCent),
    ivaTrasladado: aPesos(ivaTrasladadoCent),
    ivaRetenido: aPesos(ivaRetenidoCent),
    total: aPesos(totalCent),
  };
}

export function subtotalDesdeTotal(total: number, regimenReceptor: RegimenReceptor): number {
  const factor = regimenReceptor === "moral" ? 1.12 : 1.16;
  const totalCent = aCentavos(total);
  return aPesos(redondearHalfUp(totalCent / factor));
}
