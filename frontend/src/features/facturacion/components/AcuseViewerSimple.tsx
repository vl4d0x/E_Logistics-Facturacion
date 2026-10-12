// `05-ui-spec §5 AcuseViewer` — versión simplificada para la primera entrega de H4.4
// (zoom/rotar/miniaturas de varias páginas quedan para una siguiente pasada).
import { Anchor, Badge, Group, Image, Stack, Tabs, Text } from "@mantine/core";
import { ReescaneoControl } from "../../servicios/components/ReescaneoControl";
import type { AcuseFacturar, Ubicacion } from "../types";

export function AcuseViewerSimple({
  servicioId,
  modoAcuse,
  acuses,
  ubicaciones,
  modoAnticipado,
}: {
  servicioId: string;
  modoAcuse: string;
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
            {d.reescaneo ? " ⚠" : ""}
          </Tabs.Tab>
        ))}
      </Tabs.List>
      {destinos.map((d) => {
        const propios = acuses.filter((a) => a.viaje_id === d.viaje_id);
        return (
          <Tabs.Panel key={d.viaje_id} value={d.viaje_id} pt="sm">
            {modoAcuse === "escaneo" && (
              <Group justify="flex-end" mb="xs">
                <ReescaneoControl
                  servicioId={servicioId}
                  viajeId={d.viaje_id}
                  destino={d.lugar.nombre ?? "este destino"}
                  reescaneo={d.reescaneo}
                />
              </Group>
            )}
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
                    ) : a.url && (a.mime === "application/pdf" || /\.pdf($|\?)/i.test(a.url)) ? (
                      <Stack gap={4}>
                        <iframe
                          src={a.url}
                          title={`Acuse de ${d.lugar.nombre ?? "la entrega"}`}
                          style={{ width: "100%", height: 360, border: "1px solid var(--el-line)", borderRadius: 8 }}
                        />
                        <Anchor href={a.url} target="_blank" rel="noreferrer" size="xs">
                          Abrir el acuse en otra pestaña
                        </Anchor>
                      </Stack>
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
