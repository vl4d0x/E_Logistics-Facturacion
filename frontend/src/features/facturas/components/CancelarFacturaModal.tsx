// Cancelar una factura ante el SAT (`04 §8`): motivo 02/03/04 y aviso de la aceptación del
// receptor. Se usa en la lista de facturas y en su detalle.
import { Button, Group, Modal, Select, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { useCancelarFactura, type FacturaResumen } from "../api";
import { pesos } from "../format";

const MOTIVOS = [
  { value: "02", label: "02 · Comprobante emitido con errores sin relación" },
  { value: "03", label: "03 · No se llevó a cabo la operación" },
  { value: "04", label: "04 · Operación nominativa en factura global" },
];

export function CancelarFacturaModal({
  factura,
  onClose,
}: {
  factura: Pick<FacturaResumen, "id" | "serie" | "folio" | "cliente_nombre" | "total"> | null;
  onClose: () => void;
}) {
  const cancelar = useCancelarFactura(factura?.id ?? "");
  const [motivo, setMotivo] = useState<string | null>("02");

  return (
    <Modal opened={factura !== null} onClose={onClose} title="Cancelar factura" centered>
      {factura && (
        <Stack>
          <Text size="sm">
            Factura {factura.serie}
            {factura.folio} a <b>{factura.cliente_nombre}</b> por <b>{pesos(factura.total)}</b>.
          </Text>
          <Select label="Motivo" data={MOTIVOS} value={motivo} onChange={setMotivo} allowDeselect={false} />
          <Text size="sm" c="dimmed">
            Con más de $1,000 el receptor debe aceptar la cancelación; la factura puede quedar “en espera”.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Volver
            </Button>
            <Button
              color="red"
              loading={cancelar.isPending}
              onClick={() => motivo && cancelar.mutate({ motivo }, { onSuccess: onClose })}
            >
              Cancelar factura
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
