// Menú `…` por fila — `05-ui-spec §7.5`: Editar, Eliminar (SmartDeleteDialog), Restaurar.
import { ActionIcon, Menu } from "@mantine/core";
import { IconDotsVertical, IconEdit, IconRestore, IconTrash } from "@tabler/icons-react";

export function RowActionsMenu({
  activo,
  onEditar,
  onEliminar,
  onRestaurar,
}: {
  activo: boolean;
  onEditar: () => void;
  onEliminar: () => void;
  onRestaurar: () => void;
}) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon variant="subtle" color="gray" aria-label="Más acciones">
          <IconDotsVertical size={18} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {activo ? (
          <>
            <Menu.Item leftSection={<IconEdit size={16} />} onClick={onEditar}>
              Editar
            </Menu.Item>
            <Menu.Item leftSection={<IconTrash size={16} />} color="red" onClick={onEliminar}>
              Eliminar
            </Menu.Item>
          </>
        ) : (
          <Menu.Item leftSection={<IconRestore size={16} />} onClick={onRestaurar}>
            Restaurar
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  );
}
