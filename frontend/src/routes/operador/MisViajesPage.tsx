import { Text, Title } from "@mantine/core";
import { Card } from "../../components/Card";

export function MisViajesPage() {
  return (
    <Card>
      <Title order={4}>Mis viajes</Title>
      <Text c="dimmed" mt="xs">
        Fase 0 — andamiaje. Ver/cerrar viajes (con offline) llega en Fase 2.
      </Text>
    </Card>
  );
}
