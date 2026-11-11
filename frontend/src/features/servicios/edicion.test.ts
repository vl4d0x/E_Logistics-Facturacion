import { describe, expect, it } from "vitest";
import { cambiosDeViaje } from "./api";
import type { ViajeOut } from "./types";

const lugar = (id: string) => ({ id, nombre: id, codigo_postal: "52000" }) as ViajeOut["origen"];

const viaje = {
  id: "v1",
  tipo: "entrega",
  origen: null,
  destino: lugar("d1"),
  origen_cp: null,
  destino_cp: null,
  distancia_km: 70,
  notas_admin: null,
} as unknown as ViajeOut;

describe("cambiosDeViaje", () => {
  it("sin cambios no manda nada", () => {
    expect(
      cambiosDeViaje(viaje, {
        tipo: "entrega",
        origen_lugar_id: null,
        destino_lugar_id: "d1",
        origen_cp: null,
        destino_cp: null,
        distancia_km: 70,
        notas_admin: "",
      }),
    ).toEqual({});
  });

  it("manda solo lo que cambió (destino, km y CP propio)", () => {
    expect(
      cambiosDeViaje(viaje, {
        tipo: "entrega",
        destino_lugar_id: "d2",
        destino_cp: "50000",
        distancia_km: 120,
        notas_admin: null,
      }),
    ).toEqual({ destino_lugar_id: "d2", destino_cp: "50000", distancia_km: 120 });
  });

  it("quitar el CP propio o el km se manda como null", () => {
    const con = { ...viaje, destino_cp: "50000" } as ViajeOut;
    expect(
      cambiosDeViaje(con, { tipo: "entrega", destino_lugar_id: "d1", destino_cp: null, distancia_km: null }),
    ).toEqual({ destino_cp: null, distancia_km: null });
  });
});
