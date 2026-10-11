// `05-ui-spec §5 ViajeRow/ServiceBuilder` — una fila de viaje: tipo, origen/destino
// (según tipo) con su código postal editable, distancia y notas. Funciona tanto para un
// viaje todavía no guardado (modo "nuevo servicio") como para uno ya persistido.
import {
  ActionIcon,
  Badge,
  Group,
  NumberInput,
  SegmentedControl,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { IconLock, IconTrash } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { numberInputValue } from "../../../lib/numberInput";
import { useLugares } from "../../catalogos/api";
import { fetchDistanciaSugerida } from "../api";
import type { TipoViaje } from "../types";
import { LugarSelect } from "./LugarSelect";

export interface ViajeDraft {
  key: string; // id real si está persistido, o un uuid local si es nuevo
  tipo: TipoViaje;
  origen_lugar_id: string | null;
  destino_lugar_id: string | null;
  /** CP distinto al del lugar, solo para este viaje (null = el del lugar). */
  origen_cp?: string | null;
  destino_cp?: string | null;
  distancia_km: number | null;
  notas_admin: string | null;
  terminado?: boolean;
}

/** Casilla de CP: muestra el del lugar y deja escribir otro distinto para este viaje. */
function CpField({
  label,
  cpLugar,
  override,
  onOverride,
  disabled,
}: {
  label: string;
  cpLugar: string;
  override: string | null | undefined;
  onOverride: (cp: string | null) => void;
  disabled?: boolean;
}) {
  const [texto, setTexto] = useState<string | null>(override ?? null);
  const mostrado = texto ?? cpLugar;
  const invalido = mostrado !== "" && !/^\d{5}$/.test(mostrado);
  const distinto = /^\d{5}$/.test(mostrado) && mostrado !== cpLugar;

  return (
    <TextInput
      label={label}
      inputMode="numeric"
      maxLength={5}
      disabled={disabled}
      value={mostrado}
      error={invalido ? "5 dígitos" : undefined}
      description={distinto ? "Distinto al del lugar (solo este viaje)" : undefined}
      onChange={(e) => {
        const v = e.currentTarget.value.replace(/\D/g, "").slice(0, 5);
        setTexto(v);
        onOverride(/^\d{5}$/.test(v) && v !== cpLugar ? v : null);
      }}
      onBlur={() => {
        if (!/^\d{5}$/.test(mostrado)) setTexto(null); // incompleto: vuelve al CP del lugar
      }}
    />
  );
}

export function ViajeRowEditor({
  numero,
  viaje,
  clienteId,
  onChange,
  onRemove,
  origenOcupado = false,
}: {
  numero: number;
  viaje: ViajeDraft;
  clienteId: string;
  /** Otro viaje del servicio ya tiene el origen: solo se permiten entregas aquí. */
  origenOcupado?: boolean;
  onChange: (patch: Partial<ViajeDraft>) => void;
  onRemove: () => void;
}) {
  const requiereOrigen = viaje.tipo === "recoleccion" || viaje.tipo === "recoleccion_entrega";
  const requiereDestino = viaje.tipo === "entrega" || viaje.tipo === "recoleccion_entrega";

  const { data: lugares } = useLugares(clienteId, "");
  const cpDe = (id: string | null) => lugares?.find((l) => l.id === id)?.codigo_postal ?? "";

  // Km sugerido por destino: solo pisa el campo si está vacío o si aún tiene el valor que
  // puso la sugerencia (si el admin lo tecleó, se respeta). Sin km del cliente se sugieren
  // 70 y se marcan "no confirmado" hasta que el admin los edite.
  const kmAutomatico = useRef<number | null>(null);
  const [kmNoConfirmado, setKmNoConfirmado] = useState(false);

  async function sugerirKm(lugarId: string) {
    const sugerida = await fetchDistanciaSugerida(lugarId);
    if (sugerida == null) return;
    if (viaje.distancia_km == null || viaje.distancia_km === kmAutomatico.current) {
      kmAutomatico.current = sugerida.km;
      setKmNoConfirmado(!sugerida.confirmado);
      onChange({ distancia_km: sugerida.km });
    }
  }

  // El km sale del lugar del viaje: el destino si lo tiene; en una recolección (sin destino),
  // el lugar donde se recoge. Se dispara al elegir el lugar a mano o al precargarse solo (el
  // origen predeterminado del cliente).
  const lugarDelKm = requiereDestino ? viaje.destino_lugar_id : viaje.origen_lugar_id;
  useEffect(() => {
    if (lugarDelKm) void sugerirKm(lugarDelKm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lugarDelKm]);

  function elegirDestino(destinoId: string | null) {
    onChange({ destino_lugar_id: destinoId, destino_cp: null });
  }

  function elegirOrigen(origenId: string | null) {
    onChange({ origen_lugar_id: origenId, origen_cp: null });
  }

  return (
    <Stack
      gap="xs"
      p="sm"
      style={{ border: "1px solid var(--el-line)", borderRadius: 10 }}
    >
      <Group justify="space-between">
        <Group gap="xs">
          <Badge variant="light" color="gray">
            Viaje {numero}
          </Badge>
          {viaje.terminado && (
            <Badge leftSection={<IconLock size={12} />} color="gray" variant="light">
              Terminado
            </Badge>
          )}
        </Group>
        <ActionIcon
          variant="subtle"
          color="red"
          aria-label="Quitar viaje"
          disabled={viaje.terminado}
          onClick={onRemove}
        >
          <IconTrash size={16} />
        </ActionIcon>
      </Group>

      <SegmentedControl
        disabled={viaje.terminado}
        data={[
          { label: "Recolección", value: "recoleccion", disabled: origenOcupado },
          { label: "Entrega", value: "entrega" },
          { label: "Recolección y entrega", value: "recoleccion_entrega", disabled: origenOcupado },
        ]}
        value={viaje.tipo}
        onChange={(v) => onChange({ tipo: v as TipoViaje })}
      />

      <Group grow align="flex-start">
        {requiereOrigen && (
          <Stack gap="xs">
            <LugarSelect
              clienteId={clienteId}
              label="Origen"
              nuevoLabel="Agregar nuevo origen"
              value={viaje.origen_lugar_id}
              onChange={elegirOrigen}
            />
            {viaje.origen_lugar_id && (
              <CpField
                key={`o-${viaje.origen_lugar_id}`}
                label="Código postal del origen"
                cpLugar={cpDe(viaje.origen_lugar_id)}
                override={viaje.origen_cp}
                onOverride={(cp) => onChange({ origen_cp: cp })}
                disabled={viaje.terminado}
              />
            )}
          </Stack>
        )}
        {requiereDestino && (
          <Stack gap="xs">
            <LugarSelect
              clienteId={clienteId}
              label="Destino"
              nuevoLabel="Agregar nuevo destino"
              value={viaje.destino_lugar_id}
              onChange={elegirDestino}
            />
            {viaje.destino_lugar_id && (
              <CpField
                key={`d-${viaje.destino_lugar_id}`}
                label="Código postal del destino"
                cpLugar={cpDe(viaje.destino_lugar_id)}
                override={viaje.destino_cp}
                onOverride={(cp) => onChange({ destino_cp: cp })}
                disabled={viaje.terminado}
              />
            )}
          </Stack>
        )}
      </Group>

      <Group grow>
        <NumberInput
          label={
            <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
              Distancia (km)
              {kmNoConfirmado && (
                <Badge size="xs" color="yellow" variant="light">
                  No confirmado
                </Badge>
              )}
            </span>
          }
          decimalScale={2}
          value={viaje.distancia_km ?? undefined}
          onChange={(v) => {
            setKmNoConfirmado(false); // lo capturó el admin: ya cuenta como confirmado
            onChange({ distancia_km: numberInputValue(v) });
          }}
        />
      </Group>
      <Textarea
        label="Notas para este viaje"
        autosize
        minRows={1}
        value={viaje.notas_admin ?? ""}
        onChange={(e) => onChange({ notas_admin: e.currentTarget.value })}
      />
    </Stack>
  );
}
