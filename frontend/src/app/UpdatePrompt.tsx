// Aviso de versión nueva: tras un deploy la app (PWA) seguía mostrando la versión anterior
// guardada en caché. Revisa cada minuto si hay una nueva y ofrece actualizar con un clic,
// sin recargar sola (para no perder un formulario a medio llenar).
import { Button, Group, Paper, Text } from "@mantine/core";
import { useRegisterSW } from "virtual:pwa-register/react";

const CADA_MINUTO = 60_000;

export function UpdatePrompt() {
  const {
    needRefresh: [hayVersionNueva, setHayVersionNueva],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registro) {
      if (registro) setInterval(() => void registro.update(), CADA_MINUTO);
    },
  });

  if (!hayVersionNueva) return null;
  return (
    <Paper
      shadow="md"
      radius="md"
      p="sm"
      withBorder
      style={{ position: "fixed", bottom: 16, right: 16, left: 16, maxWidth: 420, marginLeft: "auto", zIndex: 1000 }}
    >
      <Text size="sm" fw={600}>
        Hay una versión nueva de la app
      </Text>
      <Text size="xs" c="dimmed">
        Guarda lo que estés capturando y actualiza para ver los últimos cambios.
      </Text>
      <Group justify="flex-end" mt="xs" gap="xs">
        <Button size="xs" variant="subtle" onClick={() => setHayVersionNueva(false)}>
          Después
        </Button>
        <Button size="xs" onClick={() => void updateServiceWorker(true)}>
          Actualizar
        </Button>
      </Group>
    </Paper>
  );
}
