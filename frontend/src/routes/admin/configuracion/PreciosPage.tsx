// `07-precio-sugerido` — Configuración → Precios y tarifas: tarifario fijo por unidad.
import { Button, Group, NumberInput, Stack, Table, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Card } from "../../../components/Card";
import { api, ApiError } from "../../../lib/api";
import { numberInputValue } from "../../../lib/numberInput";

const TIERS = [
  { key: "saveiro", label: "Saveiro (0.5 ton)" },
  { key: "nissan", label: "Nissan (1 ton)" },
  { key: "ram", label: "Ram (3.5 ton)" },
] as const;

type Tarifa = { cdmx: number; extra: number };
interface Tarifario {
  cliente: string;
  tarifas: Record<(typeof TIERS)[number]["key"], Tarifa>;
}

const CLAVE = "precio.tarifario_cliente";

function useTarifario() {
  return useQuery({
    queryKey: ["configuracion"],
    queryFn: () => api.get<Record<string, unknown>>("/api/v1/configuracion"),
    select: (c) => c[CLAVE] as Tarifario,
  });
}

function useGuardarTarifario() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (valor: Tarifario) => api.patch("/api/v1/configuracion", { [CLAVE]: valor }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["configuracion"] });
      client.invalidateQueries({ queryKey: ["servicios"] });
      notifications.show({ color: "green", message: "Tarifas guardadas" });
    },
    onError: (err) =>
      notifications.show({
        color: "red",
        title: "No se pudo guardar",
        message: err instanceof ApiError ? err.message : "Error inesperado",
      }),
  });
}

export function PreciosPage() {
  const { data } = useTarifario();
  const guardar = useGuardarTarifario();
  const form = useForm<Tarifario>({
    initialValues: {
      cliente: "",
      tarifas: { saveiro: { cdmx: 0, extra: 0 }, nissan: { cdmx: 0, extra: 0 }, ram: { cdmx: 0, extra: 0 } },
    },
    validate: {
      cliente: (v) => (v.trim() ? null : "Requerido"),
    },
  });

  useEffect(() => {
    if (data) form.setValues(data);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  return (
    <Card>
      <form onSubmit={form.onSubmit((values) => guardar.mutate(values))}>
        <Stack gap="md">
          <div>
            <Text fw={600}>Tarifas fijas por cliente</Text>
            <Text size="sm" c="dimmed">
              Subtotal sugerido (antes de IVA) para viajes a CDMX. El primer destino en CDMX se cobra con la
              tarifa de la unidad; cada destino o tiro adicional, con la tarifa adicional.
            </Text>
          </div>
          <TextInput
            label="Aplica al cliente cuyo nombre contiene"
            description="Sin importar mayúsculas, se busca en nombre comercial y razón social."
            required
            maw={320}
            {...form.getInputProps("cliente")}
          />
          <Table verticalSpacing="sm" maw={560}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Unidad</Table.Th>
                <Table.Th>Viaje a CDMX</Table.Th>
                <Table.Th>Cada destino adicional</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {TIERS.map(({ key, label }) => (
                <Table.Tr key={key}>
                  <Table.Td>{label}</Table.Td>
                  {(["cdmx", "extra"] as const).map((campo) => (
                    <Table.Td key={campo}>
                      <NumberInput
                        prefix="$"
                        min={0}
                        decimalScale={2}
                        fixedDecimalScale
                        thousandSeparator=","
                        value={form.values.tarifas[key][campo]}
                        onChange={(v) => form.setFieldValue(`tarifas.${key}.${campo}`, numberInputValue(v) ?? 0)}
                      />
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Group>
            <Button type="submit" loading={guardar.isPending}>
              Guardar tarifas
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}
