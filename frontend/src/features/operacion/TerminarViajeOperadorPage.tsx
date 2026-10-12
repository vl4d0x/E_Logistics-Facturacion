// `05-ui-spec §8 Terminar viaje` — mercancías, acuse (escaneo/referencia/ninguno), hora y notas.
import {
  ActionIcon,
  Alert,
  Button,
  Checkbox,
  FileButton,
  Group,
  Modal,
  NumberInput,
  Select,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { IconAlertTriangle, IconArrowLeft, IconFileTypePdf, IconTrash, IconUpload } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { numberInputValue } from "../../lib/numberInput";
import { useAgregarAcuseOperador, useMisServicios, useTerminarViajeOperador } from "./api";
import type { ServicioDetalle, ViajeOut } from "../servicios/types";

interface MercanciaRow {
  id: string;
  mercanciaFrecuenteId: string;
  cantidad: number;
  pesoKg: number;
}

function horaActual(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function TerminarViajeOperadorPage() {
  const { id: viajeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: servicios } = useMisServicios();

  let encontrado: { servicio: ServicioDetalle; viaje: ViajeOut } | null = null;
  for (const s of servicios ?? []) {
    const viaje = s.viajes.find((v) => v.id === viajeId);
    if (viaje) {
      encontrado = { servicio: s, viaje };
      break;
    }
  }

  const terminar = useTerminarViajeOperador(encontrado?.servicio.id ?? "");
  const agregarAcuse = useAgregarAcuseOperador(encontrado?.servicio.id ?? "");

  const [filas, setFilas] = useState<MercanciaRow[] | null>(null);
  const [folio, setFolio] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [revisado, setRevisado] = useState<string[]>([]);
  const [hora, setHora] = useState(horaActual());
  const [notas, setNotas] = useState("");
  // "No pude escanear": se confirma con una advertencia y la entrega queda para re-escaneo.
  const [sinEscaneo, setSinEscaneo] = useState(false);
  const [confirmarSinEscaneo, setConfirmarSinEscaneo] = useState(false);

  if (!encontrado) return <Skeleton height={200} />;
  const { servicio, viaje } = encontrado;

  const muestraMercancias = viaje.tipo !== "recoleccion";
  const bloqueado = servicio.datos_fiscales_bloqueados;
  // El acuse (o folio, según el cliente) solo se pide al entregar; nunca en una recolección.
  const requiereAcuse = viaje.tipo !== "recoleccion";
  const modoAcuse = requiereAcuse ? servicio.cliente.modo_acuse : "ninguno";
  const CHECKS_ACUSE = [
    "Se ve todo CLARO",
    "Está ESCANEADO (no es una foto)",
    `Corresponde a ${(viaje.destino?.nombre ?? "este destino").toUpperCase()}`,
    "Está SELLADO o FIRMADO",
  ];

  const filasIniciales: MercanciaRow[] =
    filas ??
    (viaje.mercancias.length > 0
      ? viaje.mercancias.map((m) => ({
          id: m.id,
          mercanciaFrecuenteId: m.mercancia_frecuente_id ?? "",
          cantidad: m.cantidad,
          pesoKg: m.peso_kg,
        }))
      : (servicio.mercancias_cliente ?? []).map((m) => ({
          id: crypto.randomUUID(),
          mercanciaFrecuenteId: m.id,
          cantidad: 1,
          pesoKg: m.peso_kg_sugerido ?? 0,
        })));

  function actualizarFila(id: string, patch: Partial<MercanciaRow>) {
    setFilas(filasIniciales.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  }

  async function enviar(omitirAcuse = false) {
    const clientActionId = crypto.randomUUID();
    await terminar.mutateAsync({
      viajeId: viaje.id,
      payload: {
        client_action_id: clientActionId,
        terminado_at: new Date().toISOString(),
        hora_llegada: `${hora}:00`,
        notas: notas || null,
        mercancias: muestraMercancias && !bloqueado
          ? filasIniciales
              .filter((f) => f.mercanciaFrecuenteId)
              .map((f) => ({
                mercancia_frecuente_id: f.mercanciaFrecuenteId,
                cantidad: f.cantidad,
                peso_kg: f.pesoKg,
              }))
          : [],
        referencia_acuse: modoAcuse === "referencia" ? folio : null,
        acuse_omitido: omitirAcuse,
      },
    });

    if (modoAcuse === "escaneo" && archivo && !omitirAcuse) {
      await agregarAcuse.mutateAsync({
        viajeId: viaje.id,
        file: archivo,
        clientActionId: crypto.randomUUID(),
      });
    }

    navigate(`/operador/servicios/${servicio.id}`);
  }

  const enviando = terminar.isPending || agregarAcuse.isPending;
  const puedeEnviar =
    (modoAcuse !== "referencia" || folio.trim().length > 0) &&
    (modoAcuse !== "escaneo" || sinEscaneo || (archivo !== null && revisado.length === CHECKS_ACUSE.length));

  return (
    <Stack gap="lg">
      <Button
        variant="subtle"
        leftSection={<IconArrowLeft size={16} />}
        onClick={() => navigate(`/operador/servicios/${servicio.id}`)}
        px={0}
      >
        Volver
      </Button>

      <Card>
        <Text fw={700}>
          Viaje {viaje.orden} · {viaje.tipo === "recoleccion" ? "Recolección" : viaje.tipo === "entrega" ? "Entrega" : "Recolección y entrega"}
        </Text>
        <Text size="sm" c="dimmed">
          {(viaje.tipo === "recoleccion" ? viaje.origen : viaje.destino)?.nombre}
        </Text>
      </Card>

      {muestraMercancias && (
        <Card>
          <Text fw={600} mb="sm">
            Mercancías
          </Text>
          {bloqueado ? (
            <Stack gap={4}>
              {viaje.mercancias.map((m) => (
                <Text key={m.id} size="sm">
                  {m.descripcion} · {m.cantidad} · {m.peso_kg} kg
                </Text>
              ))}
            </Stack>
          ) : (
            <Stack gap="sm">
              {filasIniciales.map((f) => {
                const opciones = (servicio.mercancias_cliente ?? []).map((m) => ({
                  value: m.id,
                  label: m.nombre_humano,
                }));
                return (
                  <Group key={f.id} align="flex-end">
                    <Select
                      label="Mercancía"
                      data={opciones}
                      value={f.mercanciaFrecuenteId || null}
                      onChange={(v) => actualizarFila(f.id, { mercanciaFrecuenteId: v ?? "" })}
                      style={{ flex: 2 }}
                    />
                    <NumberInput
                      label="Cantidad"
                      value={f.cantidad}
                      min={1}
                      onChange={(v) => actualizarFila(f.id, { cantidad: numberInputValue(v) ?? 1 })}
                      style={{ flex: 1 }}
                    />
                    <NumberInput
                      label="Peso (kg)"
                      value={f.pesoKg}
                      onChange={(v) => actualizarFila(f.id, { pesoKg: numberInputValue(v) ?? 0 })}
                      style={{ flex: 1 }}
                    />
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label="Quitar mercancía"
                      mb={6}
                      onClick={() => setFilas(filasIniciales.filter((x) => x.id !== f.id))}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                );
              })}
              <Button
                variant="default"
                size="xs"
                onClick={() =>
                  setFilas([
                    ...filasIniciales,
                    { id: crypto.randomUUID(), mercanciaFrecuenteId: "", cantidad: 1, pesoKg: 0 },
                  ])
                }
              >
                + Agregar mercancía
              </Button>
            </Stack>
          )}
        </Card>
      )}

      {requiereAcuse && (
      <Card>
        <Text fw={600} mb="sm">
          {modoAcuse === "referencia" ? "Folio" : "Acuse"}
        </Text>
        {modoAcuse === "referencia" && (
          <TextInput
            label="Folio del acuse"
            value={folio}
            onChange={(e) => setFolio(e.currentTarget.value)}
            size="lg"
          />
        )}
        {modoAcuse === "escaneo" && (
          <Stack gap="sm">
            <Alert color="red" variant="light" icon={<IconAlertTriangle size={18} />} title="IMPORTANTE: revisa el acuse antes de subirlo">
              <Stack gap={6} mt={4}>
                {CHECKS_ACUSE.map((c) => (
                  <Checkbox
                    key={c}
                    label={c}
                    checked={revisado.includes(c)}
                    onChange={(e) => {
                      // Leer el valor YA: dentro del updater de setState `e.currentTarget` es null
                      // (la pantalla tronaba al marcar la primera casilla).
                      const marcado = e.currentTarget.checked;
                      setRevisado((prev) => (marcado ? [...prev, c] : prev.filter((x) => x !== c)));
                    }}
                  />
                ))}
              </Stack>
            </Alert>
            <FileButton
              onChange={(f) => {
                setArchivo(f);
                if (f) setSinEscaneo(false); // si al final sí lo escaneó, se sube normal
              }}
              accept="application/pdf"
            >
              {(props) => (
                <Button variant="default" leftSection={<IconUpload size={16} />} {...props}>
                  {archivo ? "Cambiar PDF" : "Subir acuse (PDF)"}
                </Button>
              )}
            </FileButton>
            {archivo && (
              <Group justify="space-between" wrap="nowrap">
                <Group gap={6} wrap="nowrap">
                  <IconFileTypePdf size={18} />
                  <Text size="sm" truncate>
                    {archivo.name}
                  </Text>
                </Group>
                <ActionIcon variant="subtle" color="red" aria-label="Quitar PDF" onClick={() => setArchivo(null)}>
                  <IconTrash size={14} />
                </ActionIcon>
              </Group>
            )}
            <Text size="xs" c="dimmed">
              Solo un archivo PDF por entrega.
            </Text>
            {sinEscaneo ? (
              <Alert color="orange" variant="light" icon={<IconAlertTriangle size={18} />} title="Sin escanear">
                El viaje se terminará sin acuse y la oficina tendrá que subirlo.{" "}
                <Button variant="subtle" size="compact-xs" onClick={() => setSinEscaneo(false)}>
                  Mejor sí lo escaneo
                </Button>
              </Alert>
            ) : (
              <Button variant="subtle" color="gray" size="sm" onClick={() => setConfirmarSinEscaneo(true)}>
                No pude escanear el acuse
              </Button>
            )}
          </Stack>
        )}
        {modoAcuse === "ninguno" && <Text c="dimmed">Este cliente no requiere acuse.</Text>}
      </Card>
      )}

      <Card>
        <Stack gap="sm">
          <TextInput
            label="Hora de llegada"
            type="time"
            value={hora}
            onChange={(e) => setHora(e.currentTarget.value)}
          />
          <Textarea label="Notas (opcional)" value={notas} onChange={(e) => setNotas(e.currentTarget.value)} />
        </Stack>
      </Card>

      <Button
        size="lg"
        fullWidth
        disabled={!puedeEnviar}
        loading={enviando}
        onClick={() => enviar(modoAcuse === "escaneo" && sinEscaneo)}
      >
        Viaje terminado
      </Button>

      <Modal
        opened={confirmarSinEscaneo}
        onClose={() => setConfirmarSinEscaneo(false)}
        title="¿Seguro que no vas a escanear el acuse?"
        centered
      >
        <Stack gap="sm">
          <Alert color="orange" variant="light" icon={<IconAlertTriangle size={18} />}>
            Sin el acuse escaneado <b>no se puede facturar</b> este servicio. La entrega quedará marcada como
            "Re-escaneo" y alguien de la oficina tendrá que conseguirlo y subirlo.
          </Alert>
          <Text size="sm">Si puedes, escanéalo ahora: es más rápido para todos.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmarSinEscaneo(false)}>
              Volver y escanear
            </Button>
            <Button
              color="orange"
              onClick={() => {
                setSinEscaneo(true);
                setArchivo(null);
                setConfirmarSinEscaneo(false);
              }}
            >
              Sí, terminar sin escanear
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
