// H4.8-H4.10 — detalle de factura: descargas, envío por correo y cancelación.
import { Alert, Badge, Button, Group, Modal, Select, Stack, Text, TextInput } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { descargarFactura, useActualizarEstatus, useCancelarFactura, useEnviarFactura, useFactura } from "./api";
import { ESTADO_FACTURA, pesos } from "./format";

const MOTIVOS = [
  { value: "02", label: "02 · Comprobante emitido con errores sin relación" },
  { value: "03", label: "03 · No se llevó a cabo la operación" },
  { value: "04", label: "04 · Operación nominativa en factura global" },
];

export function FacturaDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data: f } = useFactura(id);
  const cancelar = useCancelarFactura(id);
  const enviar = useEnviarFactura(id);
  const actualizarEstatus = useActualizarEstatus(id);
  const [cancelando, setCancelando] = useState(false);
  const [motivo, setMotivo] = useState<string | null>("02");
  const [destinatarios, setDestinatarios] = useState<string | null>(null);

  if (!f) return null;
  const vigente = f.estado === "timbrada" || f.estado === "cancelacion_pendiente";
  const correos = destinatarios ?? f.emails_cliente.join(", ");

  return (
    <Stack gap="md">
      <Card>
        <Group justify="space-between" mb="sm">
          <Text fw={600} size="lg">
            Factura {f.serie}
            {f.folio} · {f.cliente_nombre}
          </Text>
          <Badge variant="light" color={ESTADO_FACTURA[f.estado].color}>
            {ESTADO_FACTURA[f.estado].label}
          </Badge>
        </Group>
        <Text size="sm">
          Servicio <Link to={`/admin/servicios/${f.servicio_id}`}>#{f.servicio_numero}</Link> · Subtotal{" "}
          {pesos(f.subtotal)} · IVA {pesos(f.iva_trasladado)} · Retención {pesos(f.iva_retenido)} ·{" "}
          <b>Total {pesos(f.total)}</b>
        </Text>
        <Text size="xs" c="dimmed" mt={4}>
          UUID {f.uuid_fiscal}
        </Text>

        {f.estado === "cancelacion_pendiente" && (
          <Alert color="yellow" mt="md" icon={<IconAlertTriangle size={18} />}>
            Cancelación en espera de la aceptación del receptor (hasta 3 días hábiles). Los datos del servicio siguen
            bloqueados.
            <Group mt="xs">
              <Button
                size="xs"
                variant="default"
                loading={actualizarEstatus.isPending}
                onClick={() => actualizarEstatus.mutate(undefined)}
              >
                Actualizar estatus
              </Button>
            </Group>
          </Alert>
        )}
        {f.ejercicio_anterior && f.estado === "timbrada" && (
          <Alert color="orange" mt="md" icon={<IconAlertTriangle size={18} />}>
            Es de un ejercicio anterior: el SAT puede rechazar la cancelación.
          </Alert>
        )}

        <Group mt="md">
          <Button variant="default" onClick={() => descargarFactura(f.id, "pdf")}>
            Descargar PDF
          </Button>
          <Button variant="default" onClick={() => descargarFactura(f.id, "xml")}>
            Descargar XML
          </Button>
          {f.estado === "timbrada" && f.estado_cobro !== "pagada" && (
            <Button
              variant="light"
              onClick={() => navigate(`/admin/cobranza?tab=por-cobrar&cliente=${f.cliente_id}&factura=${f.id}`)}
            >
              Registrar pago
            </Button>
          )}
          {f.estado === "timbrada" && (
            <Button color="red" variant="light" onClick={() => setCancelando(true)}>
              Cancelar factura
            </Button>
          )}
        </Group>
      </Card>

      {vigente && (
        <Card>
          <Text fw={600} mb="xs">
            Enviar por correo
          </Text>
          <TextInput
            label="Destinatarios (separados por coma)"
            value={correos}
            onChange={(e) => setDestinatarios(e.currentTarget.value)}
          />
          {f.enviado_at && (
            <Text size="sm" c="dimmed" mt="xs">
              Enviado el {new Date(f.enviado_at).toLocaleString("es-MX")} a {f.envio_destinatarios?.join(", ")}
            </Text>
          )}
          {f.envio_error && (
            <Alert color="red" mt="xs">
              Último intento falló: {f.envio_error}
            </Alert>
          )}
          <Button
            mt="md"
            loading={enviar.isPending}
            onClick={() =>
              enviar.mutate({
                to: correos
                  .split(",")
                  .map((c) => c.trim())
                  .filter(Boolean),
              })
            }
          >
            {f.enviado_at ? "Reenviar" : "Enviar al cliente"}
          </Button>
        </Card>
      )}

      <Modal opened={cancelando} onClose={() => setCancelando(false)} title="Cancelar factura">
        <Stack>
          <Select label="Motivo" data={MOTIVOS} value={motivo} onChange={setMotivo} allowDeselect={false} />
          <Text size="sm" c="dimmed">
            Con más de $1,000 el receptor debe aceptar la cancelación; la factura puede quedar “en espera”.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelando(false)}>
              Volver
            </Button>
            <Button
              color="red"
              loading={cancelar.isPending}
              onClick={() => motivo && cancelar.mutate({ motivo }, { onSuccess: () => setCancelando(false) })}
            >
              Cancelar factura
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
