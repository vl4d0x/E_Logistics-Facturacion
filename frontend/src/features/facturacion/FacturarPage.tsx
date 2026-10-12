// `05-ui-spec §7.2 Facturar` — pantalla clave: revisar todo precargado, ajustar el
// subtotal en segundos y timbrar con confianza.
import { pesos } from "../../lib/money";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Grid,
  Group,
  Modal,
  Select,
  Skeleton,
  Stack,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconArrowLeft, IconCheck, IconDownload, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { ApiError } from "../../lib/api";
import { descargarFactura } from "../facturas/api";
import { AcuseViewerSimple } from "./components/AcuseViewerSimple";
import { CollapsibleSection } from "./components/CollapsibleSection";
import { DesglosePrecio } from "./components/DesglosePrecio";
import { MercanciasEditable, RutaEditable, UnidadOperadorEditable } from "./components/EdicionFacturar";
import { PriceField } from "./components/PriceField";
import {
  useActualizarFacturacion,
  useFacturacionDetalle,
  useFacturar,
  useGuardarFolio,
  type FacturarResultado,
} from "./api";

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
  const { data: detalle, isLoading, refetch } = useFacturacionDetalle(id ?? "");
  const actualizar = useActualizarFacturacion(id ?? "");
  const facturar = useFacturar(id ?? "");
  const guardarFolioViaje = useGuardarFolio(id ?? "");

  const [subtotal, setSubtotal] = useState<number | null>(null);
  const [descripcion, setDescripcion] = useState("");
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

  // Folio del cliente por destino: se guarda y, si el concepto es el autogenerado, se refresca.
  function guardarFolio(viajeId: string, folio: string, anterior: string | null) {
    if (folio.trim() === (anterior ?? "")) return;
    guardarFolioViaje.mutate(
      { viajeId, folio },
      {
        onSuccess: async () => {
          const { data } = await refetch();
          if (data?.concepto.descripcion_autogenerada) setDescripcion(data.concepto.descripcion);
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
        // Lo siguiente es descargar o enviar: el detalle de la factura tiene ambas cosas.
        navigate(`/admin/facturas/${res.factura.id}?timbrada=1`);
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
          autoClose: false, // el admin necesita leer qué corregir
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
                      {pesos(detalle.montos?.subtotal ?? "0.10")}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">IVA 16%</Text>
                    <Text size="sm" ff="monospace">
                      {pesos(detalle.montos?.iva_trasladado ?? "0.02")}
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

            {!esCero && (
              <CollapsibleSection
                title="Desglose de precio"
                summary={
                  detalle.desglose_precio.length === 1
                    ? `1 destino · ${detalle.desglose_precio[0].destino}`
                    : `${detalle.desglose_precio.length} destinos · ${
                        detalle.desglose_precio.every((d) => d.monto != null) ? "capturado" : "sin capturar"
                      }`
                }
                forceOpen={campoConError(["desglose"])}
              >
                <DesglosePrecio
                  servicioId={detalle.servicio_id}
                  items={detalle.desglose_precio}
                  subtotal={subtotal}
                  onUsarSuma={(suma) => {
                    setSubtotal(suma);
                    actualizar.mutate({ subtotal: suma });
                  }}
                />
              </CollapsibleSection>
            )}

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
                {detalle.cliente_id && (
                  <Anchor component={Link} to={`/admin/catalogos/clientes/${detalle.cliente_id}`} size="xs">
                    Editar razón social, RFC, CP o régimen fiscal del cliente
                  </Anchor>
                )}
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
                  <Stack gap={6}>
                    <Text size="sm" fw={600}>
                      Folios de {detalle.receptor.razon_social} por destino
                    </Text>
                    <Text size="xs" c="dimmed">
                      Cada destino lleva su folio en el concepto (REF: folio, folio). Corrígelo aquí si está mal.
                    </Text>
                    {detalle.concepto.folios.map((f) => (
                      <Group key={`${f.viaje_id}-${f.folio}`} gap="xs" wrap="nowrap" align="center">
                        <Text size="sm" w={200} truncate>
                          Destino {f.destino}
                        </Text>
                        <TextInput
                          size="xs"
                          placeholder="Folio"
                          defaultValue={f.folio ?? ""}
                          error={!f.folio && errores.some((c) => c.regla === "folio_cliente_presente") ? "Falta el folio" : undefined}
                          onBlur={(e) => guardarFolio(f.viaje_id, e.currentTarget.value, f.folio)}
                        />
                      </Group>
                    ))}
                    {detalle.concepto.folios.length === 0 && (
                      <Text size="sm" c="dimmed">
                        El servicio no tiene destinos.
                      </Text>
                    )}
                  </Stack>
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
              <RutaEditable servicioId={detalle.servicio_id} clienteId={detalle.cliente_id} ubicaciones={detalle.ubicaciones} />
            </CollapsibleSection>

            <CollapsibleSection
              title="Mercancías"
              summary={`${detalle.mercancias.length} partidas · ${detalle.mercancias.reduce((a, m) => a + m.peso_kg, 0)} kg`}
              forceOpen={campoConError(["mercancias"])}
            >
              <MercanciasEditable
                servicioId={detalle.servicio_id}
                clienteId={detalle.cliente_id}
                mercancias={detalle.mercancias}
                ubicaciones={detalle.ubicaciones}
              />
            </CollapsibleSection>

            <CollapsibleSection
              title="Unidad y operador"
              summary={`${detalle.autotransporte.apodo} · ${detalle.figura.nombre}`}
              forceOpen={campoConError(["unidad", "operador"])}
            >
              <UnidadOperadorEditable servicioId={detalle.servicio_id} detalle={detalle} />
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
                    {pesos(detalle.montos?.total)}
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
                    {esCero ? "Timbrar con $0 y cancelar" : "Timbrar factura"} · {pesos(detalle.montos?.total)}
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
            <strong>{pesos(detalle.montos?.total)}</strong> ({detalle.receptor.metodo_pago}). Para corregirla
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
