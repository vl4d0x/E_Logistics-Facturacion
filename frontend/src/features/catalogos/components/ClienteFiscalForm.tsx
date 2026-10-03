// `fase-1-catalogos.md` H1.3 — datos fiscales y de acuse del cliente.
import { Button, Group, NumberInput, Pill, PillsInput, Select, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useForm, type UseFormReturnType } from "@mantine/form";
import { useState } from "react";
import { clientesApi } from "../api";
import type { Cliente, ClientePayload } from "../types";

const AYUDA_REGIMEN: Record<string, string> = {
  fisica: "Persona física: no se retiene IVA.",
  moral: "Persona moral: se retiene 4% de IVA.",
};

const AYUDA_ACUSE: Record<string, string> = {
  escaneo: "El operador sube foto del acuse sellado.",
  referencia: "El operador solo captura el folio del acuse.",
  ninguno: "No se exige acuse (solo recolecciones, por ejemplo).",
};

export function ClienteFiscalForm({
  cliente,
  onCancel,
  onSaved,
}: {
  cliente: Cliente | null;
  onCancel: () => void;
  onSaved: (cliente: Cliente) => void;
}) {
  const crear = clientesApi.useCreate();
  const editar = clientesApi.useUpdate();

  const form = useForm<ClientePayload>({
    initialValues: cliente
      ? {
          razon_social: cliente.razon_social,
          nombre_comercial: cliente.nombre_comercial,
          rfc: cliente.rfc,
          cp_fiscal: cliente.cp_fiscal,
          regimen_fiscal: cliente.regimen_fiscal,
          regimen_receptor: cliente.regimen_receptor,
          uso_cfdi: cliente.uso_cfdi,
          metodo_pago_default: cliente.metodo_pago_default,
          modo_acuse: cliente.modo_acuse,
          emails_facturacion: cliente.emails_facturacion,
          dias_credito: cliente.dias_credito,
          requiere_folio_concepto: cliente.requiere_folio_concepto,
        }
      : {
          razon_social: "",
          nombre_comercial: "",
          rfc: "",
          cp_fiscal: "",
          regimen_fiscal: "",
          regimen_receptor: "moral",
          uso_cfdi: "G03",
          metodo_pago_default: "PPD",
          modo_acuse: "escaneo",
          emails_facturacion: [],
          dias_credito: 30,
          requiere_folio_concepto: false,
        },
    validate: {
      razon_social: (v) => (v.trim() ? null : "Requerido"),
      nombre_comercial: (v) => (v.trim() ? null : "Requerido"),
      rfc: (v) =>
        /^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/.test(v.trim().toUpperCase())
          ? null
          : "RFC inválido (12 o 13 caracteres del SAT)",
      cp_fiscal: (v) => (v.trim() ? null : "Requerido"),
      regimen_fiscal: (v) => (v.trim() ? null : "Requerido"),
    },
  });

  const saving = crear.isPending || editar.isPending;

  function handleSubmit(values: ClientePayload) {
    if (cliente) {
      editar.mutate(
        { id: cliente.id, payload: values },
        { onSuccess: (actualizado) => onSaved(actualizado) },
      );
    } else {
      crear.mutate(values, { onSuccess: (creado) => onSaved(creado) });
    }
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <Group grow>
          <TextInput label="Razón social" required {...form.getInputProps("razon_social")} />
          <TextInput
            label="Nombre comercial"
            description="Lo que se muestra en la app"
            required
            {...form.getInputProps("nombre_comercial")}
          />
        </Group>
        <Group grow>
          <TextInput
            label="RFC"
            required
            {...form.getInputProps("rfc")}
            onChange={(e) => form.setFieldValue("rfc", e.currentTarget.value.toUpperCase())}
          />
          <TextInput label="CP fiscal" required {...form.getInputProps("cp_fiscal")} />
        </Group>
        <Group grow>
          <TextInput
            label="Régimen fiscal (clave SAT)"
            placeholder="601"
            required
            {...form.getInputProps("regimen_fiscal")}
          />
          <div>
            <Select
              label="Física o moral"
              required
              data={[
                { value: "fisica", label: "Física" },
                { value: "moral", label: "Moral" },
              ]}
              {...form.getInputProps("regimen_receptor")}
            />
            <Text size="xs" c="dimmed" mt={4}>
              {AYUDA_REGIMEN[form.values.regimen_receptor]}
            </Text>
          </div>
        </Group>
        <Group grow>
          <TextInput label="Uso de CFDI" {...form.getInputProps("uso_cfdi")} />
          <Select
            label="Método de pago default"
            data={[
              { value: "PPD", label: "PPD — pago en parcialidades o diferido" },
              { value: "PUE", label: "PUE — pago en una exhibición" },
            ]}
            {...form.getInputProps("metodo_pago_default")}
          />
        </Group>
        <div>
          <Select
            label="Modo de acuse"
            required
            data={[
              { value: "escaneo", label: "Escaneo" },
              { value: "referencia", label: "Referencia" },
              { value: "ninguno", label: "Ninguno" },
            ]}
            {...form.getInputProps("modo_acuse")}
          />
          <Text size="xs" c="dimmed" mt={4}>
            {AYUDA_ACUSE[form.values.modo_acuse]}
          </Text>
        </div>
        <TagsInputEmails form={form} />
        <NumberInput
          label="Días de crédito"
          description="Para calcular antigüedad de saldos en cobranza"
          min={0}
          {...form.getInputProps("dias_credito")}
        />
        <Switch
          label="Exige su propio folio en el concepto de la factura"
          description="Ej. Chemital: pide su número de remisión dentro del concepto"
          checked={form.values.requiere_folio_concepto}
          onChange={(e) => form.setFieldValue("requiere_folio_concepto", e.currentTarget.checked)}
        />

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

// Resuelto con PillsInput (en vez de un TagsInput con validación de email por pill):
// agrega al presionar Enter/coma — simple y suficiente para un puñado de correos.
function TagsInputEmails({ form }: { form: UseFormReturnType<ClientePayload> }) {
  const [draft, setDraft] = useState("");
  const emails = form.values.emails_facturacion;

  function commit() {
    const value = draft.trim();
    if (value) {
      form.setFieldValue("emails_facturacion", [...emails, value]);
    }
    setDraft("");
  }

  return (
    <PillsInput label="Correos de facturación" description="Enter o coma para agregar">
      <Pill.Group>
        {emails.map((email, index) => (
          <Pill
            key={`${email}-${index}`}
            withRemoveButton
            onRemove={() =>
              form.setFieldValue(
                "emails_facturacion",
                emails.filter((_, i) => i !== index),
              )
            }
          >
            {email}
          </Pill>
        ))}
        <PillsInput.Field
          value={draft}
          onChange={(e) => setDraft(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              commit();
            }
          }}
          onBlur={commit}
          placeholder={emails.length === 0 ? "correo@ejemplo.mx" : ""}
        />
      </Pill.Group>
    </PillsInput>
  );
}
