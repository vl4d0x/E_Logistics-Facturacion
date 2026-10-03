// `05-ui-spec §5 AcuseViewer` — versión simplificada para la primera entrega de H4.4
// (zoom/rotar/miniaturas de varias páginas quedan para una siguiente pasada).
import { Badge, Image, Stack, Tabs, Text } from "@mantine/core";
import type { AcuseFacturar, Ubicacion } from "../types";

export function AcuseViewerSimple({
  acuses,
  ubicaciones,
  modoAnticipado,
}: {
  acuses: AcuseFacturar[];
  ubicaciones: Ubicacion[];
  modoAnticipado: boolean;
}) {
  const destinos = ubicaciones.filter((u) => u.tipo === "Destino");

  if (modoAnticipado) {
    return (
      <Text size="sm" c="dimmed">
        El acuse se agregará cuando termine el servicio.
      </Text>
    );
  }

  if (destinos.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Este servicio no tiene entregas.
      </Text>
    );
  }

  return (
    <Tabs defaultValue={destinos[0].viaje_id}>
      <Tabs.List>
        {destinos.map((d, i) => (
          <Tabs.Tab key={d.viaje_id} value={d.viaje_id}>
            Entrega {i + 1} · {d.lugar.nombre ?? "—"}
          </Tabs.Tab>
        ))}
      </Tabs.List>
      {destinos.map((d) => {
        const propios = acuses.filter((a) => a.viaje_id === d.viaje_id);
        return (
          <Tabs.Panel key={d.viaje_id} value={d.viaje_id} pt="sm">
            {propios.length === 0 ? (
              <Text size="sm" c="dimmed">
                Sin acuse todavía.
              </Text>
            ) : (
              <Stack gap="xs">
                {propios.map((a, i) => (
                  <div key={i}>
                    {a.referencia ? (
                      <Badge size="lg" variant="light">
                        Folio: {a.referencia}
                      </Badge>
                    ) : a.url ? (
                      <Image src={a.url} radius="sm" fit="contain" mah={300} alt="Acuse" />
                    ) : (
                      <Text size="sm" c="dimmed">
                        Acuse subido, sin vista previa disponible.
                      </Text>
                    )}
                  </div>
                ))}
              </Stack>
            )}
          </Tabs.Panel>
        );
      })}
    </Tabs>
  );
}
