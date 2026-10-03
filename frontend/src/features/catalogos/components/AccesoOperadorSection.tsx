// `fase-1-catalogos.md` H1.2 — sección "Acceso a la app" dentro de la ficha del operador.
import { Badge, Button, Group, Skeleton, Stack, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { useAccesoOperador, useActualizarAcceso, useCrearAcceso } from "../api";

export function AccesoOperadorSection({ operadorId }: { operadorId: string }) {
  const { data: acceso, isLoading } = useAccesoOperador(operadorId);
  const crear = useCrearAcceso(operadorId);
  const actualizar = useActualizarAcceso(operadorId);
  const [mostrarRestablecer, setMostrarRestablecer] = useState(false);

  const formAlta = useForm({
    initialValues: { email: "", password_temporal: "" },
    validate: {
      email: (v) => (v.trim() ? null : "Requerido"),
      password_temporal: (v) => (v.length >= 6 ? null : "Mínimo 6 caracteres"),
    },
  });

  const formRestablecer = useForm({
    initialValues: { password_temporal: "" },
    validate: { password_temporal: (v) => (v.length >= 6 ? null : "Mínimo 6 caracteres") },
  });

  if (isLoading) return <Skeleton height={80} />;

  if (!acceso) {
    return (
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          Este operador todavía no tiene acceso a la app.
        </Text>
        <form
          onSubmit={formAlta.onSubmit((values) =>
            crear.mutate(values, { onSuccess: () => formAlta.reset() }),
          )}
        >
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="Usuario o correo"
              placeholder="usuario o correo@ejemplo.mx"
              {...formAlta.getInputProps("email")}
            />
            <TextInput
              label="Contraseña temporal"
              {...formAlta.getInputProps("password_temporal")}
            />
            <Button type="submit" loading={crear.isPending}>
              Dar acceso
            </Button>
          </Group>
        </form>
      </Stack>
    );
  }

  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <div>
          <Text size="sm" fw={600}>
            {acceso.email}
          </Text>
          <Badge color={acceso.activo ? "green" : "gray"} variant="light" mt={4}>
            {acceso.activo ? "Acceso activo" : "Acceso desactivado"}
          </Badge>
        </div>
        <Group>
          <Button variant="default" size="xs" onClick={() => setMostrarRestablecer((v) => !v)}>
            Restablecer contraseña
          </Button>
          <Button
            variant="default"
            color={acceso.activo ? "red" : "green"}
            size="xs"
            loading={actualizar.isPending}
            onClick={() => actualizar.mutate({ activo: !acceso.activo })}
          >
            {acceso.activo ? "Desactivar acceso" : "Reactivar acceso"}
          </Button>
        </Group>
      </Group>

      {mostrarRestablecer && (
        <form
          onSubmit={formRestablecer.onSubmit((values) =>
            actualizar.mutate(values, {
              onSuccess: () => {
                formRestablecer.reset();
                setMostrarRestablecer(false);
              },
            }),
          )}
        >
          <Group align="flex-end">
            <TextInput
              label="Contraseña temporal nueva"
              {...formRestablecer.getInputProps("password_temporal")}
            />
            <Button type="submit" loading={actualizar.isPending}>
              Guardar
            </Button>
          </Group>
        </form>
      )}
    </Stack>
  );
}
