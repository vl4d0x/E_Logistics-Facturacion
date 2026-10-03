// `05-ui-spec §5 LugarSelect` — combobox de lugares del cliente + globales; "+ Nuevo
// lugar" abre el form de lugar (reutilizado de catálogos) y regresa con el seleccionado.
import { Drawer, Select } from "@mantine/core";
import { useState } from "react";
import { LugarForm } from "../../catalogos/components/LugarForm";
import { useLugares } from "../../catalogos/api";

const CREAR_NUEVO = "__crear_nuevo__";

export function LugarSelect({
  clienteId,
  value,
  onChange,
  label,
}: {
  clienteId: string;
  value: string | null;
  onChange: (lugarId: string | null) => void;
  label: string;
}) {
  const { data: lugares, refetch } = useLugares(clienteId, "");
  const [drawerAbierto, setDrawerAbierto] = useState(false);

  const data = [
    ...(lugares ?? []).map((l) => ({ value: l.id, label: `${l.nombre} · ${l.codigo_postal}` })),
    { value: CREAR_NUEVO, label: "+ Nuevo lugar…" },
  ];

  return (
    <>
      <Select
        label={label}
        placeholder="Elige un lugar"
        data={data}
        value={value}
        onChange={(v) => {
          if (v === CREAR_NUEVO) {
            setDrawerAbierto(true);
            return;
          }
          onChange(v);
        }}
        searchable
      />
      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title="Nuevo lugar"
        position="right"
        size="lg"
      >
        <LugarForm
          lugar={null}
          clienteIdFijo={clienteId}
          onCancel={() => setDrawerAbierto(false)}
          onSaved={async () => {
            const result = await refetch();
            const creado = result.data?.find((l) => !lugares?.some((o) => o.id === l.id));
            setDrawerAbierto(false);
            if (creado) onChange(creado.id);
          }}
        />
      </Drawer>
    </>
  );
}
