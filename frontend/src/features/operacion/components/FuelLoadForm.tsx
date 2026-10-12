// `05-ui-spec §5 FuelLoadForm` — una o más cargas de gasolina. Con dos de los tres valores
// se calcula el tercero y se SIGUE recalculando si cambian los otros dos; si el operador
// escribe el valor calculado, queda manual (el ticket puede variar por redondeos) y solo se
// avisa si no cuadra, sin bloquear.
import { pesos } from "../../../lib/money";
import { ActionIcon, Alert, Button, FileButton, Group, NumberInput, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconPlus, IconTrash, IconUpload } from "@tabler/icons-react";
import { numberInputValue } from "../../../lib/numberInput";
import { type CargaDraft, nuevaCargaDraft } from "../types";

type Campo = "litros" | "precioLitro" | "importe";
const CAMPOS: Campo[] = ["litros", "precioLitro", "importe"];

function redondear(valor: number, decimales: number): number {
  const f = 10 ** decimales;
  return Math.round(valor * f) / f;
}

function recalcular(c: CargaDraft, editado: Campo): CargaDraft {
  // Si el operador escribe el campo que se había calculado, ese valor ya es suyo.
  let objetivo: Campo | null = c.calculado === editado ? null : (c.calculado ?? null);
  if (!objetivo && c.calculado !== editado) {
    const faltan = CAMPOS.filter((k) => c[k] === null);
    if (faltan.length === 1) objetivo = faltan[0];
  }
  if (!objetivo) return { ...c, calculado: null };
  const { litros, precioLitro, importe } = c;
  let valor: number | null = null;
  if (objetivo === "litros" && importe && precioLitro) valor = redondear(importe / precioLitro, 2);
  if (objetivo === "precioLitro" && importe && litros) valor = redondear(importe / litros, 3);
  if (objetivo === "importe" && litros && precioLitro) valor = redondear(litros * precioLitro, 2);
  if (valor === null) return { ...c, calculado: c.calculado === objetivo ? objetivo : null };
  return { ...c, [objetivo]: valor, calculado: objetivo };
}

function noCuadra(c: CargaDraft): boolean {
  if (c.calculado) return false;
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
  function actualizar(id: string, patch: Partial<CargaDraft>, editado?: Campo) {
    onChange(
      cargas.map((c) => {
        if (c.id !== id) return c;
        const actualizada = { ...c, ...patch };
        return editado ? recalcular(actualizada, editado) : actualizada;
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
              description={c.calculado === "litros" ? "Calculado" : undefined}
              onChange={(v) => actualizar(c.id, { litros: numberInputValue(v) }, "litros")}
            />
            <NumberInput
              label="Precio por litro"
              prefix="$"
              decimalScale={3}
              value={c.precioLitro ?? undefined}
              description={c.calculado === "precioLitro" ? "Calculado" : undefined}
              onChange={(v) => actualizar(c.id, { precioLitro: numberInputValue(v) }, "precioLitro")}
            />
            <NumberInput
              label="Importe"
              prefix="$"
              decimalScale={2}
              value={c.importe ?? undefined}
              description={c.calculado === "importe" ? "Calculado (puedes corregirlo con el ticket)" : undefined}
              onChange={(v) => actualizar(c.id, { importe: numberInputValue(v) }, "importe")}
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
              Litros × precio no cuadra con el importe (más de $1.00 de diferencia). Revisa el ticket; si está bien, puedes continuar.
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
            {pesos(totalImporte)}
          </Text>
        </Group>
      )}
    </Stack>
  );
}
