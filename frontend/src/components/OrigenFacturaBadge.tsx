// Etiqueta de las facturas importadas del Facturador Electrónico (la app anterior): no tienen
// servicio y sus archivos, correo y cancelación se manejan en ese sistema.
import { Badge, Tooltip } from "@mantine/core";

export function OrigenFacturaBadge({ origen }: { origen?: string | null }) {
  if (origen !== "facturador") return null;
  return (
    <Tooltip label="Timbrada en el Facturador Electrónico (sistema anterior). Aquí cuenta para cobranza, REP y dashboard.">
      <Badge variant="light" color="grape" tt="none">
        facturadorelectronico
      </Badge>
    </Tooltip>
  );
}
