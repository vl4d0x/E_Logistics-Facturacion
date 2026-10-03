// `fase-1-catalogos.md` H1.1 — CRUD de unidades.
import {
  Alert,
  Badge,
  Button,
  Drawer,
  Group,
  NumberInput,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { Card } from "../../components/Card";
import { type ActivoFiltro, unidadesApi } from "./api";
import { CatalogToolbar } from "./components/CatalogToolbar";
import { FuelGaugePreview } from "./components/FuelGaugePreview";
import { RowActionsMenu } from "./components/RowActionsMenu";
import { SmartDeleteDialog } from "./components/SmartDeleteDialog";
import type { TipoMedidor, Unidad, UnidadPayload } from "./types";

const VALORES_INICIALES: UnidadPayload = {
  apodo: "",
  placa: "",
  anio_modelo: null,
  config_vehicular: "",
  peso_bruto_vehicular: 0,
  capacidad_carga_kg: null,
  perm_sct: "",
  num_permiso_sct: "",
  aseguradora_resp_civil: "",
  poliza_resp_civil: "",
  tipo_medidor: "aguja",
  num_barras: null,
  capacidad_tanque_l: null,
  tipo_combustible: "",
};

function UnidadForm({
  unidad,
  onCancel,
  onSaved,
}: {
  unidad: Unidad | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const crear = unidadesApi.useCreate();
  const editar = unidadesApi.useUpdate();

  const form = useForm<UnidadPayload>({
    initialValues: unidad
      ? {
          apodo: unidad.apodo,
          placa: unidad.placa,
          anio_modelo: unidad.anio_modelo,
          config_vehicular: unidad.config_vehicular,
          peso_bruto_vehicular: unidad.peso_bruto_vehicular,
          capacidad_carga_kg: unidad.capacidad_carga_kg,
          perm_sct: unidad.perm_sct,
          num_permiso_sct: unidad.num_permiso_sct,
          aseguradora_resp_civil: unidad.aseguradora_resp_civil ?? "",
          poliza_resp_civil: unidad.poliza_resp_civil ?? "",
          tipo_medidor: unidad.tipo_medidor,
          num_barras: unidad.num_barras,
          capacidad_tanque_l: unidad.capacidad_tanque_l,
          tipo_combustible: unidad.tipo_combustible ?? "",
        }
      : VALORES_INICIALES,
    validate: {
      apodo: (v) => (v.trim() ? null : "Requerido"),
      placa: (v) => (v.trim() ? null : "Requerido"),
      config_vehicular: (v) => (v.trim() ? null : "Requerido"),
      perm_sct: (v) => (v.trim() ? null : "Requerido"),
      num_permiso_sct: (v) => (v.trim() ? null : "Requerido"),
      peso_bruto_vehicular: (v) => (v > 0 ? null : "Requerido, mayor a 0"),
      num_barras: (v, values) =>
        values.tipo_medidor === "barras" && !(v !== null && v >= 2 && v <= 20)
          ? "Obligatorio, entre 2 y 20 si el medidor es de barras"
          : null,
    },
  });

  const pesoPareceKg = form.values.peso_bruto_vehicular > 100;
  const saving = crear.isPending || editar.isPending;

  function handleSubmit(values: UnidadPayload) {
    const payload = { ...values, aseguradora_resp_civil: values.aseguradora_resp_civil || null, poliza_resp_civil: values.poliza_resp_civil || null, tipo_combustible: values.tipo_combustible || null };
    const onSuccess = { onSuccess: onSaved };
    if (unidad) {
      editar.mutate({ id: unidad.id, payload }, onSuccess);
    } else {
      crear.mutate(payload, onSuccess);
    }
  }

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <Group grow>
          <TextInput label="Apodo" placeholder="Saveiro Blanca" required {...form.getInputProps("apodo")} />
          <TextInput label="Placa" required {...form.getInputProps("placa")} />
        </Group>
        <NumberInput
          label="Año modelo"
          {...form.getInputProps("anio_modelo")}
          clampBehavior="strict"
          min={1980}
          max={2100}
        />

        <Text size="sm" fw={600} mt="sm">
          Carta Porte
        </Text>
        <Group grow>
          <TextInput
            label="Configuración vehicular (clave SAT)"
            placeholder="VL"
            required
            {...form.getInputProps("config_vehicular")}
          />
          <div>
            <NumberInput
              label="Peso bruto vehicular (en toneladas)"
              required
              decimalScale={2}
              {...form.getInputProps("peso_bruto_vehicular")}
            />
            {pesoPareceKg && (
              <Text size="xs" c="var(--el-warning-text)" mt={4}>
                ¿Seguro? Es en toneladas, no en kg — {form.values.peso_bruto_vehicular} parece kg.
              </Text>
            )}
          </div>
        </Group>
        <NumberInput
          label="Capacidad de carga (kg)"
          decimalScale={2}
          {...form.getInputProps("capacidad_carga_kg")}
        />
        <Group grow>
          <TextInput
            label="Tipo de permiso SCT (clave)"
            placeholder="TPAF14"
            required
            {...form.getInputProps("perm_sct")}
          />
          <TextInput label="Número de permiso SCT" required {...form.getInputProps("num_permiso_sct")} />
        </Group>
        <Group grow>
          <TextInput label="Aseguradora (resp. civil)" {...form.getInputProps("aseguradora_resp_civil")} />
          <TextInput label="Póliza (resp. civil)" {...form.getInputProps("poliza_resp_civil")} />
        </Group>

        <Text size="sm" fw={600} mt="sm">
          Medidor de gasolina
        </Text>
        <SegmentedControl
          data={[
            { label: "Aguja", value: "aguja" },
            { label: "Barras", value: "barras" },
          ]}
          {...form.getInputProps("tipo_medidor")}
          onChange={(value) => form.setFieldValue("tipo_medidor", value as TipoMedidor)}
        />
        {form.values.tipo_medidor === "barras" && (
          <NumberInput
            label="Número de barras del tablero"
            min={2}
            max={20}
            {...form.getInputProps("num_barras")}
          />
        )}
        <FuelGaugePreview tipoMedidor={form.values.tipo_medidor} numBarras={form.values.num_barras} />
        <Group grow>
          <NumberInput
            label="Capacidad del tanque (litros)"
            decimalScale={2}
            {...form.getInputProps("capacidad_tanque_l")}
          />
          <TextInput
            label="Tipo de combustible"
            placeholder="Magna, Premium, Diésel…"
            {...form.getInputProps("tipo_combustible")}
          />
        </Group>

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

export function UnidadesPage() {
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [q, setQ] = useState("");
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [unidadEditando, setUnidadEditando] = useState<Unidad | null>(null);
  const [unidadEliminando, setUnidadEliminando] = useState<Unidad | null>(null);

  const { data, isLoading, isError } = unidadesApi.useList(activo, q);
  const uso = unidadesApi.useUso(unidadEliminando?.id ?? null);
  const eliminar = unidadesApi.useDelete();
  const restaurar = unidadesApi.useRestore();

  function abrirNuevo() {
    setUnidadEditando(null);
    setDrawerAbierto(true);
  }

  function abrirEditar(unidad: Unidad) {
    setUnidadEditando(unidad);
    setDrawerAbierto(true);
  }

  return (
    <Card>
      <CatalogToolbar
        q={q}
        onQChange={setQ}
        activo={activo}
        onActivoChange={setActivo}
        onNuevo={abrirNuevo}
        nuevoLabel="Nueva unidad"
        placeholder="Buscar por apodo o placa…"
      />

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar las unidades.
        </Alert>
      )}

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Apodo</Table.Th>
            <Table.Th>Placa</Table.Th>
            <Table.Th>Año</Table.Th>
            <Table.Th>Medidor</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data?.items.map((unidad) => (
            <Table.Tr key={unidad.id}>
              <Table.Td>{unidad.apodo}</Table.Td>
              <Table.Td>{unidad.placa}</Table.Td>
              <Table.Td>{unidad.anio_modelo ?? "—"}</Table.Td>
              <Table.Td style={{ textTransform: "capitalize" }}>
                {unidad.tipo_medidor}
                {unidad.tipo_medidor === "barras" ? ` (${unidad.num_barras})` : ""}
              </Table.Td>
              <Table.Td>
                <Badge color={unidad.activo ? "green" : "gray"} variant="light">
                  {unidad.activo ? "Activa" : "Archivada"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <RowActionsMenu
                  activo={unidad.activo}
                  onEditar={() => abrirEditar(unidad)}
                  onEliminar={() => setUnidadEliminando(unidad)}
                  onRestaurar={() => restaurar.mutate(unidad.id)}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {!isLoading && data?.items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin unidades {activo === "false" ? "archivadas" : "registradas"}.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title={unidadEditando ? `Editar ${unidadEditando.apodo}` : "Nueva unidad"}
        position="right"
        size="lg"
      >
        <UnidadForm
          unidad={unidadEditando}
          onCancel={() => setDrawerAbierto(false)}
          onSaved={() => setDrawerAbierto(false)}
        />
      </Drawer>

      <SmartDeleteDialog
        opened={unidadEliminando !== null}
        onClose={() => setUnidadEliminando(null)}
        uso={uso.data}
        isLoadingUso={uso.isLoading}
        isDeleting={eliminar.isPending}
        onConfirm={() =>
          unidadEliminando &&
          eliminar.mutate(unidadEliminando.id, { onSuccess: () => setUnidadEliminando(null) })
        }
      />
    </Card>
  );
}
