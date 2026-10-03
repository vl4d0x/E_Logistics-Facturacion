// `05-ui-spec §8 Terminar viaje` — mercancías, acuse (escaneo/referencia/ninguno), hora y notas.
import { ActionIcon, Button, FileButton, Group, NumberInput, Select, Skeleton, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { IconArrowLeft, IconTrash, IconUpload } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
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
  const [archivos, setArchivos] = useState<File[]>([]);
  const [hora, setHora] = useState(horaActual());
  const [notas, setNotas] = useState("");

  if (!encontrado) return <Skeleton height={200} />;
  const { servicio, viaje } = encontrado;

  const muestraMercancias = viaje.tipo !== "recoleccion";
  const bloqueado = servicio.datos_fiscales_bloqueados;
  const modoAcuse = servicio.cliente.modo_acuse;

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

  async function enviar() {
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
      },
    });

    if (modoAcuse === "escaneo") {
      for (let i = 0; i < archivos.length; i++) {
        await agregarAcuse.mutateAsync({
          viajeId: viaje.id,
          file: archivos[i],
          clientActionId: crypto.randomUUID(),
        });
      }
    }

    navigate(`/operador/servicios/${servicio.id}`);
  }

  const enviando = terminar.isPending || agregarAcuse.isPending;
  const puedeEnviar =
    (modoAcuse !== "referencia" || folio.trim().length > 0) &&
    (modoAcuse !== "escaneo" || archivos.length > 0);

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
                      onChange={(v) => actualizarFila(f.id, { cantidad: typeof v === "number" ? v : 1 })}
                      style={{ flex: 1 }}
                    />
                    <NumberInput
                      label="Peso (kg)"
                      value={f.pesoKg}
                      onChange={(v) => actualizarFila(f.id, { pesoKg: typeof v === "number" ? v : 0 })}
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

      <Card>
        <Text fw={600} mb="sm">
          Acuse
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
          <Stack gap="xs">
            <FileButton onChange={(f) => f && setArchivos((prev) => [...prev, f])} accept="image/*">
              {(props) => (
                <Button variant="default" leftSection={<IconUpload size={16} />} {...props}>
                  Agregar página
                </Button>
              )}
            </FileButton>
            {archivos.map((a, i) => (
              <Group key={i} justify="space-between">
                <Text size="sm">
                  Página {i + 1}: {a.name}
                </Text>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  aria-label="Quitar página"
                  onClick={() => setArchivos((prev) => prev.filter((_, idx) => idx !== i))}
                >
                  <IconTrash size={14} />
                </ActionIcon>
              </Group>
            ))}
          </Stack>
        )}
        {modoAcuse === "ninguno" && <Text c="dimmed">Este cliente no requiere acuse.</Text>}
      </Card>

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

      <Button size="lg" fullWidth disabled={!puedeEnviar} loading={enviando} onClick={enviar}>
        Viaje terminado
      </Button>
    </Stack>
  );
}
