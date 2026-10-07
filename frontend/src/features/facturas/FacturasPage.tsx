// H4.9 — lista de facturas con filtros por estado y mes de emisión.
import { Badge, Group, Select, Table, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { useFacturas } from "./api";
import { ESTADO_FACTURA, pesos } from "./format";

export function FacturasPage() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("");
  const [params] = useSearchParams();
  const [mes, setMes] = useState(params.get("mes_emision") ?? "");
  const mesValido = /^\d{4}-\d{2}$/.test(mes) ? mes : "";
  const { data: facturas, isLoading } = useFacturas({ estado, mes: mesValido });

  return (
    <Card>
      <Group mb="md">
        <Select
          placeholder="Todos los estados"
          clearable
          data={Object.entries(ESTADO_FACTURA).map(([value, { label }]) => ({ value, label }))}
          value={estado || null}
          onChange={(v) => setEstado(v ?? "")}
        />
        <TextInput placeholder="Mes (AAAA-MM)" value={mes} onChange={(e) => setMes(e.currentTarget.value)} maw={150} />
      </Group>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Folio</Table.Th>
            <Table.Th>Cliente</Table.Th>
            <Table.Th>Servicio</Table.Th>
            <Table.Th>Emisión</Table.Th>
            <Table.Th ta="right">Total</Table.Th>
            <Table.Th>Estado</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {facturas?.map((f) => (
            <Table.Tr key={f.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/admin/facturas/${f.id}`)}>
              <Table.Td>{`${f.serie ?? ""}${f.folio ?? ""}` || "—"}</Table.Td>
              <Table.Td>{f.cliente_nombre}</Table.Td>
              <Table.Td>#{f.servicio_numero}</Table.Td>
              <Table.Td>{f.fecha_emision ? new Date(f.fecha_emision).toLocaleDateString("es-MX") : "—"}</Table.Td>
              <Table.Td ta="right">{pesos(f.total)}</Table.Td>
              <Table.Td>
                <Badge variant="light" color={ESTADO_FACTURA[f.estado].color}>
                  {ESTADO_FACTURA[f.estado].label}
                </Badge>
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
    </Card>
  );
}
