// Historial de movimientos de cada admin: facturó, envió factura, canceló factura/servicio.
// Solo hay registros desde el 11 nov 2026 (no se rellenan días anteriores).
import { Anchor, Badge, Button, Group, Select, Table, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../../components/Card";
import { TAMANO_PAGINA, useFiltrosHistorial, useHistorial, type Movimiento } from "./api";

const COLOR: Record<string, string> = {
  factura_timbrada: "green",
  factura_enviada: "blue",
  factura_cancelada: "red",
  servicio_cancelado: "orange",
};

const ZONA = "America/Mexico_City";
const dia = (iso: string) =>
  new Date(iso).toLocaleDateString("es-MX", { timeZone: ZONA, day: "2-digit", month: "short", year: "numeric" });
const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-MX", { timeZone: ZONA, hour: "2-digit", minute: "2-digit" });

function destino(m: Movimiento): string | null {
  if (m.factura_id) return `/admin/facturas/${m.factura_id}`;
  if (m.servicio_id) return `/admin/servicios/${m.servicio_id}`;
  return null;
}

export function HistorialPage() {
  const [usuarioId, setUsuarioId] = useState("");
  const [tipo, setTipo] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [page, setPage] = useState(1);
  const { data: filtros } = useFiltrosHistorial();
  const { data, isLoading, isError } = useHistorial({ usuario_id: usuarioId, tipo, desde, hasta, page });

  // Cambiar un filtro regresa a la primera página.
  const filtrar = (fn: () => void) => () => {
    fn();
    setPage(1);
  };
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(total / TAMANO_PAGINA));

  let ultimoDia = "";
  return (
    <Card>
      <Group mb="xs" className="el-filters">
        <Select
          placeholder="Todos los admins"
          clearable
          data={(filtros?.admins ?? []).map((a) => ({ value: a.id, label: a.nombre }))}
          value={usuarioId || null}
          onChange={(v) => { setUsuarioId(v ?? ""); setPage(1); }}
          w={200}
        />
        <Select
          placeholder="Todos los movimientos"
          clearable
          data={filtros?.tipos ?? []}
          value={tipo || null}
          onChange={(v) => { setTipo(v ?? ""); setPage(1); }}
          w={220}
        />
        <TextInput type="date" aria-label="Desde" title="Desde" value={desde} max={hasta || undefined} onChange={(e) => { setDesde(e.currentTarget.value); setPage(1); }} w={150} />
        <TextInput type="date" aria-label="Hasta" title="Hasta" value={hasta} min={desde || undefined} onChange={(e) => { setHasta(e.currentTarget.value); setPage(1); }} w={150} />
        {(desde || hasta) && (
          <Button variant="subtle" size="compact-sm" onClick={filtrar(() => { setDesde(""); setHasta(""); })}>
            Quitar fechas
          </Button>
        )}
      </Group>
      <Text size="xs" c="dimmed" mb="md">
        Se registra desde el 11 de noviembre de 2026; los días anteriores no aparecen.
      </Text>

      {isError && <Text c="red">No se pudo cargar el historial.</Text>}

      <Table verticalSpacing="sm" className="el-cardtable">
        <Table.Tbody>
          {items.map((m) => {
            const d = dia(m.created_at);
            const encabezado = d !== ultimoDia;
            ultimoDia = d;
            const ruta = destino(m);
            return [
              encabezado && (
                <Table.Tr key={`d-${m.id}`} style={{ background: "transparent" }}>
                  <Table.Td colSpan={4} pt="md" pb={2}>
                    <Text size="xs" tt="uppercase" c="dimmed" fw={700}>
                      {d}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ),
              <Table.Tr key={m.id}>
                <Table.Td w={100} style={{ whiteSpace: "nowrap" }}>{hora(m.created_at)}</Table.Td>
                <Table.Td w={170}>{m.usuario.nombre}</Table.Td>
                <Table.Td w={160}>
                  <Badge variant="light" color={COLOR[m.tipo] ?? "gray"}>
                    {m.etiqueta}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {ruta ? (
                    <Anchor component={Link} to={ruta} size="sm">
                      {m.descripcion}
                    </Anchor>
                  ) : (
                    <Text size="sm">{m.descripcion}</Text>
                  )}
                </Table.Td>
              </Table.Tr>,
            ];
          })}
        </Table.Tbody>
      </Table>

      {!isLoading && items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Todavía no hay movimientos con estos filtros.
        </Text>
      )}

      {total > TAMANO_PAGINA && (
        <Group justify="center" mt="md">
          <Button variant="default" size="xs" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Anterior
          </Button>
          <Text size="sm" c="dimmed">
            Página {page} de {paginas} · {total} movimientos
          </Text>
          <Button variant="default" size="xs" disabled={page >= paginas} onClick={() => setPage(page + 1)}>
            Siguiente
          </Button>
        </Group>
      )}
    </Card>
  );
}
