import { Text, Title } from "@mantine/core";
import { Card } from "../../components/Card";

export function DashboardPage() {
  return (
    <Card>
      <Title order={3}>Dashboard</Title>
      <Text c="dimmed" mt="xs">
        Fase 0 — andamiaje. El dashboard real (ingresos, pendientes) llega en Fase 5.
      </Text>
    </Card>
  );
}
