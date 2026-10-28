import { describe, expect, it } from "vitest";
import { armarMensajeWhatsapp } from "./mensajeWhatsapp";

describe("armarMensajeWhatsapp", () => {
  it("arma el mensaje completo", () => {
    expect(
      armarMensajeWhatsapp({
        operador: "Juan",
        acompanantes: "juan pablo",
        unidad: "Nissan gris",
        destinos: [
          { nombre: "Alimentos finos mexiquenses Neza", kg: 175, horaCita: "10:00" },
          { nombre: "Adrian campos Iztapalapa", kg: 425, horaCita: "" },
        ],
      }),
    ).toBe(
      "@~Juan /juan pablo\nNissan gris\n1. Alimentos finos mexiquenses Neza, 175 kg, cita 10:00\n2. Adrian campos Iztapalapa, 425 kg",
    );
  });

  it("sin acompañantes, kg ni cita sigue armándose", () => {
    expect(
      armarMensajeWhatsapp({
        operador: "Juan",
        acompanantes: " ",
        unidad: "Nissan gris",
        destinos: [{ nombre: "Lesaffre", kg: null, horaCita: "" }],
      }),
    ).toBe("@~Juan\nNissan gris\n1. Lesaffre");
  });
});
