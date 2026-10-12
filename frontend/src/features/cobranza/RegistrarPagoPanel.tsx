// H5.2-H5.4 — panel "Registrar pago" con conciliación automática (`06 §3`).
import { fechaCorta, hoyMexico } from "../../lib/fecha";
import {
  Alert, Anchor, Badge, Button, Divider, Group, Modal, NumberInput, Progress, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../../components/Card";
import { numberInputValue } from "../../lib/numberInput";
import {
  centavos, pesos, useCrearPago, useEnviarRep, useSugerencias, type Candidato, type FacturaCobranza, type PagoDetalle,
} from "./api";

type Resultado = PagoDetalle & { rep?: PagoDetalle["rep_vigente"]; rep_error?: string };

const FORMAS_PAGO = [
  { value: "03", label: "03 · Transferencia" },
  { value: "01", label: "01 · Efectivo" },
  { value: "02", label: "02 · Cheque" },
  { value: "04", label: "04 · Tarjeta de crédito" },
  { value: "28", label: "28 · Tarjeta de débito" },
  { value: "99", label: "99 · Por definir" },
];

function CandidatoCard({ c, titulo, color, onUsar }: { c: Candidato; titulo: string; color: string; onUsar: () => void }) {
  return (
    <Card style={{ padding: 12 }}>
      <Group justify="space-between" mb={4}>
        <Group gap="xs">
          <Badge color={color} variant="light">{titulo}</Badge>
          <Text size="xs" c="dimmed">{c.explicacion}</Text>
        </Group>
        <Button size="xs" variant="light" onClick={onUsar}>Usar</Button>
      </Group>
      <Stack gap={2}>
        {c.facturas.map((f) => (
          <Text size="xs" key={f.factura_id}>
            <b>{f.folio}</b> · <Link to={`/admin/servicios/${f.servicio.id}`}>Servicio #{f.servicio.numero}</Link> ·{" "}
            {fechaCorta(f.fecha_emision)} · {f.servicio.ruta_resumen} · {pesos(c.aplicaciones.find((a) => a.factura_id === f.factura_id)?.monto ?? f.saldo)}
          </Text>
        ))}
      </Stack>
    </Card>
  );
}

export function RegistrarPagoPanel({
  clienteId, facturas, seleccion, setSeleccion, montoInicial = null,
}: {
  clienteId: string | null;
  facturas: FacturaCobranza[];
  seleccion: Record<string, number>; // factura_id -> centavos
  setSeleccion: (s: Record<string, number>) => void;
  montoInicial?: number | null;
}) {
  const [monto, setMonto] = useState<number | null>(montoInicial);
  const [fecha, setFecha] = useState(hoyMexico());
  const [forma, setForma] = useState<string | null>("03");
  const [referencia, setReferencia] = useState("");
  const [notas, setNotas] = useState("");
  const [debounced] = useDebouncedValue(monto, 300);
  const { data: sug, isFetching } = useSugerencias(clienteId, debounced);
  const crear = useCrearPago();
  const enviarRep = useEnviarRep();
  // Confirmación previa (`05 §6`: emitir un REP es fiscal) y resultado que se queda a la vista.
  const [confirmar, setConfirmar] = useState<boolean | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);

  const montoCents = monto ? centavos(monto) : 0;
  const aplicado = Object.values(seleccion).reduce((a, b) => a + b, 0);
  const cuadra = montoCents > 0 && aplicado === montoCents;

  const usar = (c: Candidato) =>
    setSeleccion(Object.fromEntries(c.aplicaciones.map((a) => [a.factura_id, centavos(a.monto)])));

  const enviar = (emitirRep: boolean) => {
    if (!clienteId || !monto || !forma) return;
    crear.mutate(
      {
        cliente_id: clienteId,
        fecha_pago: `${fecha}T12:00:00-06:00`,
        monto: monto.toFixed(2),
        forma_pago: forma,
        num_operacion: referencia || undefined,
        notas: notas || undefined,
        aplicaciones: Object.entries(seleccion).map(([factura_id, c]) => ({ factura_id, monto: (c / 100).toFixed(2) })),
        emitir_rep: emitirRep,
      },
      {
        onSuccess: (pago) => {
          setResultado(pago as Resultado);
          setSeleccion({}); setMonto(null); setReferencia(""); setNotas("");
        },
        onSettled: () => setConfirmar(null),
      },
    );
  };

  if (!clienteId) {
    return <Card><Text c="dimmed">Elige un cliente de la lista para registrar un pago.</Text></Card>;
  }

  return (
    <Card>
      <Stack gap="sm">
        <Text fw={600}>Registrar pago</Text>
        {resultado && (
          <Alert
            color={resultado.rep_error ? "yellow" : "green"}
            withCloseButton
            onClose={() => setResultado(null)}
            title={
              resultado.rep ? "Pago aplicado y REP timbrado" : resultado.rep_error ? "Pago aplicado; el REP no se timbró" : "Pago aplicado"
            }
          >
            <Stack gap={6}>
              <Text size="sm">
                {resultado.cliente.nombre_comercial} · {pesos(resultado.monto)}
              </Text>
              {resultado.rep && (
                <>
                  <Text size="xs" c="dimmed">UUID {resultado.rep.uuid_fiscal}</Text>
                  <Group gap="sm">
                    {resultado.rep.pdf_url && <Anchor href={resultado.rep.pdf_url} target="_blank" size="sm">PDF del REP</Anchor>}
                    {resultado.rep.xml_url && <Anchor href={resultado.rep.xml_url} target="_blank" size="sm">XML</Anchor>}
                    <Button
                      size="xs"
                      loading={enviarRep.isPending}
                      onClick={() => enviarRep.mutate({ id: resultado.rep!.id, body: {} })}
                    >
                      Enviar al cliente
                    </Button>
                  </Group>
                </>
              )}
              {resultado.rep_error && (
                <Text size="sm">
                  {resultado.rep_error} Reintenta el REP desde{" "}
                  <Anchor component={Link} to={`/admin/cobranza/pagos/${resultado.id}`} size="sm">el detalle del pago</Anchor>{" "}
                  (vence el {fechaCorta(resultado.vence_rep)}).
                </Text>
              )}
              {!resultado.rep && !resultado.rep_error && (
                <Text size="sm">Emite el REP antes del {fechaCorta(resultado.vence_rep)} desde "Pagos y REP".</Text>
              )}
            </Stack>
          </Alert>
        )}
        <NumberInput
          label="Monto recibido" prefix="$" decimalScale={2} fixedDecimalScale thousandSeparator="," min={0}
          data-autofocus autoFocus value={monto ?? ""} onChange={(v) => setMonto(numberInputValue(v))}
        />
        <Group grow>
          <TextInput label="Fecha de pago" type="date" value={fecha} onChange={(e) => setFecha(e.currentTarget.value)} />
          <Select label="Forma de pago" data={FORMAS_PAGO} value={forma} onChange={setForma} allowDeselect={false} />
        </Group>
        <TextInput label="Referencia bancaria" value={referencia} onChange={(e) => setReferencia(e.currentTarget.value)} />
        <TextInput label="Notas" value={notas} onChange={(e) => setNotas(e.currentTarget.value)} />

        <Divider label="Conciliación" />
        {isFetching && <Text size="xs" c="dimmed">Buscando combinaciones…</Text>}
        {sug?.excede_saldo && (
          <Alert color="red" icon={<IconAlertTriangle size={16} />}>
            El pago excede el saldo abierto del cliente por {pesos(sug.excede_saldo)}. Regístralo por el monto aplicable y
            anota el excedente en las notas.
          </Alert>
        )}
        {sug && !sug.excede_saldo && sug.exactas.length > 0 && (
          <>
            {sug.ambigua && (
              <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
                Hay {sug.exactas.length} combinaciones que suman exacto; elige la correcta.
              </Alert>
            )}
            {sug.exactas.map((c, i) => (
              <CandidatoCard key={i} c={c} titulo={i === 0 ? "Coincidencia exacta" : "Alternativa exacta"} color="green" onUsar={() => usar(c)} />
            ))}
            {sug.nota_montos_iguales && <Text size="xs" c="dimmed">Hay facturas del mismo monto; se tomaron las más antiguas.</Text>}
          </>
        )}
        {sug && !sug.excede_saldo && sug.exactas.length === 0 && sug.aproximadas.length > 0 &&
          sug.aproximadas.map((c, i) => (
            <CandidatoCard key={i} c={c} titulo={`Aproximada (dif. ${pesos(c.diferencia ?? 0)})`} color="yellow" onUsar={() => usar(c)} />
          ))}
        {sug && !sug.excede_saldo && sug.exactas.length === 0 && sug.fifo_parcial && (
          <CandidatoCard c={sug.fifo_parcial} titulo="Más antiguas (FIFO, parcial)" color="gray" onUsar={() => usar(sug.fifo_parcial!)} />
        )}

        <Text size="sm">
          Aplicado {pesos(aplicado / 100)} de {pesos(montoCents / 100)}
        </Text>
        <Progress value={montoCents ? Math.min(100, (aplicado / montoCents) * 100) : 0} color={cuadra ? "green" : "orange"} />
        {!cuadra && aplicado > 0 && montoCents > 0 && (
          <Text size="xs" c="orange">Faltan {pesos((montoCents - aplicado) / 100)} por asignar a facturas.</Text>
        )}

        <Stack gap="xs">
          <Button fullWidth disabled={!cuadra} loading={crear.isPending} onClick={() => setConfirmar(true)}>Aplicar y generar REP</Button>
          <Button fullWidth variant="default" disabled={!cuadra} loading={crear.isPending} onClick={() => setConfirmar(false)}>Solo aplicar</Button>
        </Stack>
        <Text size="xs" c="dimmed">{facturas.length} facturas abiertas · marca facturas en la tabla o usa una sugerencia.</Text>
      </Stack>
      <Modal
        opened={confirmar !== null}
        onClose={() => setConfirmar(null)}
        title={confirmar ? "Aplicar el pago y timbrar el REP" : "Aplicar el pago"}
        centered
      >
        <Stack gap="sm">
          <Text size="sm">
            Pago de <b>{pesos(montoCents / 100)}</b> del {fechaCorta(fecha)} aplicado a:
          </Text>
          {facturas
            .filter((f) => seleccion[f.id])
            .map((f) => (
              <Group key={f.id} justify="space-between" wrap="nowrap">
                <Text size="sm">
                  {f.folio} · Servicio #{f.servicio.numero}
                </Text>
                <Text size="sm">{pesos(seleccion[f.id] / 100)}</Text>
              </Group>
            ))}
          {confirmar && (
            <Text size="xs" c="dimmed">
              Se timbra el complemento de pago (REP). Para corregirlo después habrá que cancelarlo ante el SAT.
            </Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmar(null)}>Cancelar</Button>
            <Button loading={crear.isPending} onClick={() => enviar(Boolean(confirmar))}>
              {confirmar ? "Aplicar y timbrar REP" : "Aplicar"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Card>
  );
}
