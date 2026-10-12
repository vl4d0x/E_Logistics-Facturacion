// H4.9 — lista de facturas con filtros por estado y mes de emisión; muestra si ya se envió
// por correo y permite cancelar desde la fila.
import { Badge, Button, Group, Select, Table, Text, TextInput, Tooltip } from "@mantine/core";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { useFacturas, type FacturaResumen } from "./api";
import { CancelarFacturaModal } from "./components/CancelarFacturaModal";
import { ESTADO_FACTURA, pesos } from "./format";

export function FacturasPage() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("");
  const [params] = useSearchParams();
  const [mes, setMes] = useState(params.get("mes_emision") ?? "");
  const mesValido = /^\d{4}-\d{2}$/.test(mes) ? mes : "";
  const { data: facturas, isLoading } = useFacturas({ estado, mes: mesValido });
  const [cancelando, setCancelando] = useState<FacturaResumen | null>(null);

  return (
    <Card>
      <Group mb="md" className="el-filters">
        <Select
          placeholder="Todos los estados"
          clearable
          data={Object.entries(ESTADO_FACTURA).map(([value, { label }]) => ({ value, label }))}
          value={estado || null}
          onChange={(v) => setEstado(v ?? "")}
        />
        <TextInput placeholder="Mes (AAAA-MM)" value={mes} onChange={(e) => setMes(e.currentTarget.value)} maw={150} />
      </Group>
      <Table verticalSpacing="sm" highlightOnHover className="el-cardtable">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Folio</Table.Th>
            <Table.Th>Cliente</Table.Th>
            <Table.Th>Servicio</Table.Th>
            <Table.Th>Emisión</Table.Th>
            <Table.Th ta="right">Total</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {facturas?.map((f) => (
            <Table.Tr key={f.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/admin/facturas/${f.id}`)}>
              <Table.Td data-label="Folio">{`${f.serie ?? ""}${f.folio ?? ""}` || "—"}</Table.Td>
              <Table.Td>{f.cliente_nombre}</Table.Td>
              <Table.Td data-label="Servicio">#{f.servicio_numero}</Table.Td>
              <Table.Td data-label="Emisión">{f.fecha_emision ? new Date(f.fecha_emision).toLocaleDateString("es-MX") : "—"}</Table.Td>
              <Table.Td ta="right" data-label="Total">{pesos(f.total)}</Table.Td>
              <Table.Td>
                <Group gap={4}>
                  <Badge variant="light" color={ESTADO_FACTURA[f.estado].color}>
                    {ESTADO_FACTURA[f.estado].label}
                  </Badge>
                  <EnvioBadge factura={f} />
                </Group>
              </Table.Td>
              <Table.Td onClick={(e) => e.stopPropagation()}>
                {f.estado === "timbrada" &&
                  (f.estado_cobro === "pendiente" ? (
                    <Button size="compact-xs" color="red" variant="light" onClick={() => setCancelando(f)}>
                      Cancelar
                    </Button>
                  ) : (
                    <Tooltip label="Tiene pagos aplicados: primero cancela su REP y revierte el pago (desde Cobranza)">
                      <Button size="compact-xs" color="red" variant="light" disabled>
                        Cancelar
                      </Button>
                    </Tooltip>
                  ))}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {!isLoading && facturas?.length === 0 && (
        <Text c="dimmed" ta="center" py="lg">
          No hay facturas con esos filtros.
        </Text>
      )}
      <CancelarFacturaModal factura={cancelando} onClose={() => setCancelando(null)} />
    </Card>
  );
}

/** "Enviada" (con la fecha), "Correo falló" o "Sin enviar"; nada si la factura no está vigente. */
function EnvioBadge({ factura: f }: { factura: FacturaResumen }) {
  if (f.estado !== "timbrada" && f.estado !== "cancelacion_pendiente") return null;
  if (f.envio_error && !f.enviado_at) {
    return (
      <Tooltip label={f.envio_error} multiline w={280}>
        <Badge variant="light" color="red">
          Correo falló
        </Badge>
      </Tooltip>
    );
  }
  if (f.enviado_at) {
    return (
      <Tooltip label={`Enviada el ${new Date(f.enviado_at).toLocaleString("es-MX")}`}>
        <Badge variant="light" color="blue">
          Enviada
        </Badge>
      </Tooltip>
    );
  }
  return (
    <Badge variant="outline" color="gray">
      Sin enviar
    </Badge>
  );
}
