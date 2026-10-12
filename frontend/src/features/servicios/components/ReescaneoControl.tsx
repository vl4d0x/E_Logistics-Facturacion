// Etiqueta "Re-escaneo" de una entrega: cualquier admin la pide (el acuse falta o está mal
// tomado) y otro la resuelve subiendo el escaneo; al subirlo, la etiqueta se quita sola.
import { Alert, Button, FileButton, Group, Modal, Radio, Stack, Text, Textarea } from "@mantine/core";
import { IconAlertTriangle, IconScan, IconUpload } from "@tabler/icons-react";
import { useState } from "react";
import { useAgregarAcuseArchivo, useReescaneo } from "../api";
import type { Reescaneo } from "../types";

const MOTIVOS = [
  "No se subió el acuse",
  "Está borroso o mal tomado",
  "Es una foto, no un escaneo",
  "No corresponde a este destino",
  "No tiene sello ni firma",
];

export function ReescaneoControl({
  servicioId,
  viajeId,
  destino,
  reescaneo,
}: {
  servicioId: string;
  viajeId: string;
  destino: string;
  reescaneo: Reescaneo | null | undefined;
}) {
  const marcar = useReescaneo(servicioId);
  const subir = useAgregarAcuseArchivo(servicioId);
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState(MOTIVOS[1]);
  const [otro, setOtro] = useState("");

  if (reescaneo) {
    return (
      <Alert color="orange" variant="light" icon={<IconAlertTriangle size={18} />} title="Re-escaneo pendiente">
        <Stack gap={6}>
          <Text size="sm">
            {reescaneo.motivo ?? "Hay que volver a escanear el acuse"}
            {reescaneo.solicitado_por ? ` · lo pidió ${reescaneo.solicitado_por}` : ""} ·{" "}
            {new Date(reescaneo.solicitado_at).toLocaleDateString("es-MX")}
          </Text>
          <Group gap="xs">
            <FileButton accept="application/pdf" onChange={(f) => f && subir.mutate({ viajeId, file: f })}>
              {(props) => (
                <Button size="xs" leftSection={<IconUpload size={14} />} loading={subir.isPending} {...props}>
                  Subir escaneo (PDF)
                </Button>
              )}
            </FileButton>
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              loading={marcar.isPending}
              onClick={() => marcar.mutate({ viajeId, quitar: true })}
            >
              Quitar solicitud
            </Button>
          </Group>
        </Stack>
      </Alert>
    );
  }

  return (
    <>
      <Button size="xs" variant="light" color="orange" leftSection={<IconScan size={14} />} onClick={() => setAbierto(true)}>
        Solicitar re-escaneo
      </Button>
      <Modal opened={abierto} onClose={() => setAbierto(false)} title={`Solicitar re-escaneo · ${destino}`} centered>
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            La entrega queda con la etiqueta "Re-escaneo" para que otro admin suba el acuse. No se puede timbrar hasta
            que se suba.
          </Text>
          <Radio.Group value={motivo} onChange={setMotivo}>
            <Stack gap={6}>
              {[...MOTIVOS, "Otro"].map((m) => (
                <Radio key={m} value={m} label={m} />
              ))}
            </Stack>
          </Radio.Group>
          {motivo === "Otro" && (
            <Textarea placeholder="Describe el problema" value={otro} onChange={(e) => setOtro(e.currentTarget.value)} autosize />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAbierto(false)}>
              Volver
            </Button>
            <Button
              color="orange"
              loading={marcar.isPending}
              disabled={motivo === "Otro" && !otro.trim()}
              onClick={() =>
                marcar.mutate(
                  { viajeId, motivo: motivo === "Otro" ? otro.trim() : motivo },
                  { onSuccess: () => setAbierto(false) },
                )
              }
            >
              Solicitar re-escaneo
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
