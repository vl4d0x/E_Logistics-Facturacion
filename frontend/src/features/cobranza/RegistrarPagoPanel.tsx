// H5.2-H5.4 — panel "Registrar pago" con conciliación automática (`06 §3`).
import {
  Alert, Badge, Button, Divider, Group, NumberInput, Progress, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../../components/Card";
import { numberInputValue } from "../../lib/numberInput";
import {
  centavos, pesos, useCrearPago, useSugerencias, type Candidato, type FacturaCobranza,
} from "./api";

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
            {f.fecha_emision} · {f.servicio.ruta_resumen} · {pesos(c.aplicaciones.find((a) => a.factura_id === f.factura_id)?.monto ?? f.saldo)}
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
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [forma, setForma] = useState<string | null>("03");
  const [referencia, setReferencia] = useState("");
  const [notas, setNotas] = useState("");
  const [debounced] = useDebouncedValue(monto, 300);
  const { data: sug, isFetching } = useSugerencias(clienteId, debounced);
  const crear = useCrearPago();

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
      { onSuccess: () => { setSeleccion({}); setMonto(null); setReferencia(""); setNotas(""); } },
    );
  };

  if (!clienteId) {
    return <Card><Text c="dimmed">Elige un cliente de la lista para registrar un pago.</Text></Card>;
  }

  return (
    <Card>
      <Stack gap="sm">
        <Text fw={600}>Registrar pago</Text>
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
          <Button fullWidth disabled={!cuadra} loading={crear.isPending} onClick={() => enviar(true)}>Aplicar y generar REP</Button>
          <Button fullWidth variant="default" disabled={!cuadra} loading={crear.isPending} onClick={() => enviar(false)}>Solo aplicar</Button>
        </Stack>
        <Text size="xs" c="dimmed">{facturas.length} facturas abiertas · marca facturas en la tabla o usa una sugerencia.</Text>
      </Stack>
    </Card>
  );
}
