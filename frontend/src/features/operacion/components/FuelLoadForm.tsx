// `05-ui-spec §5 FuelLoadForm` — una o más cargas de gasolina; con dos de los tres
// valores se calcula el tercero; avisa si los tres capturados no cuadran (±$1.00).
import { ActionIcon, Alert, Button, FileButton, Group, NumberInput, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconPlus, IconTrash, IconUpload } from "@tabler/icons-react";
import { numberInputValue } from "../../../lib/numberInput";
import { type CargaDraft, nuevaCargaDraft } from "../types";

function calcularFaltante(c: CargaDraft): Partial<CargaDraft> {
  const { litros, precioLitro, importe } = c;
  const presentes = [litros, precioLitro, importe].filter((v) => v !== null).length;
  if (presentes !== 2) return {};
  if (litros === null) return { litros: importe! / precioLitro! };
  if (precioLitro === null) return { precioLitro: importe! / litros! };
  if (importe === null) return { importe: litros! * precioLitro! };
  return {};
}

function noCuadra(c: CargaDraft): boolean {
  if (c.litros === null || c.precioLitro === null || c.importe === null) return false;
  return Math.abs(c.litros * c.precioLitro - c.importe) > 1;
}

export function FuelLoadForm({
  cargas,
  onChange,
}: {
  cargas: CargaDraft[];
  onChange: (cargas: CargaDraft[]) => void;
}) {
  function actualizar(id: string, patch: Partial<CargaDraft>) {
    onChange(
      cargas.map((c) => {
        if (c.id !== id) return c;
        const actualizada = { ...c, ...patch };
        return { ...actualizada, ...calcularFaltante(actualizada) };
      }),
    );
  }

  function quitar(id: string) {
    onChange(cargas.filter((c) => c.id !== id));
  }

  const totalLitros = cargas.reduce((acc, c) => acc + (c.litros ?? 0), 0);
  const totalImporte = cargas.reduce((acc, c) => acc + (c.importe ?? 0), 0);

  return (
    <Stack gap="sm">
      {cargas.map((c) => (
        <Stack key={c.id} gap={6} p="sm" style={{ border: "1px solid var(--el-line)", borderRadius: 10 }}>
          <Group grow>
            <NumberInput
              label="Litros"
              decimalScale={2}
              value={c.litros ?? undefined}
              onChange={(v) => actualizar(c.id, { litros: numberInputValue(v) })}
            />
            <NumberInput
              label="Precio por litro"
              prefix="$"
              decimalScale={3}
              value={c.precioLitro ?? undefined}
              onChange={(v) => actualizar(c.id, { precioLitro: numberInputValue(v) })}
            />
            <NumberInput
              label="Importe"
              prefix="$"
              decimalScale={2}
              value={c.importe ?? undefined}
              onChange={(v) => actualizar(c.id, { importe: numberInputValue(v) })}
            />
            <ActionIcon
              variant="subtle"
              color="red"
              aria-label="Quitar carga"
              onClick={() => quitar(c.id)}
              mt={24}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
          {noCuadra(c) && (
            <Alert color="yellow" icon={<IconAlertTriangle size={14} />} py={6}>
              Litros × precio no cuadra con el importe (diferencia mayor a $1.00).
            </Alert>
          )}
          <FileButton onChange={(file) => actualizar(c.id, { ticket: file })} accept="image/*">
            {(props) => (
              <Button variant="subtle" size="xs" leftSection={<IconUpload size={14} />} {...props}>
                {c.ticket ? c.ticket.name : "Foto del ticket (opcional)"}
              </Button>
            )}
          </FileButton>
        </Stack>
      ))}

      <Button
        variant="default"
        size="xs"
        leftSection={<IconPlus size={14} />}
        onClick={() => onChange([...cargas, nuevaCargaDraft()])}
      >
        Agregar otra carga
      </Button>

      {cargas.length > 0 && (
        <Group justify="flex-end" gap="md">
          <Text size="sm" c="dimmed">
            Total: {totalLitros.toFixed(2)} L
          </Text>
          <Text size="sm" fw={700}>
            ${totalImporte.toFixed(2)}
          </Text>
        </Group>
      )}
    </Stack>
  );
}
