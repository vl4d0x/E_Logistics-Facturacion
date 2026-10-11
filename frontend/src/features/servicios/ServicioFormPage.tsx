// `fase-2-servicios.md` H2.1 — crear un servicio con sus viajes en una sola pantalla.
import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Radio,
  Select,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { IconAlertTriangle, IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/Card";
import { TotalConIva } from "../../components/TotalConIva";
import { calcularImpuestos } from "../../lib/money";
import { numberInputValue } from "../../lib/numberInput";
import { clientesApi, operadoresApi, unidadesApi } from "../catalogos/api";
import { useLugares } from "../catalogos/api";
import { useCrearServicio } from "./api";
import type { TimbradoModo, ViajeIn } from "./types";
import { ViajeRowEditor, type ViajeDraft } from "./components/ViajeRowEditor";

function nuevoId(): string {
  return `nuevo-${Math.random().toString(36).slice(2)}`;
}

const tieneOrigen = (v: ViajeDraft) => v.tipo === "recoleccion" || v.tipo === "recoleccion_entrega";

function draftToViajeIn(d: ViajeDraft): ViajeIn {
  return {
    tipo: d.tipo,
    origen_lugar_id: d.origen_lugar_id,
    destino_lugar_id: d.destino_lugar_id,
    origen_cp: d.origen_cp ?? null,
    destino_cp: d.destino_cp ?? null,
    distancia_km: d.distancia_km,
    notas_admin: d.notas_admin,
  };
}

export function ServicioFormPage() {
  const navigate = useNavigate();
  const crear = useCrearServicio();

  const [clienteId, setClienteId] = useState<string | null>(null);
  const [unidadId, setUnidadId] = useState<string | null>(null);
  const [operadorId, setOperadorId] = useState<string | null>(null);
  const [fecha, setFecha] = useState<string>(new Date().toISOString().slice(0, 10));
  const [notas, setNotas] = useState("");
  const [subtotal, setSubtotal] = useState<number | null>(null);
  const [timbradoAnticipado, setTimbradoAnticipado] = useState(false);
  const [timbradoModo, setTimbradoModo] = useState<TimbradoModo>("precio");
  const [viajes, setViajes] = useState<ViajeDraft[]>([]);

  const { data: clientesPage } = clientesApi.useList("true", "");
  const { data: unidadesPage } = unidadesApi.useList("true", "");
  const { data: operadoresPage } = operadoresApi.useList("true", "");
  const { data: lugaresCliente } = useLugares(clienteId, "");

  function onElegirCliente(id: string | null) {
    setClienteId(id);
    if (!id) {
      setViajes([]);
      return;
    }
    const origenPredeterminado = lugaresCliente?.find(
      (l) => l.cliente_id === id && l.es_origen_predeterminado,
    );
    setViajes([
      {
        key: nuevoId(),
        tipo: "recoleccion",
        origen_lugar_id: origenPredeterminado?.id ?? null,
        destino_lugar_id: null,
        distancia_km: null,
        notas_admin: null,
      },
    ]);
  }

  function actualizarViaje(key: string, patch: Partial<ViajeDraft>) {
    setViajes((prev) => prev.map((v) => (v.key === key ? { ...v, ...patch } : v)));
  }

  function quitarViaje(key: string) {
    setViajes((prev) => prev.filter((v) => v.key !== key));
  }

  function agregarViaje(tipo: ViajeDraft["tipo"]) {
    setViajes((prev) => [
      ...prev,
      {
        key: nuevoId(),
        tipo,
        origen_lugar_id: null,
        destino_lugar_id: null,
        distancia_km: null,
        notas_admin: null,
      },
    ]);
  }

  const unidadSeleccionada = unidadesPage?.items.find((u) => u.id === unidadId);
  const clienteSeleccionado = clientesPage?.items.find((c) => c.id === clienteId);
  const operadorSeleccionado = operadoresPage?.items.find((o) => o.id === operadorId);

  const subtotalObligatorio = timbradoAnticipado && timbradoModo === "precio";
  const puedeGuardar =
    clienteId && unidadId && operadorId && viajes.length > 0 && (!subtotalObligatorio || subtotal);

  function handleSubmit() {
    if (!clienteId || !unidadId || !operadorId) return;
    crear.mutate(
      {
        cliente_id: clienteId,
        unidad_id: unidadId,
        operador_id: operadorId,
        fecha,
        notas: notas || null,
        subtotal,
        timbrado_anticipado: timbradoAnticipado,
        timbrado_modo: timbradoAnticipado ? timbradoModo : "precio",
        viajes: viajes.map(draftToViajeIn),
      },
      {
        onSuccess: (servicio) => navigate(`/admin/servicios/${servicio.id}`),
      },
    );
  }

  return (
    <div className="el-grid-aside">
      <Stack gap="lg">
        <Card>
          <Text fw={600} mb="md">
            Datos del servicio
          </Text>
          <Stack gap="md">
            <Select
              label="Cliente"
              placeholder="Elige un cliente"
              required
              searchable
              data={(clientesPage?.items ?? []).map((c) => ({
                value: c.id,
                label: c.nombre_comercial,
              }))}
              value={clienteId}
              onChange={onElegirCliente}
            />
            <TextInput
              label="Fecha"
              type="date"
              required
              value={fecha}
              onChange={(e) => setFecha(e.currentTarget.value)}
            />
            <div>
              <Select
                label="Unidad de registro"
                placeholder="Elige por apodo"
                required
                searchable
                data={(unidadesPage?.items ?? []).map((u) => ({ value: u.id, label: u.apodo }))}
                value={unidadId}
                onChange={setUnidadId}
              />
              <Text size="xs" c="dimmed" mt={4}>
                Si participan varias camionetas, elige la que quedará en el registro y en la
                factura.
              </Text>
            </div>
            <Select
              label="Operador"
              placeholder="Elige un operador"
              required
              searchable
              data={(operadoresPage?.items ?? []).map((o) => ({ value: o.id, label: o.nombre }))}
              value={operadorId}
              onChange={setOperadorId}
            />
            <Textarea
              label="Notas"
              autosize
              minRows={2}
              value={notas}
              onChange={(e) => setNotas(e.currentTarget.value)}
            />
          </Stack>
        </Card>

        <Card>
          <Group justify="space-between" mb="md">
            <Text fw={600}>Viajes</Text>
          </Group>
          {!clienteId && (
            <Text c="dimmed" size="sm">
              Elige un cliente para empezar a agregar viajes.
            </Text>
          )}
          <Stack gap="sm">
            {viajes.map((v, i) => (
              <ViajeRowEditor
                key={v.key}
                numero={i + 1}
                viaje={v}
                origenOcupado={viajes.some((o) => o.key !== v.key && tieneOrigen(o))}
                clienteId={clienteId ?? ""}
                onChange={(patch) => actualizarViaje(v.key, patch)}
                onRemove={() => quitarViaje(v.key)}
              />
            ))}
          </Stack>
          {clienteId && (
            <Group mt="md">
              <Button
                color="green"
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={() => agregarViaje("recoleccion")}
                disabled={viajes.some(tieneOrigen)}
                title={viajes.some(tieneOrigen) ? "Un servicio solo puede tener un origen" : undefined}
              >
                Recolección
              </Button>
              <Button
                color="green"
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={() => agregarViaje("entrega")}
              >
                Entrega
              </Button>
            </Group>
          )}
        </Card>
      </Stack>

      <Stack className="el-sticky-aside" gap="lg">
        <Card>
          <Text fw={600} mb="sm">
            Se llenará solo en la Carta Porte
          </Text>
          {unidadSeleccionada ? (
            <Group gap={6}>
              <Badge variant="light">{unidadSeleccionada.placa}</Badge>
              <Badge variant="light">{unidadSeleccionada.config_vehicular}</Badge>
              <Badge variant="light">{unidadSeleccionada.perm_sct}</Badge>
              {unidadSeleccionada.poliza_resp_civil && (
                <Badge variant="light">Póliza {unidadSeleccionada.poliza_resp_civil}</Badge>
              )}
              {operadorSeleccionado && (
                <Badge variant="light">Lic. {operadorSeleccionado.num_licencia}</Badge>
              )}
            </Group>
          ) : (
            <Text size="sm" c="dimmed">
              Elige una unidad para ver sus datos.
            </Text>
          )}

          <NumberInput
            label="Subtotal"
            mt="lg"
            prefix="$"
            decimalScale={2}
            value={subtotal ?? undefined}
            onChange={(v) => setSubtotal(numberInputValue(v))}
          />
          {!subtotalObligatorio && (
            <Badge color="violet" variant="light" mt={6}>
              Opcional
            </Badge>
          )}
          <TotalConIva subtotal={subtotal} regimenReceptor={clienteSeleccionado?.regimen_receptor} />

          <Switch
            mt="md"
            label="Timbrar antes del servicio"
            description="Para clientes que piden la Carta Porte antes del traslado"
            checked={timbradoAnticipado}
            onChange={(e) => setTimbradoAnticipado(e.currentTarget.checked)}
          />
          {timbradoAnticipado && (
            <Radio.Group
              mt="sm"
              value={timbradoModo}
              onChange={(v) => setTimbradoModo(v as TimbradoModo)}
            >
              <Stack gap="xs">
                <Radio value="precio" label="Timbrar con precio" />
                <Radio value="cero" label="Timbrar con $0 y cancelar" />
              </Stack>
            </Radio.Group>
          )}
          {timbradoAnticipado && timbradoModo === "precio" && !subtotal && (
            <Alert color="yellow" icon={<IconAlertTriangle size={16} />} mt="sm">
              El subtotal es obligatorio para timbrar con precio.
            </Alert>
          )}
          {timbradoAnticipado && timbradoModo === "cero" && (
            <Alert color="blue" icon={<IconAlertTriangle size={16} />} mt="sm">
              Para cuando aún no se acuerda el precio: se timbra con un subtotal simbólico de $0.10
              {clienteSeleccionado
                ? ` (total $${calcularImpuestos(0.1, clienteSeleccionado.regimen_receptor).total.toFixed(2)} con IVA)`
                : ""}
              , podrás descargar el PDF y el XML para el cliente, y la factura se cancela
              automáticamente. Después se timbra con el precio real.
            </Alert>
          )}

          <Group justify="flex-end" mt="xl">
            <Button variant="default" onClick={() => navigate("/admin/servicios")}>
              Cancelar
            </Button>
            <Button disabled={!puedeGuardar} loading={crear.isPending} onClick={handleSubmit}>
              Crear servicio
            </Button>
          </Group>
        </Card>
      </Stack>
    </div>
  );
}
