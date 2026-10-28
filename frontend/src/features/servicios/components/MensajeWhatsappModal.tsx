// Arma el mensaje para el grupo de WhatsApp y lo copia al portapapeles. No se guarda nada:
// los campos se precargan del servicio y solo afectan el texto.
import { Button, CopyButton, Group, Modal, NumberInput, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { numberInputValue } from "../../../lib/numberInput";
import type { ServicioDetalle, ViajeOut } from "../types";
import { armarMensajeWhatsapp, type DestinoMensaje } from "./mensajeWhatsapp";

function nombreDestino(viaje: ViajeOut): string {
  const { nombre, municipio } = viaje.destino!;
  return municipio && !nombre.toLowerCase().includes(municipio.toLowerCase()) ? `${nombre} ${municipio}` : nombre;
}

function destinosIniciales(servicio: ServicioDetalle): DestinoMensaje[] {
  return servicio.viajes
    .filter((v) => v.destino)
    .map((v) => {
      const kg = v.mercancias.reduce((s, m) => s + Number(m.peso_kg), 0);
      return { nombre: nombreDestino(v), kg: kg > 0 ? kg : null, horaCita: v.hora_llegada_programada?.slice(0, 5) ?? "" };
    });
}

export function MensajeWhatsappModal({
  servicio,
  opened,
  onClose,
}: {
  servicio: ServicioDetalle;
  opened: boolean;
  onClose: () => void;
}) {
  const [operador, setOperador] = useState("");
  const [acompanantes, setAcompanantes] = useState("");
  const [unidad, setUnidad] = useState("");
  const [destinos, setDestinos] = useState<DestinoMensaje[]>([]);

  // Se precarga cada vez que se abre, con los datos vigentes del servicio (no al refrescarse
  // el servicio con el modal abierto, para no borrar lo que se va escribiendo).
  useEffect(() => {
    if (!opened) return;
    setOperador(servicio.operador.nombre.split(" ")[0]);
    setAcompanantes("");
    setUnidad(servicio.unidad.apodo);
    setDestinos(destinosIniciales(servicio));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const cambiarDestino = (i: number, cambio: Partial<DestinoMensaje>) =>
    setDestinos((prev) => prev.map((d, j) => (j === i ? { ...d, ...cambio } : d)));

  const mensaje = armarMensajeWhatsapp({ operador, acompanantes, unidad, destinos });

  return (
    <Modal opened={opened} onClose={onClose} title="Mensaje para WhatsApp" size="lg">
      <Stack>
        <Group grow wrap="wrap" align="flex-start">
          <TextInput label="Operador" value={operador} onChange={(e) => setOperador(e.currentTarget.value)} miw={160} />
          <TextInput
            label="Acompañantes"
            description="Opcional"
            placeholder="juan pablo"
            value={acompanantes}
            onChange={(e) => setAcompanantes(e.currentTarget.value)}
            miw={160}
          />
        </Group>
        <TextInput label="Unidad" value={unidad} onChange={(e) => setUnidad(e.currentTarget.value)} />

        <Text size="sm" fw={600}>
          Destinos
        </Text>
        {destinos.length === 0 && (
          <Text size="sm" c="dimmed">
            El servicio no tiene destinos.
          </Text>
        )}
        {destinos.map((d, i) => (
          <Group key={i} wrap="wrap" align="flex-end" gap="xs">
            <TextInput
              label={`${i + 1}.`}
              value={d.nombre}
              onChange={(e) => cambiarDestino(i, { nombre: e.currentTarget.value })}
              style={{ flex: "1 1 220px" }}
            />
            <NumberInput
              label="Kg"
              placeholder="Opcional"
              min={0}
              value={d.kg ?? ""}
              onChange={(v) => cambiarDestino(i, { kg: numberInputValue(v) })}
              w={110}
            />
            <TextInput
              label="Hora de cita"
              type="time"
              value={d.horaCita}
              onChange={(e) => cambiarDestino(i, { horaCita: e.currentTarget.value })}
              w={130}
            />
          </Group>
        ))}

        <Textarea label="Vista previa" value={mensaje} readOnly autosize minRows={3} />

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cerrar
          </Button>
          <CopyButton value={mensaje}>
            {({ copied, copy }) => (
              <Button
                color={copied ? "green" : undefined}
                leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                onClick={copy}
              >
                {copied ? "Copiado" : "Copiar mensaje"}
              </Button>
            )}
          </CopyButton>
        </Group>
      </Stack>
    </Modal>
  );
}
