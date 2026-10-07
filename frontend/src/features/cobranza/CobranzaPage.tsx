// H5.1, H5.7, H5.8 — Cobranza: Por cobrar, Pagos y REP, Pagadas.
import { Badge, Checkbox, Group, Table, Tabs, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { centavos, pesos, useCobranzaClientes, useCobranzaFacturas, usePagos } from "./api";
import { RegistrarPagoPanel } from "./RegistrarPagoPanel";

function PorCobrarTab() {
  const [params, setParams] = useSearchParams();
  const clienteId = params.get("cliente");
  const { data: clientes } = useCobranzaClientes();
  const mes = params.get("mes");
  const anio = params.get("anio");
  const { data: facturas = [] } = useCobranzaFacturas(clienteId, "pendiente,parcial", mes, anio);
  const [seleccion, setSeleccion] = useState<Record<string, number>>({});
  const preseleccion = params.get("factura"); // atajo desde el detalle de una factura (H5.2)
  const inicial = facturas.find((f) => f.id === preseleccion);

  useEffect(() => {
    if (inicial) setSeleccion({ [inicial.id]: centavos(inicial.saldo_insoluto) });
  }, [inicial?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const alternar = (id: string, saldo: string) => {
    const { [id]: quitada, ...resto } = seleccion;
    setSeleccion(quitada !== undefined ? resto : { ...seleccion, [id]: centavos(saldo) });
  };

  return (
    <div className="el-grid-aside">
      <Card>
        <Table verticalSpacing="xs" highlightOnHover mb="lg">
          <Table.Thead>
            <Table.Tr><Table.Th>Cliente</Table.Th><Table.Th ta="right">Saldo</Table.Th><Table.Th ta="right">Vencido</Table.Th><Table.Th>Facturas</Table.Th></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {clientes?.map((c) => (
              <Table.Tr
                key={c.cliente.id} style={{ cursor: "pointer" }}
                bg={c.cliente.id === clienteId ? "var(--mantine-color-red-0)" : undefined}
                onClick={() => { setSeleccion({}); setParams({ tab: "por_cobrar", cliente: c.cliente.id }); }}
              >
                <Table.Td>{c.cliente.nombre_comercial}</Table.Td>
                <Table.Td ta="right">{pesos(c.saldo)}</Table.Td>
                <Table.Td ta="right" c={Number(c.saldo_vencido) > 0 ? "red" : undefined}>{pesos(c.saldo_vencido)}</Table.Td>
                <Table.Td>{c.facturas_abiertas}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {clientes?.length === 0 && <Text c="dimmed" ta="center">No hay saldos por cobrar.</Text>}
        {(clienteId || mes || anio) && (
          <Table verticalSpacing="xs" className="el-cardtable">
            <Table.Thead>
              <Table.Tr><Table.Th /><Table.Th>Folio</Table.Th><Table.Th>Servicio</Table.Th><Table.Th>Emisión</Table.Th><Table.Th ta="right">Total</Table.Th><Table.Th ta="right">Saldo</Table.Th><Table.Th>Antigüedad</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {facturas.map((f) => (
                <Table.Tr key={f.id}>
                  <Table.Td><Checkbox checked={f.id in seleccion} onChange={() => alternar(f.id, f.saldo_insoluto)} aria-label={`Seleccionar ${f.folio}`} /></Table.Td>
                  <Table.Td data-label="Folio">{f.folio}</Table.Td>
                  <Table.Td data-label="Servicio">#{f.servicio.numero} · {f.servicio.ruta_resumen}</Table.Td>
                  <Table.Td data-label="Emisión">{f.fecha_emision ? new Date(f.fecha_emision).toLocaleDateString("es-MX") : "—"}</Table.Td>
                  <Table.Td ta="right" data-label="Total">{pesos(f.total)}</Table.Td>
                  <Table.Td ta="right" data-label="Saldo">{pesos(f.saldo_insoluto)}</Table.Td>
                  <Table.Td><Badge color={f.vencida ? "red" : "gray"} variant="light" title={f.vencida ? "Vencida" : undefined} style={{ maxWidth: "none" }}>{f.dias_transcurridos} d{f.vencida ? " ⚠" : ""}</Badge></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
      <RegistrarPagoPanel
        key={inicial?.id ?? "manual"}
        clienteId={clienteId}
        facturas={facturas}
        seleccion={seleccion}
        setSeleccion={setSeleccion}
        montoInicial={inicial ? Number(inicial.saldo_insoluto) : null}
      />
    </div>
  );
}

export function DueBadge({ pendiente, dias, vence }: { pendiente: boolean; dias: number | null; vence: string }) {
  if (!pendiente) return <Badge color="green" variant="light">REP emitido</Badge>;
  const color = dias !== null && dias < 0 ? "red" : dias !== null && dias <= 3 ? "yellow" : "gray";
  const texto = dias !== null && dias < 0 ? `Vencido (${vence})` : `Vence el ${vence}`;
  return <Badge color={color} variant="light">{texto}</Badge>;
}

function PagosTab() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { data: pagos = [] } = usePagos(params.get("rep_pendiente") === "true");
  const pendientes = pagos.filter((p) => p.rep_pendiente);
  return (
    <Card>
      {pendientes.length > 0 && (
        <Text fw={600} mb="sm">
          {pendientes.length} REP por emitir · vence el {pendientes[0].vence_rep}
        </Text>
      )}
      <Table verticalSpacing="sm" highlightOnHover className="el-cardtable">
        <Table.Thead>
          <Table.Tr><Table.Th>Fecha</Table.Th><Table.Th>Cliente</Table.Th><Table.Th ta="right">Monto</Table.Th><Table.Th>Estado</Table.Th><Table.Th>REP</Table.Th></Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {pagos.map((p) => (
            <Table.Tr key={p.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/admin/cobranza/pagos/${p.id}`)}>
              <Table.Td data-label="Fecha">{new Date(p.fecha_pago).toLocaleDateString("es-MX")}</Table.Td>
              <Table.Td>{p.cliente.nombre_comercial}</Table.Td>
              <Table.Td ta="right" data-label="Monto">{pesos(p.monto)}</Table.Td>
              <Table.Td>{p.estado === "registrado" ? "Sin aplicar" : p.estado === "aplicado" ? "Aplicado" : "Con REP"}</Table.Td>
              <Table.Td>{p.estado === "registrado" ? "—" : <DueBadge pendiente={p.rep_pendiente} dias={p.dias_para_vencer} vence={p.vence_rep} />}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {pagos.length === 0 && <Text c="dimmed" ta="center" py="lg">Aún no hay pagos registrados.</Text>}
    </Card>
  );
}

function PagadasTab() {
  const [params] = useSearchParams();
  const { data: facturas = [] } = useCobranzaFacturas(null, "pagada", params.get("mes"), params.get("anio"));
  return (
    <Card>
      <Table verticalSpacing="sm" className="el-cardtable">
        <Table.Thead>
          <Table.Tr><Table.Th>Folio</Table.Th><Table.Th>Cliente</Table.Th><Table.Th>Servicio</Table.Th><Table.Th>Emisión</Table.Th><Table.Th ta="right">Total</Table.Th></Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {facturas.map((f) => (
            <Table.Tr key={f.id}>
              <Table.Td data-label="Folio">{f.folio}</Table.Td><Table.Td>{f.cliente_nombre}</Table.Td>
              <Table.Td data-label="Servicio">#{f.servicio.numero} · {f.servicio.ruta_resumen}</Table.Td>
              <Table.Td data-label="Emisión">{f.fecha_emision ? new Date(f.fecha_emision).toLocaleDateString("es-MX") : "—"}</Table.Td>
              <Table.Td ta="right" data-label="Total">{pesos(f.total)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {facturas.length === 0 && <Text c="dimmed" ta="center" py="lg">Todavía no hay facturas pagadas.</Text>}
    </Card>
  );
}

export function CobranzaPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "por_cobrar";
  return (
    <Tabs value={tab} onChange={(v) => v && setParams({ tab: v })}>
      <Tabs.List mb="lg">
        <Tabs.Tab value="por_cobrar">Por cobrar</Tabs.Tab>
        <Tabs.Tab value="pagos">Pagos y REP</Tabs.Tab>
        <Tabs.Tab value="pagadas">Pagadas</Tabs.Tab>
      </Tabs.List>
      <Group />
      {tab === "por_cobrar" && <PorCobrarTab />}
      {tab === "pagos" && <PagosTab />}
      {tab === "pagadas" && <PagadasTab />}
    </Tabs>
  );
}
