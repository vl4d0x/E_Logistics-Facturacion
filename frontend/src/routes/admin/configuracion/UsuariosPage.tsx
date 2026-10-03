// `fase-1-catalogos.md` H1.7 — Configuración → Usuarios (administradores).
import { Alert, Badge, Button, Drawer, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertTriangle, IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { Card } from "../../../components/Card";
import { useActualizarAdmin, useAdmins, useCrearAdmin } from "../../../features/catalogos/api";
import { useAuth } from "../../../lib/useAuth";
import type { UsuarioAdmin } from "../../../features/catalogos/types";

function NuevoAdminForm({ onCancel, onSaved }: { onCancel: () => void; onSaved: () => void }) {
  const crear = useCrearAdmin();
  const form = useForm({
    initialValues: { nombre: "", email: "", password_temporal: "" },
    validate: {
      nombre: (v) => (v.trim() ? null : "Requerido"),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Correo inválido"),
      password_temporal: (v) => (v.length >= 6 ? null : "Mínimo 6 caracteres"),
    },
  });

  return (
    <form onSubmit={form.onSubmit((values) => crear.mutate(values, { onSuccess: onSaved }))}>
      <Stack gap="md">
        <TextInput label="Nombre" required {...form.getInputProps("nombre")} />
        <TextInput label="Correo" required {...form.getInputProps("email")} />
        <TextInput label="Contraseña temporal" required {...form.getInputProps("password_temporal")} />
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="submit" loading={crear.isPending}>
            Crear
          </Button>
        </Group>
      </Stack>
    </form>
  );
}

export function UsuariosPage() {
  const { user } = useAuth();
  const { data: admins, isLoading, isError } = useAdmins();
  const actualizar = useActualizarAdmin();
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [restableciendo, setRestableciendo] = useState<UsuarioAdmin | null>(null);

  const form = useForm({
    initialValues: { password_temporal: "" },
    validate: { password_temporal: (v) => (v.length >= 6 ? null : "Mínimo 6 caracteres") },
  });

  const activos = admins?.filter((a) => a.activo).length ?? 0;

  return (
    <Card>
      <Group justify="space-between" mb="md">
        <Text fw={600}>Administradores</Text>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setDrawerAbierto(true)}>
          Nuevo administrador
        </Button>
      </Group>

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar los administradores.
        </Alert>
      )}

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Correo</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {admins?.map((admin) => {
            const esUnoMismo = admin.id === user?.id;
            const bloquearDesactivar = esUnoMismo || (admin.activo && activos <= 1);
            return (
              <Table.Tr key={admin.id}>
                <Table.Td>
                  {admin.nombre} {esUnoMismo && <Text span c="dimmed" size="xs">(tú)</Text>}
                </Table.Td>
                <Table.Td>{admin.email}</Table.Td>
                <Table.Td>
                  <Badge color={admin.activo ? "green" : "gray"} variant="light">
                    {admin.activo ? "Activo" : "Desactivado"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <Button variant="default" size="xs" onClick={() => setRestableciendo(admin)}>
                      Restablecer contraseña
                    </Button>
                    <Button
                      variant="default"
                      color={admin.activo ? "red" : "green"}
                      size="xs"
                      disabled={admin.activo && bloquearDesactivar}
                      title={
                        admin.activo && esUnoMismo
                          ? "No puedes desactivarte a ti mismo"
                          : admin.activo && activos <= 1
                            ? "No puede quedar el sistema sin administradores activos"
                            : undefined
                      }
                      loading={actualizar.isPending}
                      onClick={() =>
                        actualizar.mutate({ id: admin.id, payload: { activo: !admin.activo } })
                      }
                    >
                      {admin.activo ? "Desactivar" : "Reactivar"}
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>

      {!isLoading && admins?.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin administradores.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title="Nuevo administrador"
        position="right"
      >
        <NuevoAdminForm onCancel={() => setDrawerAbierto(false)} onSaved={() => setDrawerAbierto(false)} />
      </Drawer>

      <Drawer
        opened={restableciendo !== null}
        onClose={() => setRestableciendo(null)}
        title={`Restablecer contraseña — ${restableciendo?.nombre ?? ""}`}
        position="right"
      >
        <form
          onSubmit={form.onSubmit((values) => {
            if (!restableciendo) return;
            actualizar.mutate(
              { id: restableciendo.id, payload: values },
              {
                onSuccess: () => {
                  form.reset();
                  setRestableciendo(null);
                },
              },
            );
          })}
        >
          <Stack gap="md">
            <TextInput label="Contraseña temporal nueva" required {...form.getInputProps("password_temporal")} />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRestableciendo(null)}>
                Cancelar
              </Button>
              <Button type="submit" loading={actualizar.isPending}>
                Guardar
              </Button>
            </Group>
          </Stack>
        </form>
      </Drawer>
    </Card>
  );
}
