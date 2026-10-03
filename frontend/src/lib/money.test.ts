// `04-facturacion-cfdi §3-3.1` — mismos casos que `backend/tests/test_taxes.py`.
import { describe, expect, it } from "vitest";
import { calcularImpuestos, subtotalDesdeTotal } from "./money";

describe("calcularImpuestos", () => {
  it("retiene 4% para receptor moral", () => {
    const montos = calcularImpuestos(1650.0, "moral");
    expect(montos.subtotal).toBe(1650.0);
    expect(montos.ivaTrasladado).toBe(264.0);
    expect(montos.ivaRetenido).toBe(66.0);
    expect(montos.total).toBe(1848.0);
  });

  it("no retiene para receptor física", () => {
    const montos = calcularImpuestos(1650.0, "fisica");
    expect(montos.ivaRetenido).toBe(0);
    expect(montos.total).toBe(1914.0);
  });
});

describe("subtotalDesdeTotal", () => {
  it("despeja el subtotal de un total con IVA (moral)", () => {
    expect(subtotalDesdeTotal(1848.0, "moral")).toBe(1650.0);
  });

  it("despeja el subtotal de un total con IVA (física)", () => {
    expect(subtotalDesdeTotal(1914.0, "fisica")).toBe(1650.0);
  });
});
