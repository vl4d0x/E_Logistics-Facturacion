// `05-ui-spec §5 LugarSelect` — combobox de lugares del cliente + globales. Al escribir un
// nombre que no existe, el botón "Agregar nuevo origen/destino" siempre queda visible al pie
// de la lista y abre el form de lugar (reutilizado de catálogos) con ese nombre ya escrito.
import { Button, Combobox, Drawer, InputBase, ScrollArea, Text, useCombobox } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { LugarForm } from "../../catalogos/components/LugarForm";
import { useLugares } from "../../catalogos/api";

function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function LugarSelect({
  clienteId,
  value,
  onChange,
  label,
  nuevoLabel = "Agregar nuevo lugar",
}: {
  clienteId: string;
  value: string | null;
  onChange: (lugarId: string | null) => void;
  label: string;
  /** Texto del botón fijo al pie, ej. "Agregar nuevo origen". */
  nuevoLabel?: string;
}) {
  const { data: lugares, refetch } = useLugares(clienteId, "");
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState<string | null>(null);
  const [nombreNuevo, setNombreNuevo] = useState("");

  const combobox = useCombobox({
    onDropdownClose: () => {
      combobox.resetSelectedOption();
      setBusqueda(null);
    },
  });

  const seleccionado = lugares?.find((l) => l.id === value);
  const texto = busqueda ?? (seleccionado ? `${seleccionado.nombre} · ${seleccionado.codigo_postal}` : "");
  const filtro = normalizar(busqueda ?? "");
  const filtrados = (lugares ?? []).filter((l) => normalizar(`${l.nombre} ${l.codigo_postal}`).includes(filtro));

  function abrirNuevo() {
    setNombreNuevo((busqueda ?? "").trim());
    combobox.closeDropdown();
    setDrawerAbierto(true);
  }

  return (
    <>
      <Combobox
        store={combobox}
        onOptionSubmit={(id) => {
          onChange(id);
          combobox.closeDropdown();
        }}
      >
        <Combobox.Target>
          <InputBase
            label={label}
            placeholder="Escribe para buscar o elige un lugar"
            rightSection={<Combobox.Chevron />}
            rightSectionPointerEvents="none"
            value={texto}
            onChange={(e) => {
              setBusqueda(e.currentTarget.value);
              combobox.openDropdown();
              combobox.updateSelectedOptionIndex();
            }}
            onClick={() => combobox.openDropdown()}
            onFocus={() => combobox.openDropdown()}
            onBlur={() => combobox.closeDropdown()}
          />
        </Combobox.Target>
        <Combobox.Dropdown>
          <Combobox.Options>
            <ScrollArea.Autosize mah={220} type="scroll">
              {filtrados.map((l) => (
                <Combobox.Option value={l.id} key={l.id} active={l.id === value}>
                  {l.nombre} · {l.codigo_postal}
                </Combobox.Option>
              ))}
              {filtrados.length === 0 && (
                <Text size="sm" c="dimmed" px="sm" py="xs">
                  Sin resultados
                </Text>
              )}
            </ScrollArea.Autosize>
          </Combobox.Options>
          <Combobox.Footer>
            <Button
              variant="light"
              color="green"
              fullWidth
              leftSection={<IconPlus size={16} />}
              // mouseDown: evita que el input pierda el foco (y cierre la lista) antes del clic.
              onMouseDown={(e) => e.preventDefault()}
              onClick={abrirNuevo}
            >
              {nuevoLabel}
            </Button>
          </Combobox.Footer>
        </Combobox.Dropdown>
      </Combobox>
      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title={nuevoLabel}
        position="right"
        size="lg"
      >
        <LugarForm
          lugar={null}
          clienteIdFijo={clienteId}
          nombreInicial={nombreNuevo}
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
