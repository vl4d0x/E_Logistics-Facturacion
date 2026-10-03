// Vista previa (solo lectura) del medidor que verá el operador — `05-ui-spec §5 FuelGauge`.
// H1.1: "al elegir barras, el formulario muestra una vista previa del FuelGauge". La
// versión interactiva completa (arrastrar, tocar, teclado) es de la PWA del operador,
// Fase 3 — aquí solo ayuda al admin a visualizar cuántas barras está configurando.
import { Group, Text } from "@mantine/core";
import type { TipoMedidor } from "../types";

const OCTAVOS_EJEMPLO = 5; // ~½ tanque, solo ilustrativo

export function FuelGaugePreview({
  tipoMedidor,
  numBarras,
}: {
  tipoMedidor: TipoMedidor;
  numBarras: number | null;
}) {
  if (tipoMedidor === "aguja") {
    return (
      <div>
        <Group justify="space-between" mb={4}>
          {["E", "¼", "½", "¾", "F"].map((etiqueta) => (
            <Text key={etiqueta} size="xs" c="dimmed" fw={600}>
              {etiqueta}
            </Text>
          ))}
        </Group>
        <div
          style={{
            height: 10,
            borderRadius: 999,
            background: "var(--el-line)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: "50%",
              background: "var(--el-red)",
              borderRadius: 999,
            }}
          />
        </div>
        <Text size="xs" c="dimmed" mt={4}>
          Vista previa — así se ve el medidor de aguja (ejemplo a ½ tanque)
        </Text>
      </div>
    );
  }

  const total = numBarras && numBarras >= 2 ? numBarras : 0;
  const llenas = Math.round((OCTAVOS_EJEMPLO / 8) * total);

  return (
    <div>
      <Group gap={4}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            style={{
              width: 14,
              height: 24,
              borderRadius: 3,
              background: i < llenas ? "var(--el-red)" : "var(--el-line)",
            }}
          />
        ))}
        {total === 0 && (
          <Text size="xs" c="dimmed">
            Captura el número de barras para ver la vista previa
          </Text>
        )}
      </Group>
      {total > 0 && (
        <Text size="xs" c="dimmed" mt={4}>
          Vista previa — {llenas} de {total} barras (ejemplo)
        </Text>
      )}
    </div>
  );
}
