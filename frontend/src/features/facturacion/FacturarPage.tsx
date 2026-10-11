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
  TextInput,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconArrowLeft, IconCheck, IconDownload, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { ApiError } from "../../lib/api";
import { descargarFactura } from "../facturas/api";
import { AcuseViewerSimple } from "./components/AcuseViewerSimple";
import { CollapsibleSection } from "./components/CollapsibleSection";
import { PriceField } from "./components/PriceField";
import { useActualizarFacturacion, useFacturacionDetalle, useFacturar, type FacturarResultado } from "./api";

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
  const [folioCliente, setFolioCliente] = useState("");
  const [confirmarAbierto, setConfirmarAbierto] = useState(false);
  const [checksAbierto, setChecksAbierto] = useState(false);
  const [cargadoPara, setCargadoPara] = useState<string | null>(null);
  const [resultadoCero, setResultadoCero] = useState<FacturarResultado | null>(null);

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
    setFolioCliente(detalle.concepto.folio_cliente ?? "");
  }

  if (isLoading || !detalle) return <Skeleton height={400} />;

  const esCero = detalle.timbrado_modo === "cero";
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

  function guardarFolioCliente() {
    actualizar.mutate(
      { folio_cliente: folioCliente || null },
      {
        onSuccess: (data) => {
          if (data.concepto.descripcion_autogenerada) setDescripcion(data.concepto.descripcion);
        },
      },
    );
  }

  function confirmarTimbrado() {
    const total = detalle!.montos?.total;
    if (!total) return;
    facturar.mutate(total, {
      onSuccess: (res) => {
        setConfirmarAbierto(false);
        if (esCero) {
          // Se queda aquí para que el admin descargue el PDF y el XML antes de salir.
          setResultadoCero(res);
          return;
        }
        notifications.show({ color: "green", message: "Factura timbrada" });
        navigate(`/admin/servicios/`);
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
              {esCero ? (
                <Stack gap={6}>
                  <Text size="sm" fw={600} c="dimmed">
                    Timbrado sin precio
                  </Text>
                  <Text size="sm">
                    Se timbra con un subtotal simbólico de <strong>$0.10</strong> y la factura se
                    cancela sola (motivo 02). Después podrás descargar el PDF y el XML. El precio real se
                    timbra más adelante.
                  </Text>
                  <Group justify="space-between">
                    <Text size="sm">Subtotal</Text>
                    <Text size="sm" ff="monospace">
                      ${detalle.montos?.subtotal ?? "0.10"}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">IVA 16%</Text>
                    <Text size="sm" ff="monospace">
                      ${detalle.montos?.iva_trasladado ?? "0.02"}
                    </Text>
                  </Group>
                </Stack>
              ) : (
              <PriceField
                subtotal={subtotal}
                onChange={setSubtotal}
                onCommit={guardarSubtotal}
                regimenReceptor={detalle.receptor.regimen_receptor}
                precioSugerido={detalle.precio_sugerido}
              />
              )}
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
              forceOpen={campoConError(["concepto"])}
            >
              <Stack gap="xs">
                {detalle.concepto.requiere_folio && (
                  <TextInput
                    label={`Folio de ${detalle.receptor.razon_social}`}
                    description="Este cliente exige su propio folio dentro del concepto de la factura"
                    value={folioCliente}
                    onChange={(e) => setFolioCliente(e.currentTarget.value)}
                    onBlur={guardarFolioCliente}
                    error={
                      errores.some((c) => c.regla === "folio_cliente_presente")
                        ? "Falta el folio"
                        : undefined
                    }
                  />
                )}
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
          <Stack gap="md" className="el-sticky-aside">
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
                    {esCero ? "Timbrar con $0 y cancelar" : "Timbrar factura"} · ${detalle.montos?.total ?? "0.00"}
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
          {esCero && (
            <Text size="sm" fw={600}>
              Es un timbrado sin precio: la factura se cancelará automáticamente al terminar.
            </Text>
          )}
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

      <Modal
        opened={resultadoCero !== null}
        onClose={() => navigate(`/admin/servicios/${id}`)}
        title="Factura timbrada"
        closeOnClickOutside={false}
      >
        <Stack>
          {resultadoCero?.cancelada_automaticamente ? (
            <Alert color="green" icon={<IconCheck size={16} />}>
              Se timbró con $0.10 y la factura ya se canceló. Descarga los archivos para enviarlos al
              cliente.
            </Alert>
          ) : (
            <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
              La factura se timbró, pero no se pudo cancelar sola
              {resultadoCero?.cancelacion_error ? `: ${resultadoCero.cancelacion_error}` : "."} Descarga los
              archivos y cancélala desde Facturas (motivo 02).
            </Alert>
          )}
          <Group>
            <Button
              variant="default"
              leftSection={<IconDownload size={16} />}
              onClick={() => resultadoCero && descargarFactura(resultadoCero.factura.id, "pdf")}
            >
              Descargar PDF
            </Button>
            <Button
              variant="default"
              leftSection={<IconDownload size={16} />}
              onClick={() => resultadoCero && descargarFactura(resultadoCero.factura.id, "xml")}
            >
              Descargar XML
            </Button>
          </Group>
          <Group justify="flex-end">
            <Button onClick={() => navigate(`/admin/servicios/${id}`)}>Listo</Button>
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
