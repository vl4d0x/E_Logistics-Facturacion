// Fecha de "hoy" en hora de México (`01-architecture §9`). `toISOString()` da la fecha UTC:
// después de las 18:00 en México ya es "mañana" y los formularios proponían el día siguiente.
export function hoyMexico(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City" }).format(new Date());
}

/** "2026-10-11" (o un ISO con hora) → "11/10/2026", sin que la zona horaria mueva el día. */
export function fechaCorta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return d && m && a ? `${d}/${m}/${a}` : iso;
}
