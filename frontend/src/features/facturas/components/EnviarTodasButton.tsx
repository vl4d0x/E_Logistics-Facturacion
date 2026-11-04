// "Enviar todas": manda por correo, cada una a su cliente, las facturas timbradas que aún no se
// han enviado. Antes de enviar muestra la lista (con a quién va cada una) para confirmar.
// El backend las bloquea una por una y no reenvía las que ya salieron: un doble clic no duplica.
import { Alert, Button, Checkbox, Group, List, Modal, Stack, Table, Text, Tooltip } from "@mantine/core";
import { IconMailForward } from "@tabler/icons-react";
import { useState } from "react";
import { useEnviarPendientes, useEnvioPendiente, type ResultadoEnvio } from "../api";
import { pesos } from "../format";

export function EnviarTodasButton() {
  const { data } = useEnvioPendiente();
  const [abierto, setAbierto] = useState(false);
  const enviables = (data?.facturas ?? []).filter((f) => !f.motivo_no_enviable);
  const n = enviables.length;
  return (
    <>
      <Tooltip label={n ? "Envía cada factura a los correos de su cliente" : "No hay facturas sin enviar"}>
        <Button leftSection={<IconMailForward size={16} />} onClick={() => setAbierto(true)} disabled={!data?.facturas.length}>
          Enviar todas{n ? ` (${n})` : ""}
        </Button>
      </Tooltip>
      {abierto && <EnviarTodasModal onClose={() => setAbierto(false)} />}
    </>
  );
}

function EnviarTodasModal({ onClose }: { onClose: () => void }) {
  const { data } = useEnvioPendiente();
  const enviar = useEnviarPendientes();
  const [quitadas, setQuitadas] = useState<Set<string>>(new Set());
  const [resultado, setResultado] = useState<ResultadoEnvio | null>(null);
  const facturas = data?.facturas ?? [];
  const elegidas = facturas.filter((f) => !f.motivo_no_enviable && !quitadas.has(f.id));

  function alternar(id: string) {
    setQuitadas((prev) => {
      const sig = new Set(prev);
      if (sig.has(id)) sig.delete(id);
      else sig.add(id);
      return sig;
    });
  }

  return (
    <Modal opened onClose={enviar.isPending ? () => {} : onClose} title="Enviar facturas a los clientes" size="xl">
      {resultado ? (
        <Stack>
          <Text>
            <b>{resultado.enviadas.length}</b> enviada{resultado.enviadas.length === 1 ? "" : "s"}
            {data?.modo_prueba ? " (en modo prueba)" : ""}.
          </Text>
          {resultado.fallidas.length > 0 && (
            <Alert color="red" variant="light" title="No se pudieron enviar">
              <List size="sm">
                {resultado.fallidas.map((f) => (
                  <List.Item key={f.id}>
                    {f.folio}: {f.error}
                  </List.Item>
                ))}
              </List>
            </Alert>
          )}
          {resultado.omitidas.length > 0 && (
            <Alert color="yellow" variant="light" title="No se enviaron">
              <List size="sm">
                {resultado.omitidas.map((f) => (
                  <List.Item key={f.id}>
                    {f.folio ?? "—"}: {f.motivo}
                  </List.Item>
                ))}
              </List>
            </Alert>
          )}
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          {data?.modo_prueba ? (
            <Alert color="yellow" variant="light" title="Modo prueba">
              Los correos irán a <b>{data.destino_prueba}</b>, no a los clientes, y las facturas seguirán como "Sin enviar".
            </Alert>
          ) : (
            data?.copia && (
              <Text size="sm" c="dimmed">
                Cada correo lleva copia a {data.copia}. Las que ya se enviaron no se vuelven a mandar.
              </Text>
            )
          )}
          {facturas.length === 0 ? (
            <Text c="dimmed" ta="center" py="lg">
              No hay facturas sin enviar.
            </Text>
          ) : (
            <Table verticalSpacing="xs" className="el-cardtable">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th />
                  <Table.Th>Folio</Table.Th>
                  <Table.Th>Cliente</Table.Th>
                  <Table.Th>Servicio</Table.Th>
                  <Table.Th ta="right">Total</Table.Th>
                  <Table.Th>Para</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {facturas.map((f) => (
                  <Table.Tr key={f.id} style={{ opacity: f.motivo_no_enviable || quitadas.has(f.id) ? 0.55 : 1 }}>
                    <Table.Td>
                      <Checkbox
                        aria-label={`Enviar ${f.serie ?? ""}${f.folio ?? ""}`}
                        checked={!f.motivo_no_enviable && !quitadas.has(f.id)}
                        disabled={!!f.motivo_no_enviable || enviar.isPending}
                        onChange={() => alternar(f.id)}
                      />
                    </Table.Td>
                    <Table.Td data-label="Folio">{`${f.serie ?? ""}${f.folio ?? ""}` || "—"}</Table.Td>
                    <Table.Td data-label="Cliente">{f.cliente_nombre}</Table.Td>
                    <Table.Td data-label="Servicio">{f.servicio_numero != null ? `#${f.servicio_numero}` : "—"}</Table.Td>
                    <Table.Td ta="right" data-label="Total">
                      {pesos(f.total)}
                    </Table.Td>
                    <Table.Td data-label="Para">
                      {f.motivo_no_enviable ? (
                        <Text size="sm" c="orange.8">
                          {f.motivo_no_enviable}
                        </Text>
                      ) : (
                        <Text size="sm" style={{ wordBreak: "break-all" }}>
                          {f.destinatarios.join(", ")}
                        </Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose} disabled={enviar.isPending}>
              Cancelar
            </Button>
            <Button
              leftSection={<IconMailForward size={16} />}
              disabled={elegidas.length === 0}
              loading={enviar.isPending}
              onClick={() => enviar.mutate(elegidas.map((f) => f.id), { onSuccess: setResultado })}
            >
              Enviar {elegidas.length} factura{elegidas.length === 1 ? "" : "s"}
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
