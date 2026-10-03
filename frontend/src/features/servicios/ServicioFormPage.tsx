// `fase-2-servicios.md` H2.1 — crear un servicio con sus viajes en una sola pantalla.
import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
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
import { clientesApi, operadoresApi, unidadesApi } from "../catalogos/api";
import { useLugares } from "../catalogos/api";
import { useCrearServicio } from "./api";
import type { ViajeIn } from "./types";
import { ViajeRowEditor, type ViajeDraft } from "./components/ViajeRowEditor";

function nuevoId(): string {
  return `nuevo-${Math.random().toString(36).slice(2)}`;
}

function draftToViajeIn(d: ViajeDraft): ViajeIn {
  return {
    tipo: d.tipo,
    origen_lugar_id: d.origen_lugar_id,
    destino_lugar_id: d.destino_lugar_id,
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
      {
        key: nuevoId(),
        tipo: "entrega",
        origen_lugar_id: null,
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

  const puedeGuardar =
    clienteId && unidadId && operadorId && viajes.length > 0 && (!timbradoAnticipado || subtotal);

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
        viajes: viajes.map(draftToViajeIn),
      },
      {
        onSuccess: (servicio) => navigate(`/admin/servicios/${servicio.id}`),
      },
    );
  }

  return (
    <Group align="flex-start" gap="lg" wrap="nowrap">
      <Stack style={{ flex: 2 }} gap="lg">
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
                clienteId={clienteId ?? ""}
                onChange={(patch) => actualizarViaje(v.key, patch)}
                onRemove={() => quitarViaje(v.key)}
              />
            ))}
          </Stack>
          {clienteId && (
            <Group mt="md">
              <Button
                variant="default"
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={() => agregarViaje("recoleccion")}
              >
                Recolección
              </Button>
              <Button
                variant="default"
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

      <Stack style={{ flex: 1, position: "sticky", top: 16 }} gap="lg">
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

          <Text fw={600} mt="lg" mb="sm">
            Qué se le pedirá al operador
          </Text>
          <Text size="sm" c="dimmed">
            {clienteSeleccionado
              ? {
                  escaneo: "Inspección de salida, mercancía y el acuse escaneado por entrega.",
                  referencia: "Inspección de salida, mercancía y el folio del acuse por entrega.",
                  ninguno: "Inspección de salida y mercancía — este cliente no pide acuse.",
                }[clienteSeleccionado.modo_acuse]
              : "Elige un cliente para ver qué le pedirá la app al operador."}
          </Text>

          <NumberInput
            label="Subtotal"
            description="Opcional, salvo si timbras antes del servicio"
            mt="lg"
            prefix="$"
            decimalScale={2}
            value={subtotal ?? undefined}
            onChange={(v) => setSubtotal(typeof v === "number" ? v : null)}
          />

          <Switch
            mt="md"
            label="Timbrar antes del servicio"
            description="Para clientes que piden la Carta Porte antes del traslado"
            checked={timbradoAnticipado}
            onChange={(e) => setTimbradoAnticipado(e.currentTarget.checked)}
          />
          {timbradoAnticipado && !subtotal && (
            <Alert color="yellow" icon={<IconAlertTriangle size={16} />} mt="sm">
              El subtotal es obligatorio para timbrar antes del servicio.
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
    </Group>
  );
}
