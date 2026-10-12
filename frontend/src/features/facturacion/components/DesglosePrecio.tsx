// Desglose de precio: cuánto del subtotal corresponde a cada destino. No va al CFDI;
// se manda al cliente como tabla en el correo de la factura. Tiene que sumar el subtotal.
import { Button, Group, NumberInput, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { numberInputValue } from "../../../lib/numberInput";
import { useGuardarDesglose } from "../api";
import type { DesgloseDestino } from "../types";

const pesos = (n: number) => `$${n.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function DesglosePrecio({
  servicioId,
  items,
  subtotal,
  onUsarSuma,
}: {
  servicioId: string;
  items: DesgloseDestino[];
  subtotal: number | null;
  onUsarSuma: (suma: number) => void;
}) {
  const guardar = useGuardarDesglose(servicioId);
  // Montos que se están tecleando, para que la suma se actualice antes de guardar.
  const [editados, setEditados] = useState<Record<string, number | null>>({});

  if (items.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        El servicio no tiene destinos.
      </Text>
    );
  }

  const monto = (d: DesgloseDestino) =>
    d.viaje_id in editados ? editados[d.viaje_id] : d.monto != null ? Number(d.monto) : null;
  const montos = items.map(monto);
  const completo = montos.every((m) => m != null);
  const suma = montos.reduce<number>((a, m) => a + (m ?? 0), 0);
  const diferencia = subtotal != null ? Math.round((suma - subtotal) * 100) / 100 : null;

  function guardarMonto(d: DesgloseDestino, valor: number | null) {
    const anterior = d.monto != null ? Number(d.monto) : null;
    if (valor === anterior) return;
    guardar.mutate([{ viaje_id: d.viaje_id, monto: valor }], {
      onSuccess: () =>
        setEditados(({ [d.viaje_id]: _quitado, ...resto }) => resto),
    });
  }

  return (
    <Stack gap="xs">
      <Text size="xs" c="dimmed">
        Cuánto se cobra por cada destino. Se envía al cliente como tabla en el correo de la factura y debe
        sumar el subtotal.
      </Text>
      {items.map((d) => (
        <Group key={`${d.viaje_id}-${d.monto}`} gap="xs" wrap="nowrap" justify="space-between">
          <Text size="sm" lineClamp={2} style={{ flex: 1, minWidth: 0 }}>
            {d.destino}
          </Text>
          <NumberInput
            w={150}
            prefix="$"
            thousandSeparator=","
            decimalScale={2}
            min={0}
            aria-label={`Monto de ${d.destino}`}
            placeholder="0.00"
            defaultValue={d.monto != null ? Number(d.monto) : undefined}
            onChange={(v) => setEditados((e) => ({ ...e, [d.viaje_id]: numberInputValue(v) }))}
            onBlur={(e) => guardarMonto(d, numberInputValue(e.currentTarget.value.replace(/[^\d.]/g, "")))}
          />
        </Group>
      ))}
      <Group justify="space-between" wrap="wrap" gap="xs">
        <Text size="sm" fw={600}>
          Suma {pesos(suma)}
        </Text>
        {completo && diferencia != null && diferencia !== 0 && (
          <Group gap="xs" wrap="wrap">
            <Text size="sm" c="var(--el-warning-text)">
              {diferencia > 0 ? "Sobran" : "Faltan"} {pesos(Math.abs(diferencia))} para el subtotal
            </Text>
            <Button size="compact-xs" variant="light" onClick={() => onUsarSuma(suma)}>
              Usar la suma como subtotal
            </Button>
          </Group>
        )}
        {completo && diferencia === 0 && (
          <Text size="sm" c="var(--el-success-text)">
            Cuadra con el subtotal
          </Text>
        )}
      </Group>
    </Stack>
  );
}
