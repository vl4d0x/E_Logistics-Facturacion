// `05-ui-spec §7.2 Facturar` — pantalla clave: revisar todo precargado, ajustar el
// subtotal en segundos y timbrar con confianza.
import {
  Alert,
  Badge,
  Button,
  Grid,
  Group,
  Modal,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconArrowLeft, IconCheck, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { ApiError } from "../../lib/api";
import { AcuseViewerSimple } from "./components/AcuseViewerSimple";
import { CollapsibleSection } from "./components/CollapsibleSection";
import { PriceField } from "./components/PriceField";
import { useActualizarFacturacion, useFacturacionDetalle, useFacturar } from "./api";

const USO_CFDI_OPCIONES = [
  { value: "G03", label: "G03 · Gastos en general" },
  { value: "G01", label: "G01 · Adquisición de mercancías" },
  { value: "P01", label: "P01 · Por definir" },
];
const METODO_PAGO_OPCIONES = [
  { value: "PPD", label: "PPD · Pago en parcialidades o diferido" },
  { value: "PUE", label: "PUE · Pago en una sola exhibición" },
];

function NivelIcon({ nivel }: { nivel: "ok" | "warning" | "error" }) {
  if (nivel === "ok") return <IconCheck size={14} color="var(--el-success-text)" />;
  if (nivel === "warning") return <IconAlertTriangle size={14} color="var(--el-warning-text)" />;
  return <IconX size={14} color="var(--el-red)" />;
}

export function FacturarPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: detalle, isLoading } = useFacturacionDetalle(id ?? "");
  const actualizar = useActualizarFacturacion(id ?? "");
  const facturar = useFacturar(id ?? "");

  const [subtotal, setSubtotal] = useState<number | null>(null);
  const [descripcion, setDescripcion] = useState("");
  const [confirmarAbierto, setConfirmarAbierto] = useState(false);
  const [checksAbierto, setChecksAbierto] = useState(false);
  const [cargadoPara, setCargadoPara] = useState<string | null>(null);

  if (detalle && detalle.servicio_id !== cargadoPara) {
    setCargadoPara(detalle.servicio_id);
    setSubtotal(
      detalle.montos
        ? Number(detalle.montos.subtotal)
        : detalle.precio_sugerido.monto
          ? Number(detalle.precio_sugerido.monto)
          : null,
    );
    setDescripcion(detalle.concepto.descripcion);
  }

  if (isLoading || !detalle) return <Skeleton height={400} />;

  const errores = detalle.validacion.checks.filter((c) => c.nivel === "error");
  const warnings = detalle.validacion.checks.filter((c) => c.nivel === "warning");
  const oks = detalle.validacion.checks.filter((c) => c.nivel === "ok");
  const campoConError = (campos: string[]) => errores.some((e) => e.campo && campos.includes(e.campo));

  function guardarSubtotal() {
    if (subtotal != null) actualizar.mutate({ subtotal });
  }

  function guardarDescripcion(valor: string | null) {
    setDescripcion(valor ?? detalle!.concepto.descripcion);
    actualizar.mutate({ descripcion_concepto: valor });
  }

  function confirmarTimbrado() {
    const total = detalle!.montos?.total;
    if (!total) return;
    facturar.mutate(total, {
      onSuccess: () => {
        notifications.show({ color: "green", message: "Factura timbrada" });
        setConfirmarAbierto(false);
        navigate(`/admin/servicios/${id}`);
      },
      onError: (err) => {
        setConfirmarAbierto(false);
        if (err instanceof ApiError && err.code === "facturama_no_configurado") {
          notifications.show({
            color: "yellow",
            title: "Timbrado pendiente",
            message: err.message,
            autoClose: 8000,
          });
          return;
        }
        if (err instanceof ApiError && err.code === "no_implementado") {
          notifications.show({
            color: "yellow",
            title: "Todavía no disponible",
            message: "El timbrado real se activa en cuanto estén las credenciales de Facturama.",
            autoClose: 8000,
          });
          return;
        }
        notifications.show({
          color: "red",
          title: "No se pudo timbrar",
          message: err instanceof ApiError ? err.message : "Error inesperado",
        });
      },
    });
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => navigate(`/admin/servicios/${id}`)}
          px={0}
        >
          Volver al servicio
        </Button>
        {detalle.modo === "anticipado" && (
          <Badge color="blue" variant="light">
            Anticipada
          </Badge>
        )}
      </Group>

      {detalle.modo === "anticipado" && (
        <Alert color="blue" icon={<IconAlertTriangle size={16} />}>
          Timbrado anticipado: se usan las fechas programadas y no se pide acuse.
        </Alert>
      )}

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Stack gap="md">
            <Card>
              <PriceField
                subtotal={subtotal}
                onChange={setSubtotal}
                onCommit={guardarSubtotal}
                regimenReceptor={detalle.receptor.regimen_receptor}
                precioSugerido={detalle.precio_sugerido}
              />
            </Card>

            <CollapsibleSection
              title="Receptor y pago"
              summary={`${detalle.receptor.razon_social} · ${detalle.receptor.uso_cfdi} · ${detalle.receptor.metodo_pago} · ${detalle.receptor.forma_pago}`}
              forceOpen={campoConError(["cliente"])}
            >
              <Stack gap="xs">
                <Text size="sm">
                  {detalle.receptor.razon_social} · RFC {detalle.receptor.rfc}
                </Text>
                <Text size="sm" c="dimmed">
                  CP fiscal {detalle.receptor.cp_fiscal} · Régimen {detalle.receptor.regimen_fiscal}
                </Text>
                <Group grow>
                  <Select
                    label="Uso CFDI"
                    data={USO_CFDI_OPCIONES}
                    value={detalle.receptor.uso_cfdi}
                    onChange={(v) => v && actualizar.mutate({ uso_cfdi: v })}
                  />
                  <Select
                    label="Método de pago"
                    data={METODO_PAGO_OPCIONES}
                    value={detalle.receptor.metodo_pago}
                    onChange={(v) => v && actualizar.mutate({ metodo_pago: v })}
                  />
                </Group>
              </Stack>
            </CollapsibleSection>

            <CollapsibleSection
              title="Concepto"
              summary={detalle.concepto.descripcion.split("\n")[0]}
            >
              <Stack gap="xs">
                <Textarea
                  autosize
                  minRows={4}
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.currentTarget.value)}
                  onBlur={() => actualizar.mutate({ descripcion_concepto: descripcion })}
                />
                {!detalle.concepto.descripcion_autogenerada && (
                  <Button variant="subtle" size="compact-xs" onClick={() => guardarDescripcion(null)}>
                    Regenerar
                  </Button>
                )}
              </Stack>
            </CollapsibleSection>

            <CollapsibleSection
              title="Ruta y ubicaciones"
              summary={`${detalle.ubicaciones.length} ubicaciones`}
              forceOpen={campoConError(["viajes"])}
            >
              <Table verticalSpacing={4}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Lugar</Table.Th>
                    <Table.Th>CP</Table.Th>
                    <Table.Th>Fecha/hora</Table.Th>
                    <Table.Th>Distancia</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detalle.ubicaciones.map((u) => (
                    <Table.Tr key={u.id_ubicacion}>
                      <Table.Td>{u.tipo}</Table.Td>
                      <Table.Td>{u.lugar.nombre ?? "—"}</Table.Td>
                      <Table.Td>{u.lugar.codigo_postal ?? "—"}</Table.Td>
                      <Table.Td>
                        {u.fecha_hora ? new Date(u.fecha_hora).toLocaleString("es-MX") : "—"}{" "}
                        <Text span size="xs" c="dimmed">
                          ({u.fecha_hora_fuente})
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {u.distancia_km != null ? `${u.distancia_km} km` : "—"}
                        {u.km_reportado != null && u.distancia_km != null && u.km_reportado !== u.distancia_km && (
                          <Badge ml={6} size="xs" variant="light" color="yellow">
                            Operador: {u.km_reportado} km
                          </Badge>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </CollapsibleSection>

            <CollapsibleSection
              title="Mercancías"
              summary={`${detalle.mercancias.length} partidas · ${detalle.mercancias.reduce((a, m) => a + m.peso_kg, 0)} kg`}
              forceOpen={campoConError(["viajes"])}
            >
              <Table verticalSpacing={4}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Descripción</Table.Th>
                    <Table.Th>Clave SAT</Table.Th>
                    <Table.Th>Cantidad</Table.Th>
                    <Table.Th>Peso (kg)</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detalle.mercancias.map((m, i) => (
                    <Table.Tr key={i}>
                      <Table.Td>{m.descripcion}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {m.bienes_transp} / {m.clave_unidad}
                        </Text>
                      </Table.Td>
                      <Table.Td>{Number(m.cantidad)}</Table.Td>
                      <Table.Td>{m.peso_kg}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </CollapsibleSection>

            <CollapsibleSection
              title="Unidad y operador"
              summary={`${detalle.autotransporte.apodo} · ${detalle.figura.nombre}`}
              forceOpen={campoConError(["unidad", "operador"])}
            >
              <Group gap="xs" mb="sm">
                <Badge variant="light">Placa {detalle.autotransporte.placa}</Badge>
                <Badge variant="light">{detalle.autotransporte.config_vehicular}</Badge>
                <Badge variant="light">{detalle.autotransporte.perm_sct}</Badge>
                <Badge variant="light" color={detalle.autotransporte.poliza ? "gray" : "red"}>
                  {detalle.autotransporte.poliza ? `Póliza ${detalle.autotransporte.poliza}` : "Sin póliza"}
                </Badge>
              </Group>
              <Text size="sm">
                {detalle.figura.nombre} · RFC {detalle.figura.rfc} · Lic. {detalle.figura.num_licencia}
              </Text>
            </CollapsibleSection>
          </Stack>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Stack gap="md" style={{ position: "sticky", top: 20 }}>
            <Card>
              <Text fw={600} mb="sm">
                Acuses
              </Text>
              <AcuseViewerSimple
                acuses={detalle.acuses}
                ubicaciones={detalle.ubicaciones}
                modoAnticipado={detalle.modo === "anticipado"}
              />
            </Card>

            <Card>
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text fw={600}>Total</Text>
                  <Text fw={700} size="lg">
                    ${detalle.montos?.total ?? "0.00"}
                  </Text>
                </Group>

                <UnstyledValidacionSummary
                  oks={oks.length}
                  warnings={warnings.length}
                  errores={errores.length}
                  onClick={() => setChecksAbierto((v) => !v)}
                />
                {checksAbierto && (
                  <Stack gap={4}>
                    {[...errores, ...warnings].map((c, i) => (
                      <Group key={i} gap={6} wrap="nowrap" align="flex-start">
                        <NivelIcon nivel={c.nivel} />
                        <Text size="sm">{c.mensaje}</Text>
                      </Group>
                    ))}
                  </Stack>
                )}

                <Tooltip label={errores[0]?.mensaje} disabled={errores.length === 0}>
                  <Button
                    fullWidth
                    size="md"
                    disabled={!detalle.validacion.ok || subtotal == null}
                    onClick={() => setConfirmarAbierto(true)}
                  >
                    Timbrar factura · ${detalle.montos?.total ?? "0.00"}
                  </Button>
                </Tooltip>
                <Button variant="default" fullWidth onClick={() => navigate(`/admin/servicios/${id}`)}>
                  Guardar y salir
                </Button>
              </Stack>
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>

      <Modal opened={confirmarAbierto} onClose={() => setConfirmarAbierto(false)} title="Confirmar timbrado">
        <Stack>
          <Text size="sm">
            Vas a timbrar una factura a <strong>{detalle.receptor.razon_social}</strong> por{" "}
            <strong>${detalle.montos?.total}</strong> ({detalle.receptor.metodo_pago}). Para corregirla
            después habrá que cancelarla ante el SAT.
          </Text>
          {detalle.modo === "anticipado" && (
            <Text size="sm" c="dimmed">
              El servicio aún no se realiza: si cambia el precio, la ruta o la mercancía habrá que
              cancelar esta factura.
            </Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmarAbierto(false)}>
              Cancelar
            </Button>
            <Button loading={facturar.isPending} onClick={confirmarTimbrado}>
              Timbrar
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

function UnstyledValidacionSummary({
  oks,
  warnings,
  errores,
  onClick,
}: {
  oks: number;
  warnings: number;
  errores: number;
  onClick: () => void;
}) {
  return (
    <Group gap={10} style={{ cursor: "pointer" }} onClick={onClick}>
      <Text size="sm" c="dimmed">
        Validación:
      </Text>
      <Group gap={4}>
        <IconCheck size={14} color="var(--el-success-text)" />
        <Text size="sm">{oks}</Text>
      </Group>
      <Group gap={4}>
        <IconAlertTriangle size={14} color="var(--el-warning-text)" />
        <Text size="sm">{warnings}</Text>
      </Group>
      <Group gap={4}>
        <IconX size={14} color="var(--el-red)" />
        <Text size="sm">{errores}</Text>
      </Group>
    </Group>
  );
}
