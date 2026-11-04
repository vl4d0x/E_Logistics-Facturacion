// H4.8-H4.10 — detalle de factura: vista previa del PDF, envío por correo, descargas,
// duplicar el servicio y cancelación. Es también la pantalla que se abre al timbrar.
import { Alert, Anchor, Badge, Button, Group, Modal, Skeleton, Stack, Text, TextInput } from "@mantine/core";
import { IconAlertTriangle, IconCheck, IconCopy, IconDownload, IconMail } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { OrigenFacturaBadge } from "../../components/OrigenFacturaBadge";
import { hoyMexico } from "../../lib/fecha";
import { useDuplicarServicio } from "../servicios/api";
import {
  descargarFactura,
  useActualizarEstatus,
  useEnviarFactura,
  useFactura,
  usePdfFactura,
} from "./api";
import { CancelarFacturaModal } from "./components/CancelarFacturaModal";
import { ESTADO_FACTURA, pesos } from "./format";

export function FacturaDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const recienTimbrada = params.get("timbrada") === "1";
  const { data: f } = useFactura(id);
  const enviar = useEnviarFactura(id);
  const actualizarEstatus = useActualizarEstatus(id);
  const duplicar = useDuplicarServicio(f?.servicio_id ?? "");
  const [cancelando, setCancelando] = useState(false);
  const [destinatarios, setDestinatarios] = useState<string | null>(null);
  const [duplicando, setDuplicando] = useState(false);
  const [fechaDuplicado, setFechaDuplicado] = useState(hoyMexico());
  const delFacturador = f?.origen === "facturador";
  const conArchivos = Boolean(f && f.estado !== "error" && !delFacturador);
  const pdf = usePdfFactura(id, conArchivos);

  if (!f) return <Skeleton height={400} />;
  const vigente = f.estado === "timbrada" || f.estado === "cancelacion_pendiente";
  const correos = destinatarios ?? f.emails_cliente.join(", ");

  return (
    <Stack gap="md">
      {recienTimbrada && f.estado === "timbrada" && (
        <Alert color="green" icon={<IconCheck size={18} />} title="Factura timbrada">
          Revísala y envíala al cliente. Si algo está mal, cancélala (motivo 02) y vuelve a timbrar.
        </Alert>
      )}

      <Card>
        <Group justify="space-between" mb="sm">
          <Text fw={600} size="lg">
            Factura {f.serie}
            {f.folio} · {f.cliente_nombre}
          </Text>
          <Group gap={6}>
            <OrigenFacturaBadge origen={f.origen} />
            <Badge variant="light" color={ESTADO_FACTURA[f.estado].color}>
              {ESTADO_FACTURA[f.estado].label}
            </Badge>
          </Group>
        </Group>
        <Text size="sm">
          {f.servicio_id ? (
            <>
              Servicio <Link to={`/admin/servicios/${f.servicio_id}`}>#{f.servicio_numero}</Link> ·{" "}
            </>
          ) : (
            <>{f.receptor_nombre} · </>
          )}
          {f.fecha_emision ? `${new Date(f.fecha_emision).toLocaleDateString("es-MX")} · ` : ""}Subtotal{" "}
          {pesos(f.subtotal)} · IVA {pesos(f.iva_trasladado)} · Retención {pesos(f.iva_retenido)} ·{" "}
          <b>Total {pesos(f.total)}</b>
        </Text>
        {f.uuid_fiscal && (
          <Text size="xs" c="dimmed" mt={4}>
            UUID {f.uuid_fiscal}
          </Text>
        )}
        {delFacturador && (
          <Stack gap="xs" mt="md">
            <Text size="sm">
              {f.metodo_pago} · Saldo <b>{pesos(f.saldo_insoluto)}</b>
              {Number(f.pagado_externo) > 0 && <> · cobrado en el Facturador {pesos(f.pagado_externo)}</>}
            </Text>
            <Alert color="grape" variant="light">
              Se timbró en el Facturador Electrónico. Su PDF, XML, envío por correo y cancelación están en ese sistema;
              aquí cuenta para cobranza, REP y dashboard.
            </Alert>
            {f.estado === "timbrada" && f.estado_cobro !== "pagada" && f.metodo_pago === "PPD" && (
              <Group>
                <Button
                  variant="light"
                  onClick={() => navigate(`/admin/cobranza?tab=por_cobrar&cliente=${f.cliente_id}&factura=${f.id}`)}
                >
                  Registrar pago y REP
                </Button>
              </Group>
            )}
          </Stack>
        )}

        {f.estado === "error" && (
          <Alert color="red" mt="md" icon={<IconAlertTriangle size={18} />} title="No se timbró">
            {f.error_detalle ?? "Facturama rechazó el timbrado."} Corrige el dato y vuelve a timbrar desde{" "}
            <Link to={`/admin/servicios/${f.servicio_id}/facturar`}>Facturar</Link>: se reutiliza este intento.
          </Alert>
        )}

        {f.estado === "cancelacion_pendiente" && (
          <Alert color="yellow" mt="md" icon={<IconAlertTriangle size={18} />}>
            Cancelación en espera de la aceptación del receptor (hasta 3 días hábiles). Los datos del servicio siguen
            bloqueados.
            <Group mt="xs">
              <Button
                size="xs"
                variant="default"
                loading={actualizarEstatus.isPending}
                onClick={() => actualizarEstatus.mutate(undefined)}
              >
                Actualizar estatus
              </Button>
            </Group>
          </Alert>
        )}
        {f.ejercicio_anterior && f.estado === "timbrada" && (
          <Alert color="orange" mt="md" icon={<IconAlertTriangle size={18} />}>
            Es de un ejercicio anterior: el SAT puede rechazar la cancelación.
          </Alert>
        )}
      </Card>

      {conArchivos && (
        <div className="el-grid-aside">
          <Card>
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Vista previa</Text>
              {pdf.url && (
                <Anchor href={pdf.url} target="_blank" rel="noreferrer" size="sm">
                  Abrir en otra pestaña
                </Anchor>
              )}
            </Group>
            {pdf.error ? (
              <Alert color="yellow" icon={<IconAlertTriangle size={18} />}>
                No se pudo cargar la vista previa. Usa "Descargar PDF".
              </Alert>
            ) : pdf.url ? (
              <iframe
                src={`${pdf.url}#view=FitH&navpanes=0`}
                title={`Factura ${f.serie ?? ""}${f.folio ?? ""}`}
                style={{
                  width: "100%",
                  height: "min(80vh, 1000px)",
                  border: "1px solid var(--el-line)",
                  borderRadius: 8,
                }}
              />
            ) : (
              <Skeleton height={600} />
            )}
          </Card>

          <Stack gap="md" className="el-sticky-aside">
            {vigente && (
              <Card>
                <Text fw={600} mb="xs">
                  Enviar por correo
                </Text>
                <TextInput
                  label="Destinatarios (separados por coma)"
                  value={correos}
                  onChange={(e) => setDestinatarios(e.currentTarget.value)}
                />
                {f.enviado_at && (
                  <Text size="sm" c="dimmed" mt="xs">
                    Enviado el {new Date(f.enviado_at).toLocaleString("es-MX")} a {f.envio_destinatarios?.join(", ")}
                  </Text>
                )}
                {f.envio_error && (
                  <Alert color="red" mt="xs">
                    Último intento falló: {f.envio_error}
                  </Alert>
                )}
                <Button
                  mt="md"
                  fullWidth
                  leftSection={<IconMail size={16} />}
                  loading={enviar.isPending}
                  onClick={() =>
                    enviar.mutate({
                      to: correos
                        .split(",")
                        .map((c) => c.trim())
                        .filter(Boolean),
                    })
                  }
                >
                  {f.enviado_at ? "Reenviar" : "Enviar al cliente"}
                </Button>
              </Card>
            )}

            <Card>
              <Text fw={600} mb="xs">
                Acciones
              </Text>
              <Stack gap="xs">
                <Group grow>
                  <Button variant="default" leftSection={<IconDownload size={16} />} onClick={() => descargarFactura(f.id, "pdf")}>
                    PDF
                  </Button>
                  <Button variant="default" leftSection={<IconDownload size={16} />} onClick={() => descargarFactura(f.id, "xml")}>
                    XML
                  </Button>
                </Group>
                <Button variant="default" leftSection={<IconCopy size={16} />} onClick={() => setDuplicando(true)}>
                  Duplicar servicio
                </Button>
                {f.estado === "timbrada" && f.estado_cobro !== "pagada" && (
                  <Button
                    variant="light"
                    onClick={() => navigate(`/admin/cobranza?tab=por_cobrar&cliente=${f.cliente_id}&factura=${f.id}`)}
                  >
                    Registrar pago
                  </Button>
                )}
                {f.estado === "timbrada" && (
                  <Button color="red" variant="light" onClick={() => setCancelando(true)}>
                    Cancelar factura
                  </Button>
                )}
              </Stack>
            </Card>
          </Stack>
        </div>
      )}

      <CancelarFacturaModal factura={cancelando ? f : null} onClose={() => setCancelando(false)} />

      <Modal opened={duplicando} onClose={() => setDuplicando(false)} title="Duplicar servicio">
        <Stack>
          <Text size="sm">
            Se crea un servicio nuevo a partir del servicio #{f.servicio_numero}, con el mismo cliente, unidad, operador y
            ruta (sin precio, mercancías ni acuses). Lo facturas cuando se realice.
          </Text>
          <TextInput label="Fecha" type="date" value={fechaDuplicado} onChange={(e) => setFechaDuplicado(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDuplicando(false)}>
              Volver
            </Button>
            <Button
              loading={duplicar.isPending}
              disabled={!fechaDuplicado}
              onClick={() =>
                duplicar.mutate(fechaDuplicado, { onSuccess: (nuevo) => navigate(`/admin/servicios/${nuevo.id}`) })
              }
            >
              Duplicar
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
