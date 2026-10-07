// H5.4-H5.6, H5.8 — detalle de un pago: aplicaciones, REP, revertir, enviar y cancelar.
import { Alert, Button, Group, Modal, Select, Stack, Table, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import {
  pesos, useActualizarEstatusRep, useCancelarRep, useEnviarRep, useGenerarRep, usePago, useRevertirPago,
} from "./api";
import { DueBadge } from "./CobranzaPage";

const MOTIVOS = [
  { value: "02", label: "02 · Comprobante emitido con errores sin relación" },
  { value: "03", label: "03 · No se llevó a cabo la operación" },
];

export function PagoDetailPage() {
  const { id = "" } = useParams();
  const { data: p } = usePago(id);
  const generar = useGenerarRep();
  const revertir = useRevertirPago();
  const enviar = useEnviarRep();
  const cancelar = useCancelarRep();
  const estatus = useActualizarEstatusRep();
  const [cancelando, setCancelando] = useState(false);
  const [motivo, setMotivo] = useState<string | null>("02");
  if (!p) return null;
  const rep = p.rep_vigente;
  const puede = (a: string) => p.acciones_permitidas.includes(a);

  return (
    <Stack gap="md">
      <Card>
        <Group justify="space-between" mb="xs">
          <Text fw={600} size="lg">Pago de {p.cliente.nombre_comercial} · {pesos(p.monto)}</Text>
          {p.estado !== "registrado" && <DueBadge pendiente={p.rep_pendiente} dias={p.dias_para_vencer} vence={p.vence_rep} />}
        </Group>
        <Text size="sm" c="dimmed">
          {new Date(p.fecha_pago).toLocaleDateString("es-MX")} · forma {p.forma_pago}
          {p.num_operacion ? ` · ref. ${p.num_operacion}` : ""}
        </Text>
        {p.rep_pendiente && p.dias_para_vencer !== null && p.dias_para_vencer < 0 && (
          <Alert color="red" mt="md" icon={<IconAlertTriangle size={18} />}>
            El REP de este pago ya está vencido; emítelo hoy.
          </Alert>
        )}
        {rep?.estado === "cancelacion_pendiente" && (
          <Alert color="yellow" mt="md" icon={<IconAlertTriangle size={18} />}>
            Cancelación del REP en espera de aceptación del receptor.
            <Group mt="xs">
              <Button size="xs" variant="default" loading={estatus.isPending} onClick={() => estatus.mutate({ id: rep.id })}>
                Actualizar estatus
              </Button>
            </Group>
          </Alert>
        )}
        <Group mt="md">
          {puede("generar_rep") && <Button loading={generar.isPending} onClick={() => generar.mutate({ id: p.id })}>Generar REP</Button>}
          {rep && puede("enviar_rep") && <Button variant="default" loading={enviar.isPending} onClick={() => enviar.mutate({ id: rep.id, body: {} })}>{rep.enviado_at ? "Reenviar REP" : "Enviar REP al cliente"}</Button>}
          {rep && puede("cancelar_rep") && <Button color="red" variant="light" onClick={() => setCancelando(true)}>Cancelar REP</Button>}
          {puede("revertir") && <Button color="red" variant="subtle" loading={revertir.isPending} onClick={() => revertir.mutate({ id: p.id })}>Revertir aplicación</Button>}
          {rep?.pdf_url && <Button component="a" href={rep.pdf_url} target="_blank" variant="default">PDF</Button>}
          {rep?.xml_url && <Button component="a" href={rep.xml_url} target="_blank" variant="default">XML</Button>}
        </Group>
      </Card>

      <Card>
        <Text fw={600} mb="xs">Facturas pagadas</Text>
        <Table verticalSpacing="xs">
          <Table.Thead>
            <Table.Tr><Table.Th>Factura</Table.Th><Table.Th>Parcialidad</Table.Th><Table.Th ta="right">Saldo anterior</Table.Th><Table.Th ta="right">Pagado</Table.Th><Table.Th ta="right">Saldo</Table.Th></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {p.aplicaciones.map((a) => (
              <Table.Tr key={a.factura_id}>
                <Table.Td><Link to={`/admin/facturas/${a.factura_id}`}>{a.folio}</Link></Table.Td>
                <Table.Td>{a.num_parcialidad}</Table.Td>
                <Table.Td ta="right">{pesos(a.saldo_anterior)}</Table.Td>
                <Table.Td ta="right">{pesos(a.monto)}</Table.Td>
                <Table.Td ta="right">{pesos(a.saldo_insoluto)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {p.aplicaciones.length === 0 && <Text c="dimmed" size="sm">Este pago aún no está aplicado a ninguna factura.</Text>}
      </Card>

      {p.reps.length > 0 && (
        <Card>
          <Text fw={600} mb="xs">Historial de REP</Text>
          {p.reps.map((r) => (
            <Text size="sm" key={r.id}>{r.serie}{r.folio} · {r.estado} · {r.uuid_fiscal ?? r.error_detalle ?? "—"}</Text>
          ))}
        </Card>
      )}

      <Modal opened={cancelando} onClose={() => setCancelando(false)} title="Cancelar REP">
        <Stack>
          <Select label="Motivo" data={MOTIVOS} value={motivo} onChange={setMotivo} allowDeselect={false} />
          <Text size="sm" c="dimmed">La cancelación de un REP siempre requiere la aceptación del receptor.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelando(false)}>Volver</Button>
            <Button color="red" loading={cancelar.isPending} onClick={() => rep && motivo && cancelar.mutate({ id: rep.id, body: { motivo } }, { onSuccess: () => setCancelando(false) })}>Cancelar REP</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
