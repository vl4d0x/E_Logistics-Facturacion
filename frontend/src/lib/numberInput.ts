// Mantine `NumberInput.onChange` entrega `number | string`: puede mandar un string
// en un valor intermedio mientras se escribe, o al reformatear con
// `fixedDecimalScale` al perder el foco — nunca tratar un string como "vacío" o se
// pierde el valor justo antes de guardarlo (visto en vivo: el subtotal volvía a null
// al salir del campo). Usa esto en vez de `typeof v === "number" ? v : fallback`.
export function numberInputValue(v: number | string): number | null {
  if (typeof v === "number") return v;
  if (v.trim() === "") return null;
  const parsed = Number(v.replace(/[$,\s]/g, ""));
  return Number.isNaN(parsed) ? null : parsed;
}
