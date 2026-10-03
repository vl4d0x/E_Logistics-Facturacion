// `fase-1-catalogos.md` H1.5 — formulario de lugar (origen/destino frecuente).
import { Button, Group, Select, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import {
  useCreateLugar,
  useUpdateLugar,
} from "../api";
import type { Cliente, Lugar, LugarPayload } from "../types";

export function LugarForm({
  lugar,
  clienteIdFijo,
  clientes,
  onCancel,
  onSaved,
}: {
  lugar: Lugar | null;
  /** Si se da (tab Lugares de un cliente), el cliente no se puede cambiar. */
  clienteIdFijo?: string;
  /** Lista de clientes para el selector, solo cuando no hay `clienteIdFijo` (vista global). */
  clientes?: Cliente[];
  onCancel: () => void;
  onSaved: () => void;
}) {
  const crear = useCreateLugar();
  const editar = useUpdateLugar();

  const form = useForm<LugarPayload>({
    initialValues: lugar
      ? {
          cliente_id: lugar.cliente_id,
          nombre: lugar.nombre,
          rfc_remitente_destinatario: lugar.rfc_remitente_destinatario,
          nombre_remitente_destinatario: lugar.nombre_remitente_destinatario ?? "",
          calle: lugar.calle ?? "",
          num_exterior: lugar.num_exterior ?? "",
          colonia: lugar.colonia ?? "",
          localidad: lugar.localidad ?? "",
          municipio: lugar.municipio ?? "",
          estado: lugar.estado,
          pais: lugar.pais,
          codigo_postal: lugar.codigo_postal,
          referencia: lugar.referencia ?? "",
          es_origen_predeterminado: lugar.es_origen_predeterminado,
        }
      : {
          cliente_id: clienteIdFijo ?? null,
          nombre: "",
          rfc_remitente_destinatario: "XAXX010101000",
          nombre_remitente_destinatario: "",
          calle: "",
          num_exterior: "",
          colonia: "",
          localidad: "",
          municipio: "",
          estado: "",
          pais: "MEX",
          codigo_postal: "",
          referencia: "",
          es_origen_predeterminado: false,
        },
    validate: {
      nombre: (v) => (v.trim() ? null : "Requerido"),
      estado: (v) => (v.trim() ? null : "Requerido"),
      codigo_postal: (v) => (v.trim() ? null : "Requerido"),
    },
  });

  const saving = crear.isPending || editar.isPending;
  const clienteSeleccionable = clienteIdFijo === undefined;

  function handleSubmit(values: LugarPayload) {
    const payload = {
      ...values,
      cliente_id: clienteIdFijo ?? values.cliente_id,
      nombre_remitente_destinatario: values.nombre_remitente_destinatario || null,
      calle: values.calle || null,
      num_exterior: values.num_exterior || null,
      colonia: values.colonia || null,
      localidad: values.localidad || null,
      municipio: values.municipio || null,
      referencia: values.referencia || null,
    };
    if (lugar) {
      editar.mutate({ id: lugar.id, payload }, { onSuccess: onSaved });
    } else {
      crear.mutate(payload, { onSuccess: onSaved });
    }
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <TextInput label="Nombre" placeholder="Planta Chemital Toluca" required {...form.getInputProps("nombre")} />

        {clienteSeleccionable && (
          <Select
            label="Cliente"
            description="Vacío = lugar compartido por todos los clientes"
            clearable
            data={(clientes ?? []).map((c) => ({ value: c.id, label: c.nombre_comercial }))}
            {...form.getInputProps("cliente_id")}
          />
        )}

        <Group grow>
          <TextInput label="Calle" {...form.getInputProps("calle")} />
          <TextInput label="Número exterior" {...form.getInputProps("num_exterior")} />
        </Group>
        <Group grow>
          <TextInput label="Colonia" {...form.getInputProps("colonia")} />
          <TextInput label="Localidad" {...form.getInputProps("localidad")} />
        </Group>
        <Group grow>
          <TextInput label="Municipio" {...form.getInputProps("municipio")} />
          <TextInput label="Estado (clave SAT)" placeholder="MEX" required {...form.getInputProps("estado")} />
        </Group>
        <Group grow>
          <TextInput label="País" {...form.getInputProps("pais")} />
          <TextInput label="Código postal" required {...form.getInputProps("codigo_postal")} />
        </Group>

        <div>
          <TextInput
            label="RFC del remitente/destinatario"
            {...form.getInputProps("rfc_remitente_destinatario")}
          />
          <Text size="xs" c="dimmed" mt={4}>
            Usa el RFC real si lo conoces; si no, deja el genérico XAXX010101000.
          </Text>
        </div>
        <TextInput
          label="Nombre del remitente/destinatario"
          {...form.getInputProps("nombre_remitente_destinatario")}
        />
        <TextInput
          label="Referencia"
          placeholder="Entrada por calle lateral…"
          {...form.getInputProps("referencia")}
        />

        {(clienteIdFijo ?? form.values.cliente_id) && (
          <Switch
            label="Origen predeterminado de este cliente"
            description="Se precarga al crear servicios; marcar otro desmarca este"
            {...form.getInputProps("es_origen_predeterminado", { type: "checkbox" })}
          />
        )}

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
