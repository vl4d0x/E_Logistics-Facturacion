// `fase-1-catalogos.md` H1.4 — mercancías frecuentes de un cliente.
import { Badge, Button, Drawer, Group, NumberInput, Stack, Table, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import {
  useCreateMercancia,
  useDeleteMercancia,
  useMercanciaUso,
  useMercancias,
  useRestoreMercancia,
  useUpdateMercancia,
} from "../api";
import type { Mercancia, MercanciaPayload } from "../types";
import { RowActionsMenu } from "./RowActionsMenu";
import { SmartDeleteDialog } from "./SmartDeleteDialog";

function MercanciaForm({
  clienteId,
  mercancia,
  onCancel,
  onSaved,
}: {
  clienteId: string;
  mercancia: Mercancia | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const crear = useCreateMercancia(clienteId);
  const editar = useUpdateMercancia(clienteId);

  const form = useForm<MercanciaPayload>({
    initialValues: mercancia
      ? {
          nombre_humano: mercancia.nombre_humano,
          bienes_transp: mercancia.bienes_transp,
          clave_unidad: mercancia.clave_unidad,
          unidad_desc: mercancia.unidad_desc ?? "",
          peso_kg_sugerido: mercancia.peso_kg_sugerido,
        }
      : { nombre_humano: "", bienes_transp: "", clave_unidad: "", unidad_desc: "", peso_kg_sugerido: null },
    validate: {
      nombre_humano: (v) => (v.trim() ? null : "Requerido"),
      bienes_transp: (v) => (v.trim() ? null : "Requerido (clave SAT BienesTransp)"),
      clave_unidad: (v) => (v.trim() ? null : "Requerido (clave SAT ClaveUnidad)"),
    },
  });

  const saving = crear.isPending || editar.isPending;

  function handleSubmit(values: MercanciaPayload) {
    const payload = { ...values, unidad_desc: values.unidad_desc || null };
    if (mercancia) {
      editar.mutate({ id: mercancia.id, payload }, { onSuccess: onSaved });
    } else {
      crear.mutate(payload, { onSuccess: onSaved });
    }
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <TextInput
          label="Nombre"
          description="Lo que ve el operador"
          required
          {...form.getInputProps("nombre_humano")}
        />
        <Group grow>
          <TextInput label="BienesTransp (clave SAT)" required {...form.getInputProps("bienes_transp")} />
          <TextInput label="ClaveUnidad (clave SAT)" required {...form.getInputProps("clave_unidad")} />
        </Group>
        <Group grow>
          <TextInput label="Unidad descriptiva" placeholder="Caja de cartón" {...form.getInputProps("unidad_desc")} />
          <NumberInput label="Peso sugerido (kg)" decimalScale={2} {...form.getInputProps("peso_kg_sugerido")} />
        </Group>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}

export function MercanciasManager({ clienteId }: { clienteId: string }) {
  const { data: mercancias, isLoading } = useMercancias(clienteId);
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [editando, setEditando] = useState<Mercancia | null>(null);
  const [eliminando, setEliminando] = useState<Mercancia | null>(null);

  const uso = useMercanciaUso(eliminando?.id ?? null);
  const eliminar = useDeleteMercancia(clienteId);
  const restaurar = useRestoreMercancia(clienteId);

  return (
    <div>
      <Group justify="flex-end" mb="md">
        <Button
          leftSection={<IconPlus size={16} />}
          onClick={() => {
            setEditando(null);
            setDrawerAbierto(true);
          }}
        >
          Nueva mercancía
        </Button>
      </Group>

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>BienesTransp</Table.Th>
            <Table.Th>ClaveUnidad</Table.Th>
            <Table.Th>Peso sugerido</Table.Th>
            <Table.Th>Estatus</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {mercancias?.map((m) => (
            <Table.Tr key={m.id}>
              <Table.Td>{m.nombre_humano}</Table.Td>
              <Table.Td>{m.bienes_transp}</Table.Td>
              <Table.Td>{m.clave_unidad}</Table.Td>
              <Table.Td>{m.peso_kg_sugerido ? `${m.peso_kg_sugerido} kg` : "—"}</Table.Td>
              <Table.Td>
                <Badge color={m.activo ? "green" : "gray"} variant="light">
                  {m.activo ? "Activa" : "Archivada"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <RowActionsMenu
                  activo={m.activo}
                  onEditar={() => {
                    setEditando(m);
                    setDrawerAbierto(true);
                  }}
                  onEliminar={() => setEliminando(m)}
                  onRestaurar={() => restaurar.mutate(m.id)}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {!isLoading && mercancias?.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin mercancías registradas.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title={editando ? editando.nombre_humano : "Nueva mercancía"}
        position="right"
      >
        <MercanciaForm
          clienteId={clienteId}
          mercancia={editando}
          onCancel={() => setDrawerAbierto(false)}
          onSaved={() => setDrawerAbierto(false)}
        />
      </Drawer>

      <SmartDeleteDialog
        opened={eliminando !== null}
        onClose={() => setEliminando(null)}
        uso={uso.data}
        isLoadingUso={uso.isLoading}
        isDeleting={eliminar.isPending}
        onConfirm={() =>
          eliminando && eliminar.mutate(eliminando.id, { onSuccess: () => setEliminando(null) })
        }
      />
    </div>
  );
}
