// H4.9 — lista de facturas con filtros por estado y mes de emisión; muestra si ya se envió
// por correo y permite cancelar desde la fila.
import { Badge, Button, FileButton, Group, List, Modal, Select, Stack, Table, Text, TextInput, Tooltip } from "@mantine/core";
import { IconUpload } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { OrigenFacturaBadge } from "../../components/OrigenFacturaBadge";
import { useFacturas, useImportarFacturador, type FacturaResumen, type ResultadoImportacion } from "./api";
import { CancelarFacturaModal } from "./components/CancelarFacturaModal";
import { EnviarTodasButton } from "./components/EnviarTodasButton";
import { ESTADO_FACTURA, pesos } from "./format";

/** Último día del mes "AAAA-MM" como AAAA-MM-DD. */
function finDeMes(mes: string): string {
  const [a, m] = mes.split("-").map(Number);
  return `${mes}-${String(new Date(a, m, 0).getDate()).padStart(2, "0")}`;
}

export function FacturasPage() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("");
  const [params] = useSearchParams();
  // El enlace del dashboard trae un mes (AAAA-MM): se convierte al rango de ese mes.
  const mesInicial = /^\d{4}-\d{2}$/.test(params.get("mes_emision") ?? "") ? params.get("mes_emision")! : "";
  const [desde, setDesde] = useState(mesInicial ? `${mesInicial}-01` : "");
  const [hasta, setHasta] = useState(mesInicial ? finDeMes(mesInicial) : "");
  const [origen, setOrigen] = useState("");
  const { data: facturas, isLoading } = useFacturas({ estado, mes: "", origen, desde, hasta });
  const [cancelando, setCancelando] = useState<FacturaResumen | null>(null);
  const importar = useImportarFacturador();
  const [resultado, setResultado] = useState<ResultadoImportacion | null>(null);
  // Con el historial del Facturador son miles: se muestran de 200 en 200.
  const [visibles, setVisibles] = useState(200);

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
        <TextInput type="date" aria-label="Desde" title="Emitidas desde" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.currentTarget.value)} maw={160} />
        <TextInput type="date" aria-label="Hasta" title="Emitidas hasta" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.currentTarget.value)} maw={160} />
        {(desde || hasta) && (
          <Button variant="subtle" size="compact-sm" onClick={() => { setDesde(""); setHasta(""); }}>
            Quitar fechas
          </Button>
        )}
        <Select
          placeholder="Todos los sistemas"
          clearable
          data={[
            { value: "app", label: "Timbradas en esta app" },
            { value: "facturador", label: "facturadorelectronico" },
          ]}
          value={origen || null}
          onChange={(v) => setOrigen(v ?? "")}
          maw={230}
        />
        <FileButton
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(f) => f && importar.mutate(f, { onSuccess: setResultado })}
        >
          {(props) => (
            <Tooltip label="Reporte de emisión del Facturador Electrónico (.xlsx). Se puede volver a subir uno más nuevo: actualiza lo cobrado sin duplicar.">
              <Button {...props} variant="default" leftSection={<IconUpload size={16} />} loading={importar.isPending} ml="auto">
                Importar del Facturador
              </Button>
            </Tooltip>
          )}
        </FileButton>
        <EnviarTodasButton />
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
          {facturas?.slice(0, visibles).map((f) => (
            <Table.Tr key={f.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/admin/facturas/${f.id}`)}>
              <Table.Td data-label="Folio">{`${f.serie ?? ""}${f.folio ?? ""}` || "—"}</Table.Td>
              <Table.Td>{f.cliente_nombre}</Table.Td>
              <Table.Td data-label="Servicio">
                {f.servicio_numero != null ? `#${f.servicio_numero}` : <OrigenFacturaBadge origen={f.origen} />}
              </Table.Td>
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
                {f.estado === "timbrada" && f.origen !== "facturador" &&
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
      {facturas && facturas.length > visibles && (
        <Group justify="center" mt="md">
          <Button variant="light" onClick={() => setVisibles((v) => v + 200)}>
            Mostrar más ({(facturas.length - visibles).toLocaleString("es-MX")} restantes)
          </Button>
        </Group>
      )}
      <ResultadoImportacionModal resultado={resultado} onClose={() => setResultado(null)} />
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
function ResultadoImportacionModal({ resultado: r, onClose }: { resultado: ResultadoImportacion | null; onClose: () => void }) {
  return (
    <Modal opened={!!r} onClose={onClose} title="Importación del Facturador Electrónico">
      {r && (
        <Stack gap="sm">
          <List size="sm" spacing={4}>
            <List.Item>
              {r.creadas.toLocaleString("es-MX")} facturas nuevas, {r.actualizadas.toLocaleString("es-MX")} actualizadas
            </List.Item>
            <List.Item>
              {r.vigentes.toLocaleString("es-MX")} vigentes: {r.pagadas.toLocaleString("es-MX")} pagadas y{" "}
              {r.con_saldo.toLocaleString("es-MX")} con saldo ({pesos(r.saldo_total)})
            </List.Item>
            <List.Item>{r.canceladas.toLocaleString("es-MX")} canceladas (no cuentan en el dashboard)</List.Item>
            {r.de_la_app > 0 && <List.Item>{r.de_la_app} ya estaban timbradas en esta app: no se tocaron</List.Item>}
            <List.Item>{r.ignoradas.toLocaleString("es-MX")} filas ignoradas (REP emitidos en el Facturador: no se importan)</List.Item>
          </List>
          {r.clientes_creados.length > 0 && (
            <Text size="sm" c="var(--el-warning-text)">
              Se dieron de alta {r.clientes_creados.length} clientes que no estaban en el catálogo ({r.clientes_creados.join(", ")}).
              Completa su código postal y régimen fiscal en Catálogos → Clientes antes de emitirles un REP.
            </Text>
          )}
          <Button onClick={onClose}>Listo</Button>
        </Stack>
      )}
    </Modal>
  );
}

function EnvioBadge({ factura: f }: { factura: FacturaResumen }) {
  if (f.origen === "facturador") return null;
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
