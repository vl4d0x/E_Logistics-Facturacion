// `fase-1-catalogos.md` H1.2 — CRUD de operadores + su acceso a la app.
import { Alert, Badge, Button, Divider, Drawer, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Card } from "../../components/Card";
import { type ActivoFiltro, operadoresApi } from "./api";
import { AccesoOperadorSection } from "./components/AccesoOperadorSection";
import { CatalogToolbar } from "./components/CatalogToolbar";
import { RowActionsMenu } from "./components/RowActionsMenu";
import { SmartDeleteDialog } from "./components/SmartDeleteDialog";
import type { Operador, OperadorPayload } from "./types";

function OperadorForm({
  operador,
  onCancel,
  onSaved,
}: {
  operador: Operador | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const crear = operadoresApi.useCreate();
  const editar = operadoresApi.useUpdate();

  const form = useForm<OperadorPayload>({
    initialValues: operador
      ? {
          nombre: operador.nombre,
          rfc: operador.rfc,
          num_licencia: operador.num_licencia,
          telefono: operador.telefono ?? "",
        }
      : { nombre: "", rfc: "", num_licencia: "", telefono: "" },
    validate: {
      nombre: (v) => (v.trim() ? null : "Requerido"),
      rfc: (v) =>
        /^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/.test(v.trim().toUpperCase())
          ? null
          : "RFC inválido (12 o 13 caracteres del SAT)",
      num_licencia: (v) => (v.trim() ? null : "Requerido"),
    },
  });

  const saving = crear.isPending || editar.isPending;

  function handleSubmit(values: OperadorPayload) {
    const payload = { ...values, telefono: values.telefono || null };
    const onSuccess = { onSuccess: onSaved };
    if (operador) {
      editar.mutate({ id: operador.id, payload }, onSuccess);
    } else {
      crear.mutate(payload, onSuccess);
    }
  }

  return (
    <Stack gap="lg">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="md">
          <TextInput label="Nombre completo" required {...form.getInputProps("nombre")} />
          <Group grow>
            <TextInput
              label="RFC"
              required
              {...form.getInputProps("rfc")}
              onChange={(e) => form.setFieldValue("rfc", e.currentTarget.value.toUpperCase())}
            />
            <TextInput label="Número de licencia" required {...form.getInputProps("num_licencia")} />
          </Group>
          <TextInput label="Teléfono" {...form.getInputProps("telefono")} />

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

      {operador && (
        <>
          <Divider label="Acceso a la app" labelPosition="left" />
          <AccesoOperadorSection operadorId={operador.id} />
        </>
      )}
    </Stack>
  );
}

export function OperadoresPage() {
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [q, setQ] = useState("");
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [editando, setEditando] = useState<Operador | null>(null);
  const [eliminando, setEliminando] = useState<Operador | null>(null);

  const { data, isLoading, isError } = operadoresApi.useList(activo, q);
  const uso = operadoresApi.useUso(eliminando?.id ?? null);
  const eliminar = operadoresApi.useDelete();
  const restaurar = operadoresApi.useRestore();

  return (
    <Card>
      <CatalogToolbar
        q={q}
        onQChange={setQ}
        activo={activo}
        onActivoChange={setActivo}
        onNuevo={() => {
          setEditando(null);
          setDrawerAbierto(true);
        }}
        nuevoLabel="Nuevo operador"
        placeholder="Buscar por nombre o RFC…"
      />

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar los operadores.
        </Alert>
      )}

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>RFC</Table.Th>
            <Table.Th>Licencia</Table.Th>
            <Table.Th>Teléfono</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data?.items.map((operador) => (
            <Table.Tr key={operador.id}>
              <Table.Td>{operador.nombre}</Table.Td>
              <Table.Td>{operador.rfc}</Table.Td>
              <Table.Td>{operador.num_licencia}</Table.Td>
              <Table.Td>{operador.telefono ?? "—"}</Table.Td>
              <Table.Td>
                <Badge color={operador.activo ? "green" : "gray"} variant="light">
                  {operador.activo ? "Activo" : "Archivado"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <RowActionsMenu
                  activo={operador.activo}
                  onEditar={() => {
                    setEditando(operador);
                    setDrawerAbierto(true);
                  }}
                  onEliminar={() => setEliminando(operador)}
                  onRestaurar={() => restaurar.mutate(operador.id)}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {!isLoading && data?.items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin operadores {activo === "false" ? "archivados" : "registrados"}.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title={editando ? editando.nombre : "Nuevo operador"}
        position="right"
        size="lg"
      >
        <OperadorForm
          operador={editando}
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
    </Card>
  );
}
