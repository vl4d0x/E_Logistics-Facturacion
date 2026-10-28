// `fase-2-servicios.md` H2.3/H2.4 — detalle, cierre desde escritorio, duplicar, cancelar.
import { pesos } from "../../lib/money";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  FileButton,
  Group,
  Menu,
  Modal,
  Skeleton,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconBrandWhatsapp,
  IconCheck,
  IconDotsVertical,
  IconRestore,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { TotalConIva } from "../../components/TotalConIva";
import {
  useAgregarAcuseArchivo,
  useAgregarAcuseReferencia,
  useCancelarServicio,
  useDuplicarServicio,
  useEliminarViaje,
  useMarcarTerminado,
  useReabrirViaje,
  useServicio,
  useTerminarViaje,
} from "./api";
import { descargarFactura } from "../facturas/api";
import { OperatorReportCard } from "../operacion/components/OperatorReportCard";
import { MensajeWhatsappModal } from "./components/MensajeWhatsappModal";
import { ReescaneoControl } from "./components/ReescaneoControl";
import type { RegimenReceptor } from "../catalogos/types";
import type { FacturaVigente, ViajeOut } from "./types";

const ESTADO_LABEL: Record<string, string> = {
  programado: "Programado",
  en_curso: "En curso",
  terminado: "Terminado",
  cancelado: "Cancelado",
};

// `05-ui-spec §5 StatusBadge`: operación en neutral, salvo "En curso" (info).
const ESTADO_COLOR: Record<string, string> = {
  programado: "gray",
  en_curso: "blue",
  terminado: "gray",
  cancelado: "gray",
};

const COBRO_LABEL: Record<string, string> = { pendiente: "Por cobrar", parcial: "Parcial", pagada: "Pagada" };

// `05-ui-spec §7.1` — la factura vigente del servicio, con descargas y acceso al envío.
function FacturaVigenteCard({ factura }: { factura: FacturaVigente }) {
  return (
    <Card>
      <Group justify="space-between" mb={4}>
        <Text fw={600}>
          Factura {factura.serie}
          {factura.folio} · {pesos(factura.total)}
        </Text>
        <Group gap={6}>
          <Badge variant="light" color={factura.estado === "timbrada" ? "green" : "yellow"}>
            {factura.estado === "timbrada" ? "Timbrada" : "En espera de cancelación"}
          </Badge>
          <Badge variant="light" color={factura.estado_cobro === "pagada" ? "green" : "red"}>
            {COBRO_LABEL[factura.estado_cobro] ?? factura.estado_cobro}
          </Badge>
        </Group>
      </Group>
      {factura.uuid_fiscal && (
        <Text size="xs" c="dimmed">
          UUID {factura.uuid_fiscal}
        </Text>
      )}
      <Group mt="sm" gap="xs">
        <Button size="xs" variant="default" onClick={() => descargarFactura(factura.id, "pdf")}>
          Descargar PDF
        </Button>
        <Button size="xs" variant="default" onClick={() => descargarFactura(factura.id, "xml")}>
          Descargar XML
        </Button>
        <Button size="xs" variant="light" component={Link} to={`/admin/facturas/${factura.id}`}>
          Enviar o ver factura
        </Button>
      </Group>
    </Card>
  );
}

function ViajeCard({
  servicioId,
  viaje,
  modoAcuse,
  onEliminar,
  puedeEditar,
}: {
  servicioId: string;
  viaje: ViajeOut;
  modoAcuse: string;
  onEliminar: () => void;
  puedeEditar: boolean;
}) {
  const terminar = useTerminarViaje(servicioId);
  const reabrir = useReabrirViaje(servicioId);
  const acuseReferencia = useAgregarAcuseReferencia(servicioId);
  const acuseArchivo = useAgregarAcuseArchivo(servicioId);
  const [folio, setFolio] = useState("");

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <Text fw={600}>
            Viaje {viaje.orden} · {viaje.tipo === "recoleccion" ? "Recolección" : viaje.tipo === "entrega" ? "Entrega" : "Recolección y entrega"}
          </Text>
          <Badge variant="light" color={viaje.estado === "terminado" ? "green" : "gray"}>
            {viaje.estado === "terminado" ? "Terminado" : "Pendiente"}
          </Badge>
        </Group>
        <Group gap="xs">
          {viaje.estado === "pendiente" ? (
            <Button
              size="xs"
              leftSection={<IconCheck size={14} />}
              loading={terminar.isPending}
              onClick={() => terminar.mutate({ id: viaje.id, payload: {} })}
            >
              Terminar en nombre del operador
            </Button>
          ) : (
            <Button
              size="xs"
              variant="default"
              leftSection={<IconRestore size={14} />}
              loading={reabrir.isPending}
              onClick={() => reabrir.mutate(viaje.id)}
            >
              Reabrir
            </Button>
          )}
          {puedeEditar && viaje.estado !== "terminado" && (
            <ActionIcon variant="subtle" color="red" aria-label="Quitar viaje" onClick={onEliminar}>
              <IconTrash size={14} />
            </ActionIcon>
          )}
        </Group>
      </Group>

      <Text size="sm" c="dimmed">
        {viaje.origen ? `Origen: ${viaje.origen.nombre}${viaje.origen_cp ? ` (CP ${viaje.origen_cp})` : ""}` : null}
        {viaje.origen && viaje.destino ? " · " : null}
        {viaje.destino ? `Destino: ${viaje.destino.nombre}${viaje.destino_cp ? ` (CP ${viaje.destino_cp})` : ""}` : null}
        {viaje.distancia_km ? ` · ${viaje.distancia_km} km` : ""}
      </Text>

      {viaje.acuse_requerido && (
        <Stack gap={4} mt="sm">
          <Group justify="space-between">
            <Text size="xs" fw={600} c="dimmed">
              Acuse
            </Text>
            {modoAcuse === "escaneo" && !viaje.reescaneo && viaje.estado === "terminado" && (
              <ReescaneoControl
                servicioId={servicioId}
                viajeId={viaje.id}
                destino={viaje.destino?.nombre ?? "este destino"}
                reescaneo={null}
              />
            )}
          </Group>
          {viaje.reescaneo && (
            <ReescaneoControl
              servicioId={servicioId}
              viajeId={viaje.id}
              destino={viaje.destino?.nombre ?? "este destino"}
              reescaneo={viaje.reescaneo}
            />
          )}
          {viaje.acuse_completo ? (
            <Group gap="xs">
              <Badge color="green" variant="light">
                Completo
              </Badge>
              {viaje.acuses.map((a) =>
                a.referencia ? (
                  <Text key={a.id} size="sm">
                    Folio: {a.referencia}
                  </Text>
                ) : (
                  <a key={a.id} href={a.url ?? undefined} target="_blank" rel="noreferrer">
                    Ver acuse
                  </a>
                ),
              )}
            </Group>
          ) : modoAcuse === "referencia" ? (
            <Group>
              <TextInput
                placeholder="Folio del acuse"
                value={folio}
                onChange={(e) => setFolio(e.currentTarget.value)}
                size="xs"
              />
              <Button
                size="xs"
                loading={acuseReferencia.isPending}
                onClick={() =>
                  acuseReferencia.mutate(
                    { viajeId: viaje.id, referencia: folio },
                    { onSuccess: () => setFolio("") },
                  )
                }
              >
                Guardar folio
              </Button>
            </Group>
          ) : viaje.reescaneo ? null : (
            <FileButton
              onChange={(file) => file && acuseArchivo.mutate({ viajeId: viaje.id, file })}
              accept="application/pdf"
            >
              {(props) => (
                <Button size="xs" variant="default" leftSection={<IconUpload size={14} />} loading={acuseArchivo.isPending} {...props}>
                  Subir acuse
                </Button>
              )}
            </FileButton>
          )}
        </Stack>
      )}
    </Card>
  );
}

export function ServicioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: servicio, isLoading, isError } = useServicio(id ?? null);
  const eliminarViaje = useEliminarViaje(id ?? "");
  const duplicar = useDuplicarServicio(id ?? "");
  const cancelar = useCancelarServicio(id ?? "");
  const marcarTerminado = useMarcarTerminado(id ?? "");

  const [duplicarAbierto, setDuplicarAbierto] = useState(false);
  const [fechaDuplicar, setFechaDuplicar] = useState("");
  const [cancelarAbierto, setCancelarAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  // Recién creado el servicio, el mensaje de WhatsApp se ofrece abierto.
  const [whatsappAbierto, setWhatsappAbierto] = useState(
    Boolean((location.state as { mensajeWhatsapp?: boolean } | null)?.mensajeWhatsapp),
  );

  if (isLoading) return <Skeleton height={300} />;
  if (isError || !servicio) {
    return (
      <Alert color="red" icon={<IconAlertTriangle size={18} />}>
        No se pudo cargar el servicio.
      </Alert>
    );
  }

  const puedeEditar = !servicio.datos_fiscales_bloqueados && servicio.estado !== "cancelado";

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate("/admin/servicios")} px={0}>
          Servicios
        </Button>
        <Group gap="xs">
          <Button
            variant="default"
            leftSection={<IconBrandWhatsapp size={16} />}
            onClick={() => setWhatsappAbierto(true)}
          >
            Mensaje WhatsApp
          </Button>
          {/* Con todos los viajes terminados, el siguiente paso queda a la vista (no solo en el menú). */}
          {servicio.acciones_permitidas.includes("marcar_terminado") && (
            <Button
              variant={servicio.acciones_permitidas.includes("facturar") ? "default" : "filled"}
              loading={marcarTerminado.isPending}
              onClick={() => marcarTerminado.mutate()}
            >
              Marcar terminado
            </Button>
          )}
          {servicio.acciones_permitidas.includes("facturar") && (
            <Button onClick={() => navigate(`/admin/servicios/${servicio.id}/facturar`)}>Facturar</Button>
          )}
          <Menu>
            <Menu.Target>
              <ActionIcon variant="default" aria-label="Más acciones">
                <IconDotsVertical size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item onClick={() => setDuplicarAbierto(true)}>Duplicar</Menu.Item>
              {servicio.acciones_permitidas.includes("marcar_terminado") && (
                <Menu.Item onClick={() => marcarTerminado.mutate()}>Marcar terminado</Menu.Item>
              )}
              {servicio.acciones_permitidas.includes("cancelar") && (
                <Menu.Item color="red" onClick={() => setCancelarAbierto(true)}>
                  Cancelar servicio
                </Menu.Item>
              )}
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      <Card>
        <Group justify="space-between">
          <div>
            <Text size="xl" fw={700}>
              Servicio #{servicio.numero}
            </Text>
            <Text c="dimmed" size="sm">
              {servicio.cliente.nombre_comercial} · {servicio.unidad.apodo} · {servicio.operador.nombre} ·{" "}
              {new Date(`${servicio.fecha}T00:00:00`).toLocaleDateString("es-MX")}
            </Text>
          </div>
          <Group gap="xs">
            <Badge variant="light" color={ESTADO_COLOR[servicio.estado]}>
              {ESTADO_LABEL[servicio.estado]}
            </Badge>
            {servicio.estado_facturacion === "facturado" ? (
              <Badge variant="light" color="green">
                Facturado
              </Badge>
            ) : (
              servicio.estado !== "cancelado" &&
              (servicio.estado === "terminado" || servicio.timbrado_anticipado) && (
                <Badge variant="light" color="yellow">
                  Por facturar
                </Badge>
              )
            )}
            {servicio.timbrado_anticipado && (
              <Badge variant="light" color="blue">
                Anticipada
              </Badge>
            )}
          </Group>
        </Group>
        {servicio.subtotal && (
          <div style={{ maxWidth: 280 }}>
            <Text mt="sm">
              Subtotal: <strong>{pesos(servicio.subtotal)}</strong>
            </Text>
            <TotalConIva
              subtotal={Number(servicio.subtotal)}
              regimenReceptor={servicio.cliente.regimen_receptor as RegimenReceptor}
            />
          </div>
        )}
        {servicio.timbrado_anticipado && servicio.timbrado_modo === "cero" && (
          <Text size="sm" c="dimmed" mt="xs">
            Se timbrará con $0.10 y la factura se cancelará sola; el precio real se timbra después.
          </Text>
        )}
        {servicio.notas && (
          <Text size="sm" c="dimmed" mt="xs">
            {servicio.notas}
          </Text>
        )}
        {servicio.datos_fiscales_bloqueados && (
          <Alert color="yellow" icon={<IconAlertTriangle size={16} />} mt="md">
            Facturado: cancela la factura para cambiar sus datos fiscales.
          </Alert>
        )}
      </Card>

      {servicio.factura_vigente && <FacturaVigenteCard factura={servicio.factura_vigente} />}

      <OperatorReportCard servicio={servicio} />

      <Text fw={600}>Viajes</Text>
      {servicio.viajes.map((v) => (
        <ViajeCard
          key={v.id}
          servicioId={servicio.id}
          viaje={v}
          modoAcuse={servicio.cliente.modo_acuse}
          puedeEditar={puedeEditar}
          onEliminar={() => eliminarViaje.mutate(v.id)}
        />
      ))}


      <MensajeWhatsappModal
        servicio={servicio}
        opened={whatsappAbierto}
        onClose={() => {
          setWhatsappAbierto(false);
          // Que no se vuelva a abrir solo al recargar la página.
          navigate(location.pathname, { replace: true, state: null });
        }}
      />

      <Modal opened={duplicarAbierto} onClose={() => setDuplicarAbierto(false)} title="Duplicar servicio">
        <Stack>
          <TextInput
            label="Nueva fecha"
            type="date"
            value={fechaDuplicar}
            onChange={(e) => setFechaDuplicar(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDuplicarAbierto(false)}>
              Cancelar
            </Button>
            <Button
              loading={duplicar.isPending}
              disabled={!fechaDuplicar}
              onClick={() =>
                duplicar.mutate(fechaDuplicar, {
                  onSuccess: (nuevo) => navigate(`/admin/servicios/${nuevo.id}`),
                })
              }
            >
              Duplicar
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={cancelarAbierto} onClose={() => setCancelarAbierto(false)} title="Cancelar servicio">
        <Stack>
          <Text size="sm">Este servicio no se realizó. Indica el motivo.</Text>
          <TextInput label="Motivo" value={motivo} onChange={(e) => setMotivo(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelarAbierto(false)}>
              Volver
            </Button>
            <Button
              color="red"
              disabled={!motivo}
              loading={cancelar.isPending}
              onClick={() =>
                cancelar.mutate(motivo, { onSuccess: () => setCancelarAbierto(false) })
              }
            >
              Cancelar servicio
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
