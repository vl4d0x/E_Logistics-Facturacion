// `05-ui-spec §5 ViajeRow/ServiceBuilder` — una fila de viaje: tipo, origen/destino
// (según tipo), distancia y notas. Funciona tanto para un viaje todavía no guardado
// (modo "nuevo servicio") como para uno ya persistido (modo edición).
import { ActionIcon, Badge, Group, NumberInput, SegmentedControl, Stack, Textarea } from "@mantine/core";
import { IconLock, IconTrash } from "@tabler/icons-react";
import type { TipoViaje } from "../types";
import { LugarSelect } from "./LugarSelect";

export interface ViajeDraft {
  key: string; // id real si está persistido, o un uuid local si es nuevo
  tipo: TipoViaje;
  origen_lugar_id: string | null;
  destino_lugar_id: string | null;
  distancia_km: number | null;
  notas_admin: string | null;
  terminado?: boolean;
}

export function ViajeRowEditor({
  numero,
  viaje,
  clienteId,
  onChange,
  onRemove,
}: {
  numero: number;
  viaje: ViajeDraft;
  clienteId: string;
  onChange: (patch: Partial<ViajeDraft>) => void;
  onRemove: () => void;
}) {
  const requiereOrigen = viaje.tipo === "recoleccion" || viaje.tipo === "recoleccion_entrega";
  const requiereDestino = viaje.tipo === "entrega" || viaje.tipo === "recoleccion_entrega";

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
          { label: "Recolección", value: "recoleccion" },
          { label: "Entrega", value: "entrega" },
          { label: "Recolección y entrega", value: "recoleccion_entrega" },
        ]}
        value={viaje.tipo}
        onChange={(v) => onChange({ tipo: v as TipoViaje })}
      />

      <Group grow align="flex-start">
        {requiereOrigen && (
          <LugarSelect
            clienteId={clienteId}
            label="Origen"
            value={viaje.origen_lugar_id}
            onChange={(v) => onChange({ origen_lugar_id: v })}
          />
        )}
        {requiereDestino && (
          <LugarSelect
            clienteId={clienteId}
            label="Destino"
            value={viaje.destino_lugar_id}
            onChange={(v) => onChange({ destino_lugar_id: v })}
          />
        )}
      </Group>

      <Group grow>
        <NumberInput
          label="Distancia (km)"
          decimalScale={2}
          value={viaje.distancia_km ?? undefined}
          onChange={(v) => onChange({ distancia_km: typeof v === "number" ? v : null })}
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
