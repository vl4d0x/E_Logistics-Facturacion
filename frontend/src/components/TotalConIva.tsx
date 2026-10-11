// Desglose "subtotal + IVA − retención = total" para cualquier lugar donde se capture o
// muestre un subtotal. Usa el régimen del receptor real (retención 4% solo a personas
// morales), igual que el CFDI (`lib/money.ts` espeja `facturacion/taxes.py`).
import { Group, Stack, Text } from "@mantine/core";
import { calcularImpuestos } from "../lib/money";
import type { RegimenReceptor } from "../features/catalogos/types";

const pesos = (n: number) => `$${n.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function TotalConIva({
  subtotal,
  regimenReceptor,
}: {
  subtotal: number | null | undefined;
  regimenReceptor: RegimenReceptor | null | undefined;
}) {
  if (subtotal == null || !(subtotal > 0)) return null;
  if (!regimenReceptor) {
    return (
      <Text size="xs" c="dimmed" mt={6}>
        Elige un cliente para ver el total con IVA.
      </Text>
    );
  }
  const m = calcularImpuestos(subtotal, regimenReceptor);
  return (
    <Stack gap={2} mt={6}>
      <Group justify="space-between">
        <Text size="xs" c="dimmed">
          IVA 16%
        </Text>
        <Text size="xs" ff="monospace">
          {pesos(m.ivaTrasladado)}
        </Text>
      </Group>
      {regimenReceptor === "moral" && (
        <Group justify="space-between">
          <Text size="xs" c="dimmed">
            Retención IVA 4%
          </Text>
          <Text size="xs" ff="monospace">
            −{pesos(m.ivaRetenido)}
          </Text>
        </Group>
      )}
      <Group justify="space-between">
        <Text size="sm" fw={700}>
          Total con IVA
        </Text>
        <Text size="sm" fw={700} ff="monospace">
          {pesos(m.total)}
        </Text>
      </Group>
    </Stack>
  );
}
