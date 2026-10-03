// `specs/05-ui-spec.md §5`: antes de "Eliminar" consulta `/uso`. Sin referencias se borra
// definitivo; con referencias se archiva (se explica por qué); con servicios activos que
// lo usan, bloqueado con la lista y enlaces para reasignar.
import { Alert, Button, Group, List, Modal, Skeleton, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import type { UsoOut } from "../types";

const ETIQUETAS_REFERENCIA: Record<string, string> = {
  mercancias: "mercancía(s)",
  lugares: "lugar(es)",
  usuarios: "acceso(s) a la app",
  servicios: "servicio(s)",
  facturas: "factura(s)",
};

function describirReferencias(referencias: Record<string, number>): string {
  const partes = Object.entries(referencias)
    .filter(([, cantidad]) => cantidad > 0)
    .map(([clave, cantidad]) => `${cantidad} ${ETIQUETAS_REFERENCIA[clave] ?? clave}`);
  return partes.join(" y ");
}

export function SmartDeleteDialog({
  opened,
  onClose,
  uso,
  isLoadingUso,
  onConfirm,
  isDeleting,
}: {
  opened: boolean;
  onClose: () => void;
  uso: UsoOut | undefined;
  isLoadingUso: boolean;
  onConfirm: () => void;
  isDeleting: boolean;
}) {
  const tieneBloqueos = (uso?.bloqueos.length ?? 0) > 0;

  return (
    <Modal opened={opened} onClose={onClose} title="Eliminar" centered>
      {isLoadingUso || !uso ? (
        <Skeleton height={60} />
      ) : tieneBloqueos ? (
        <>
          <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
            Hay servicios activos que usan este registro. Reasígnalos antes de poder
            eliminarlo o archivarlo.
          </Alert>
          <List size="sm" spacing={4}>
            {uso.bloqueos.map((b) => (
              <List.Item key={b.servicio_id}>
                Servicio #{b.numero} — {b.estado}
              </List.Item>
            ))}
          </List>
        </>
      ) : uso.accion_al_eliminar === "archivar" ? (
        <Text size="sm">
          Tiene {describirReferencias(uso.referencias)}; se <strong>archivará</strong> (podrás
          restaurarlo después) en vez de borrarse definitivamente.
        </Text>
      ) : (
        <Text size="sm">Se eliminará definitivamente. No se puede deshacer.</Text>
      )}

      <Group justify="flex-end" mt="lg">
        <Button variant="default" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          color="red"
          disabled={tieneBloqueos || isLoadingUso || !uso}
          loading={isDeleting}
          onClick={onConfirm}
        >
          {uso?.accion_al_eliminar === "archivar" ? "Archivar" : "Eliminar"}
        </Button>
      </Group>
    </Modal>
  );
}
