// `fase-1-catalogos.md` H1.5 — formulario de lugar (origen/destino frecuente).
import { Button, Group, NumberInput, Select, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { api, ApiError } from "../../../lib/api";
import {
  useCreateLugar,
  useUpdateLugar,
} from "../api";
import { numberInputValue } from "../../../lib/numberInput";
import type { Cliente, Lugar, LugarPayload } from "../types";

export function LugarForm({
  lugar,
  clienteIdFijo,
  nombreInicial,
  clientes,
  onCancel,
  onSaved,
}: {
  lugar: Lugar | null;
  /** Si se da (tab Lugares de un cliente), el cliente no se puede cambiar. */
  clienteIdFijo?: string;
  /** Nombre precargado al crear un lugar nuevo (lo que el admin ya había escrito al buscar). */
  nombreInicial?: string;
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
          distancia_km: lugar.distancia_km ?? null,
        }
      : {
          cliente_id: clienteIdFijo ?? null,
          nombre: nombreInicial ?? "",
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
          distancia_km: null,
        },
    validate: {
      nombre: (v) => (v.trim() ? null : "Requerido"),
      estado: (v) => (v.trim() ? null : "Requerido"),
      codigo_postal: (v) => (/^\d{5}$/.test(v.trim()) ? null : "Debe tener 5 dígitos"),
      rfc_remitente_destinatario: (v) =>
        v.trim().toUpperCase() === "XEXX010101000"
          ? "XEXX010101000 es para extranjeros: usa el RFC real o XAXX010101000"
          : null,
    },
  });

  const saving = crear.isPending || editar.isPending;
  const [buscandoCp, setBuscandoCp] = useState(false);

  // Con el CP se consulta el catálogo del SAT y se llena el estado (el admin no tiene que saber las claves).
  async function resolverCp(valor: string) {
    const cp = valor.trim();
    if (!/^\d{5}$/.test(cp)) return;
    setBuscandoCp(true);
    try {
      const r = await api.get<{ estado: string }>(`/api/v1/catalogos/codigos-postales/${cp}`);
      form.setFieldValue("estado", r.estado);
      form.clearFieldError("codigo_postal");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) form.setFieldError("codigo_postal", err.message);
    } finally {
      setBuscandoCp(false);
    }
  }
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
      distancia_km: values.distancia_km == null ? null : numberInputValue(values.distancia_km),
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

        <Group grow align="flex-start">
          <TextInput
            label="Código postal"
            required
            inputMode="numeric"
            maxLength={5}
            description={buscandoCp ? "Buscando en el catálogo del SAT…" : "El estado se llena solo"}
            {...form.getInputProps("codigo_postal")}
            onBlur={(e) => resolverCp(e.currentTarget.value)}
          />
          <TextInput
            label="Estado (clave SAT)"
            placeholder="MEX"
            required
            description="Ej. MEX, CMX, PUE"
            {...form.getInputProps("estado")}
          />
        </Group>
        <Group grow>
          <TextInput label="Calle" description="Opcional" {...form.getInputProps("calle")} />
          <TextInput label="Número exterior" description="Opcional" {...form.getInputProps("num_exterior")} />
        </Group>
        <Group grow>
          <TextInput
            label="Colonia"
            description="Opcional · clave SAT de 4 dígitos (un nombre no se manda a la Carta Porte)"
            {...form.getInputProps("colonia")}
          />
          <TextInput label="Municipio" description="Opcional · solo informativo" {...form.getInputProps("municipio")} />
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

        <NumberInput
          label="Kilómetros hasta este lugar"
          description="Se sugiere al elegirlo como destino de un viaje. Vacío = 70 km marcados “no confirmado”."
          min={0}
          decimalScale={2}
          suffix=" km"
          {...form.getInputProps("distancia_km")}
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
