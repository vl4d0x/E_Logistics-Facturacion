// `05-ui-spec §5 OperatorReportCard` — solo lectura, en el detalle del servicio (admin).
import { Badge, Divider, Group, Image, SimpleGrid, Stack, Table, Text } from "@mantine/core";
import { IconCheck, IconX } from "@tabler/icons-react";
import { Card } from "../../../components/Card";
import type { ServicioDetalle } from "../../servicios/types";
import { ETIQUETAS_CHECKLIST } from "../types";
import { FuelGauge } from "./FuelGauge";

export function OperatorReportCard({ servicio }: { servicio: ServicioDetalle }) {
  const { inspeccion, cierre, cargas, combustible_total } = servicio;

  if (!inspeccion && !cierre && (!cargas || cargas.length === 0)) {
    return null;
  }

  return (
    <Card>
      <Text fw={600} mb="md">
        Reporte del operador
      </Text>

      {inspeccion && (
        <Stack gap="xs" mb="lg">
          <Group justify="space-between">
            <Text size="sm" fw={600}>
              Inspección de salida
            </Text>
            {!inspeccion.todo_ok && (
              <Badge color="yellow" variant="light">
                {inspeccion.fallas.length} con falla
              </Badge>
            )}
          </Group>
          <SimpleGrid cols={2} spacing={4}>
            {(Object.keys(ETIQUETAS_CHECKLIST) as (keyof typeof ETIQUETAS_CHECKLIST)[]).map((key) => {
              const ok = !inspeccion.fallas.includes(key);
              return (
                <Group key={key} gap={6}>
                  {ok ? (
                    <IconCheck size={14} color="var(--el-success-text)" />
                  ) : (
                    <IconX size={14} color="var(--el-warning-text)" />
                  )}
                  <Text size="xs" c={ok ? undefined : "var(--el-warning-text)"}>
                    {ETIQUETAS_CHECKLIST[key]}
                  </Text>
                </Group>
              );
            })}
          </SimpleGrid>
          {inspeccion.observaciones && (
            <Text size="xs" c="dimmed">
              Observaciones: {inspeccion.observaciones}
            </Text>
          )}
          <Group align="flex-start" mt="xs">
            <div>
              <Text size="xs" c="dimmed" mb={4}>
                Gasolina al salir
              </Text>
              <FuelGauge
                tipoMedidor={servicio.unidad.tipo_medidor as "aguja" | "barras"}
                numBarras={servicio.unidad.num_barras}
                lectura={inspeccion.lectura_medidor}
                readonly
              />
            </div>
            {inspeccion.odometro_km != null && (
              <Text size="xs" c="dimmed">
                Odómetro: {inspeccion.odometro_km.toLocaleString("es-MX")} km
              </Text>
            )}
          </Group>
        </Stack>
      )}

      {cierre && (
        <>
          <Divider mb="md" />
          <Stack gap="xs" mb="lg">
            <Text size="sm" fw={600}>
              Cierre del servicio
            </Text>
            <Table verticalSpacing={4}>
              <Table.Tbody>
                {servicio.viajes.map((v) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>
                      Viaje {v.orden} · {v.tipo === "entrega" ? v.destino?.nombre : v.origen?.nombre}
                    </Table.Td>
                    <Table.Td ta="right">{v.km_reportado != null ? `${v.km_reportado} km` : "—"}</Table.Td>
                  </Table.Tr>
                ))}
                <Table.Tr>
                  <Table.Td fw={700}>Total</Table.Td>
                  <Table.Td ta="right" fw={700}>
                    {servicio.viajes.reduce((acc, v) => acc + (v.km_reportado ?? 0), 0)} km
                  </Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
            {cierre.odometro_km != null && (
              <Text size="xs" c="dimmed">
                Odómetro al llegar: {cierre.odometro_km.toLocaleString("es-MX")} km
                {inspeccion?.odometro_km != null &&
                  ` · Recorrido: ${cierre.odometro_km - inspeccion.odometro_km} km`}
              </Text>
            )}
            <div>
              <Text size="xs" c="dimmed" mb={4}>
                Gasolina al llegar
              </Text>
              <FuelGauge
                tipoMedidor={servicio.unidad.tipo_medidor as "aguja" | "barras"}
                numBarras={servicio.unidad.num_barras}
                lectura={cierre.lectura_medidor}
                readonly
              />
            </div>
          </Stack>
        </>
      )}

      {cargas && cargas.length > 0 && (
        <>
          <Divider mb="md" />
          <Stack gap="xs">
            <Text size="sm" fw={600}>
              Cargas de combustible
            </Text>
            {cargas.map((c) => (
              <Group key={c.id as string} justify="space-between">
                <Group gap="xs">
                  {c.ticket_url && (
                    <Image src={c.ticket_url} w={32} h={32} radius={4} fit="cover" alt="Ticket" />
                  )}
                  <Text size="sm">
                    {c.litros} L · ${c.precio_litro}/L
                  </Text>
                </Group>
                <Text size="sm" fw={600}>
                  ${c.importe}
                </Text>
              </Group>
            ))}
            {combustible_total && (
              <Group justify="flex-end">
                <Text size="sm" fw={700}>
                  Total: {combustible_total.litros} L · ${combustible_total.importe}
                </Text>
              </Group>
            )}
          </Stack>
        </>
      )}
    </Card>
  );
}
