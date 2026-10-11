// Carga los km por destino desde el Excel de Carta Porte (una hoja por cliente).
// El km de cada destino se sugiere al armar un servicio; sin km se usan 70 "no confirmado".
import { Alert, Button, FileButton, Group, List, Stack, Text } from "@mantine/core";
import { IconFileSpreadsheet } from "@tabler/icons-react";
import { useImportarKm } from "../api";

export function ImportarKmCard() {
  const importar = useImportarKm();
  const resultado = importar.data;

  return (
    <Stack gap="xs" mb="md">
      <Group justify="space-between" wrap="wrap">
        <div>
          <Text fw={600}>Kilómetros por destino</Text>
          <Text size="sm" c="dimmed">
            Sube el Excel de Carta Porte para cargar el km de cada destino. Los destinos sin km usan
            70 km marcados como “no confirmado”.
          </Text>
        </div>
        <FileButton onChange={(f) => f && importar.mutate(f)} accept=".xlsx">
          {(props) => (
            <Button
              {...props}
              variant="default"
              leftSection={<IconFileSpreadsheet size={16} />}
              loading={importar.isPending}
            >
              Importar km (Excel)
            </Button>
          )}
        </FileButton>
      </Group>
      {resultado && (
        <Alert color="green" title="Importación terminada">
          <List size="sm" spacing={2}>
            {resultado.hojas.map((h) => (
              <List.Item key={h.hoja}>
                <strong>{h.cliente}</strong>: {h.actualizados} con km
                {h.sin_km > 0 && `, ${h.sin_km} sin km en el Excel`}
                {h.sin_lugar.length > 0 &&
                  `, ${h.sin_lugar.length} no están en Lugares (${h.sin_lugar.slice(0, 5).join(", ")}${
                    h.sin_lugar.length > 5 ? "…" : ""
                  })`}
              </List.Item>
            ))}
          </List>
          {resultado.hojas_sin_cliente.length > 0 && (
            <Text size="sm" mt="xs">
              Hojas sin cliente en el sistema: {resultado.hojas_sin_cliente.join(", ")}
            </Text>
          )}
        </Alert>
      )}
    </Stack>
  );
}
