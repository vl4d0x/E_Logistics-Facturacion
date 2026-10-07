// Barra repetida en cada catálogo: buscador + filtro Activos/Archivados + "+ Nuevo".
import { Button, Group, SegmentedControl, TextInput } from "@mantine/core";
import { IconPlus, IconSearch } from "@tabler/icons-react";
import type { ActivoFiltro } from "../api";

export function CatalogToolbar({
  q,
  onQChange,
  activo,
  onActivoChange,
  onNuevo,
  nuevoLabel,
  placeholder,
}: {
  q: string;
  onQChange: (value: string) => void;
  activo: ActivoFiltro;
  onActivoChange: (value: ActivoFiltro) => void;
  onNuevo: () => void;
  nuevoLabel: string;
  placeholder: string;
}) {
  return (
    <Group justify="space-between" mb="md" wrap="wrap" className="el-filters">
      <Group className="el-filters">
        <TextInput
          placeholder={placeholder}
          leftSection={<IconSearch size={16} />}
          value={q}
          onChange={(e) => onQChange(e.currentTarget.value)}
          w={260}
        />
        <SegmentedControl
          value={activo}
          onChange={(value) => onActivoChange(value as ActivoFiltro)}
          data={[
            { label: "Activos", value: "true" },
            { label: "Archivados", value: "false" },
            { label: "Todos", value: "todos" },
          ]}
        />
      </Group>
      <Button leftSection={<IconPlus size={16} />} onClick={onNuevo}>
        {nuevoLabel}
      </Button>
    </Group>
  );
}
