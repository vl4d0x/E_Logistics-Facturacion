// Edición manual dentro de la pantalla Facturar: ruta (CP, hora, km), mercancías, unidad y
// operador. Cada cambio se guarda al salir del campo y refresca el detalle; con factura
// vigente el servidor responde 409 y se avisa (hay que cancelar la factura primero).
import { ActionIcon, Badge, Button, Group, NumberInput, Select, Stack, Table, Text, TextInput } from "@mantine/core";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { numberInputValue } from "../../../lib/numberInput";
import { operadoresApi, unidadesApi, useMercancias } from "../../catalogos/api";
import { fetchDistanciaSugerida, useAgregarViaje, useEditarServicio, useEditarViaje, useEliminarViaje } from "../../servicios/api";
import { LugarSelect } from "../../servicios/components/LugarSelect";
import { useGuardarMercancias } from "../api";
import type { FacturacionDetalle, MercanciaFacturar, Ubicacion } from "../types";

// --- Ruta y ubicaciones ------------------------------------------------------

export function RutaEditable({
  servicioId,
  clienteId,
  ubicaciones,
}: {
  servicioId: string;
  clienteId: string | null | undefined;
  ubicaciones: Ubicacion[];
}) {
  const editar = useEditarViaje(servicioId);
  const eliminar = useEliminarViaje(servicioId);
  const agregar = useAgregarViaje(servicioId);
  const [nuevoOrigen, setNuevoOrigen] = useState<string | null>(null);
  const [nuevoDestino, setNuevoDestino] = useState<string | null>(null);
  const hayOrigen = ubicaciones.some((u) => u.tipo === "Origen");

  // Cambiar el lugar de una ubicación; en un destino se vuelve a sugerir su km.
  async function cambiarLugar(u: Ubicacion, lugarId: string | null) {
    if (!lugarId || lugarId === u.lugar.id) return;
    if (u.tipo === "Origen") {
      editar.mutate({ id: u.viaje_id, payload: { origen_lugar_id: lugarId, origen_cp: null } });
      return;
    }
    const km = (await fetchDistanciaSugerida(lugarId))?.km ?? null;
    editar.mutate({ id: u.viaje_id, payload: { destino_lugar_id: lugarId, destino_cp: null, distancia_km: km } });
  }

  // Quitar una ubicación: si el viaje solo tenía esa, se elimina; si era "recolección y
  // entrega", se queda con la otra mitad.
  function quitar(u: Ubicacion) {
    const que = u.tipo === "Origen" ? "origen" : "destino";
    if (!window.confirm(`¿Quitar este ${que} (${u.lugar.nombre ?? "sin nombre"}) del servicio?`)) return;
    if (u.viaje_tipo === "recoleccion_entrega") {
      editar.mutate({
        id: u.viaje_id,
        payload:
          u.tipo === "Origen"
            ? { tipo: "entrega", origen_lugar_id: null, origen_cp: null }
            : { tipo: "recoleccion", destino_lugar_id: null, destino_cp: null, distancia_km: null },
      });
    } else {
      eliminar.mutate(u.viaje_id);
    }
  }

  async function agregarOrigen() {
    if (!nuevoOrigen) return;
    agregar.mutate({ tipo: "recoleccion", origen_lugar_id: nuevoOrigen }, { onSuccess: () => setNuevoOrigen(null) });
  }

  async function agregarDestino() {
    if (!nuevoDestino) return;
    const km = (await fetchDistanciaSugerida(nuevoDestino))?.km ?? null;
    agregar.mutate(
      { tipo: "entrega", destino_lugar_id: nuevoDestino, distancia_km: km },
      { onSuccess: () => setNuevoDestino(null) },
    );
  }

  function guardarCp(u: Ubicacion, valor: string) {
    const cp = valor.trim();
    if (cp !== "" && !/^\d{5}$/.test(cp)) return; // incompleto: no se guarda
    if (cp === (u.lugar.codigo_postal ?? "")) return;
    editar.mutate({
      id: u.viaje_id,
      payload: u.tipo === "Origen" ? { origen_cp: cp || null } : { destino_cp: cp || null },
    });
  }

  function guardarHora(u: Ubicacion, valor: string) {
    if (valor === (u.hora_programada ?? "").slice(0, 5)) return;
    const hora = valor ? `${valor}:00` : null;
    editar.mutate({
      id: u.viaje_id,
      payload: u.tipo === "Origen" ? { hora_salida_programada: hora } : { hora_llegada_programada: hora },
    });
  }

  function guardarKm(u: Ubicacion, valor: number | null) {
    if (valor === u.distancia_km) return;
    editar.mutate({ id: u.viaje_id, payload: { distancia_km: valor } });
  }

  return (
    <Stack gap="xs">
      <Text size="xs" c="dimmed">
        Cambia el lugar, el CP, la hora programada y los km, o quita un origen o destino; se guarda al salir del campo. Vaciar el CP vuelve al del lugar.
      </Text>
      <Table verticalSpacing={4}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tipo</Table.Th>
            <Table.Th>Lugar</Table.Th>
            <Table.Th>CP</Table.Th>
            <Table.Th>Hora</Table.Th>
            <Table.Th>Km</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {ubicaciones.map((u) => {
            const real = u.fecha_hora_fuente === "real";
            return (
              <Table.Tr key={u.id_ubicacion}>
                <Table.Td>{u.tipo}</Table.Td>
                <Table.Td>
                  {clienteId ? (
                    <LugarSelect
                      clienteId={clienteId}
                      label=""
                      value={u.lugar.id ?? null}
                      onChange={(id) => cambiarLugar(u, id)}
                      nuevoLabel={u.tipo === "Origen" ? "Agregar nuevo origen" : "Agregar nuevo destino"}
                    />
                  ) : (
                    (u.lugar.nombre ?? "—")
                  )}
                </Table.Td>
                <Table.Td>
                  <TextInput
                    key={`cp-${u.id_ubicacion}-${u.lugar.codigo_postal}`}
                    size="xs"
                    w={80}
                    inputMode="numeric"
                    maxLength={5}
                    defaultValue={u.lugar.codigo_postal ?? ""}
                    onBlur={(e) => guardarCp(u, e.currentTarget.value)}
                  />
                </Table.Td>
                <Table.Td>
                  {real ? (
                    <Text size="sm">
                      {u.fecha_hora ? new Date(u.fecha_hora).toLocaleString("es-MX") : "—"}{" "}
                      <Text span size="xs" c="dimmed">
                        (real)
                      </Text>
                    </Text>
                  ) : (
                    <TextInput
                      key={`h-${u.id_ubicacion}-${u.hora_programada}`}
                      size="xs"
                      w={110}
                      type="time"
                      defaultValue={(u.hora_programada ?? "").slice(0, 5)}
                      onBlur={(e) => guardarHora(u, e.currentTarget.value)}
                    />
                  )}
                </Table.Td>
                <Table.Td>
                  {u.tipo === "Destino" ? (
                    <Group gap={6} wrap="nowrap">
                      <NumberInput
                        key={`km-${u.id_ubicacion}-${u.distancia_km}`}
                        size="xs"
                        w={90}
                        decimalScale={2}
                        min={0}
                        defaultValue={u.distancia_km ?? undefined}
                        onBlur={(e) => guardarKm(u, numberInputValue(e.currentTarget.value.replace(/[^\d.]/g, "")))}
                      />
                      {u.km_reportado != null && u.distancia_km != null && u.km_reportado !== u.distancia_km && (
                        <Badge size="xs" variant="light" color="yellow">
                          Operador: {u.km_reportado} km
                        </Badge>
                      )}
                    </Group>
                  ) : (
                    "—"
                  )}
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    aria-label={`Quitar ${u.tipo.toLowerCase()}`}
                    loading={eliminar.isPending}
                    onClick={() => quitar(u)}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>

      {clienteId && (
        <Group align="flex-end" gap="md" wrap="wrap">
          {!hayOrigen && (
            <Group align="flex-end" gap="xs" wrap="nowrap">
              <div style={{ width: 240 }}>
                <LugarSelect
                  clienteId={clienteId}
                  label="Agregar origen"
                  nuevoLabel="Agregar nuevo origen"
                  value={nuevoOrigen}
                  onChange={setNuevoOrigen}
                />
              </div>
              <Button size="xs" color="green" leftSection={<IconPlus size={14} />} disabled={!nuevoOrigen} loading={agregar.isPending} onClick={agregarOrigen}>
                Origen
              </Button>
            </Group>
          )}
          <Group align="flex-end" gap="xs" wrap="nowrap">
            <div style={{ width: 240 }}>
              <LugarSelect
                clienteId={clienteId}
                label="Agregar destino"
                nuevoLabel="Agregar nuevo destino"
                value={nuevoDestino}
                onChange={setNuevoDestino}
              />
            </div>
            <Button size="xs" color="green" leftSection={<IconPlus size={14} />} disabled={!nuevoDestino} loading={agregar.isPending} onClick={agregarDestino}>
              Destino
            </Button>
          </Group>
        </Group>
      )}
    </Stack>
  );
}

// --- Mercancías --------------------------------------------------------------

export function MercanciasEditable({
  servicioId,
  clienteId,
  mercancias,
  ubicaciones,
}: {
  servicioId: string;
  clienteId: string | null | undefined;
  mercancias: MercanciaFacturar[];
  ubicaciones: Ubicacion[];
}) {
  const { data: catalogo } = useMercancias(clienteId ?? null);
  const guardar = useGuardarMercancias(servicioId);
  const [nueva, setNueva] = useState<string | null>(null);
  const [cantNueva, setCantNueva] = useState<number | string>(1);
  const [pesoNuevo, setPesoNuevo] = useState<number | string>(1);

  const opciones = (catalogo ?? []).filter((m) => m.activo).map((m) => ({ value: m.id, label: m.nombre_humano }));
  const viajeNuevo = ubicaciones.find((u) => u.tipo === "Destino")?.viaje_id ?? ubicaciones[0]?.viaje_id;

  function itemsDe(viajeId: string) {
    return mercancias
      .filter((m) => m.viaje_id === viajeId && m.mercancia_frecuente_id)
      .map((m) => ({
        mercancia_frecuente_id: m.mercancia_frecuente_id as string,
        cantidad: Number(m.cantidad),
        peso_kg: m.peso_kg,
      }));
  }

  function cambiar(m: MercanciaFacturar, patch: { mercancia_frecuente_id?: string; cantidad?: number; peso_kg?: number }) {
    const items = mercancias
      .filter((x) => x.viaje_id === m.viaje_id && x.mercancia_frecuente_id)
      .map((x) => {
        const base = {
          mercancia_frecuente_id: x.mercancia_frecuente_id as string,
          cantidad: Number(x.cantidad),
          peso_kg: x.peso_kg,
        };
        return x === m ? { ...base, ...patch } : base;
      });
    guardar.mutate({ viajeId: m.viaje_id, items });
  }

  function quitar(m: MercanciaFacturar) {
    const items = mercancias
      .filter((x) => x.viaje_id === m.viaje_id && x.mercancia_frecuente_id && x !== m)
      .map((x) => ({
        mercancia_frecuente_id: x.mercancia_frecuente_id as string,
        cantidad: Number(x.cantidad),
        peso_kg: x.peso_kg,
      }));
    guardar.mutate({ viajeId: m.viaje_id, items });
  }

  function agregar() {
    const cantidad = numberInputValue(cantNueva);
    const peso = numberInputValue(pesoNuevo);
    if (!nueva || !viajeNuevo || !cantidad || !peso) return;
    guardar.mutate(
      {
        viajeId: viajeNuevo,
        items: [...itemsDe(viajeNuevo), { mercancia_frecuente_id: nueva, cantidad, peso_kg: peso }],
      },
      { onSuccess: () => setNueva(null) },
    );
  }

  return (
    <Stack gap="xs">
      <Table verticalSpacing={4}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Mercancía</Table.Th>
            <Table.Th>Cantidad</Table.Th>
            <Table.Th>Peso (kg)</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {mercancias.map((m, i) => {
            const editable = Boolean(m.mercancia_frecuente_id);
            return (
              <Table.Tr key={m.id ?? i}>
                <Table.Td>
                  {editable ? (
                    <Select
                      size="xs"
                      searchable
                      data={opciones}
                      value={m.mercancia_frecuente_id ?? null}
                      onChange={(v) => v && v !== m.mercancia_frecuente_id && cambiar(m, { mercancia_frecuente_id: v })}
                      allowDeselect={false}
                    />
                  ) : (
                    <Text size="sm">{m.descripcion}</Text>
                  )}
                  <Text size="xs" c="dimmed">
                    {m.bienes_transp} / {m.clave_unidad}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    key={`c-${m.id}-${m.cantidad}`}
                    size="xs"
                    w={80}
                    min={0}
                    decimalScale={2}
                    disabled={!editable}
                    defaultValue={Number(m.cantidad)}
                    onBlur={(e) => {
                      const v = numberInputValue(e.currentTarget.value.replace(/[^\d.]/g, ""));
                      if (v && v !== Number(m.cantidad)) cambiar(m, { cantidad: v });
                    }}
                  />
                </Table.Td>
                <Table.Td>
                  <NumberInput
                    key={`p-${m.id}-${m.peso_kg}`}
                    size="xs"
                    w={90}
                    min={0}
                    decimalScale={2}
                    disabled={!editable}
                    defaultValue={m.peso_kg}
                    onBlur={(e) => {
                      const v = numberInputValue(e.currentTarget.value.replace(/[^\d.]/g, ""));
                      if (v && v !== m.peso_kg) cambiar(m, { peso_kg: v });
                    }}
                  />
                </Table.Td>
                <Table.Td>
                  <ActionIcon variant="subtle" color="red" aria-label="Quitar mercancía" disabled={!editable} onClick={() => quitar(m)}>
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            );
          })}
          {mercancias.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text size="sm" c="dimmed">
                  Sin mercancías: agrega al menos una.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>

      <Group align="flex-end" gap="xs" wrap="wrap">
        <Select
          label="Agregar mercancía"
          placeholder="Elige del catálogo del cliente"
          size="xs"
          searchable
          data={opciones}
          value={nueva}
          onChange={setNueva}
          w={260}
        />
        <NumberInput label="Cantidad" size="xs" w={80} min={0} decimalScale={2} value={cantNueva} onChange={setCantNueva} />
        <NumberInput label="Peso (kg)" size="xs" w={90} min={0} decimalScale={2} value={pesoNuevo} onChange={setPesoNuevo} />
        <Button size="xs" color="green" leftSection={<IconPlus size={14} />} loading={guardar.isPending} disabled={!nueva} onClick={agregar}>
          Agregar
        </Button>
      </Group>
      <Text size="xs" c="dimmed">
        Las mercancías salen del catálogo del cliente (Catálogos → Clientes). Para una nueva, agrégala ahí.
      </Text>
    </Stack>
  );
}

// --- Unidad y operador -------------------------------------------------------

export function UnidadOperadorEditable({ servicioId, detalle }: { servicioId: string; detalle: FacturacionDetalle }) {
  const editar = useEditarServicio(servicioId);
  const { data: unidades } = unidadesApi.useList("true", "");
  const { data: operadores } = operadoresApi.useList("true", "");

  return (
    <Stack gap="sm">
      <Group grow align="flex-start">
        <Select
          label="Unidad"
          searchable
          allowDeselect={false}
          data={(unidades?.items ?? []).map((u) => ({ value: u.id, label: `${u.apodo} · ${u.placa}` }))}
          value={detalle.unidad_id ?? null}
          onChange={(v) => v && v !== detalle.unidad_id && editar.mutate({ unidad_id: v })}
        />
        <Select
          label="Operador"
          searchable
          allowDeselect={false}
          data={(operadores?.items ?? []).map((o) => ({ value: o.id, label: o.nombre }))}
          value={detalle.operador_id ?? null}
          onChange={(v) => v && v !== detalle.operador_id && editar.mutate({ operador_id: v })}
        />
      </Group>
      <Group gap="xs">
        <Badge variant="light">Placa {detalle.autotransporte.placa}</Badge>
        <Badge variant="light">{detalle.autotransporte.config_vehicular}</Badge>
        <Badge variant="light">{detalle.autotransporte.perm_sct}</Badge>
        <Badge variant="light" color={detalle.autotransporte.poliza ? "gray" : "red"}>
          {detalle.autotransporte.poliza ? `Póliza ${detalle.autotransporte.poliza}` : "Sin póliza"}
        </Badge>
      </Group>
      <Text size="sm">
        {detalle.figura.nombre} · RFC {detalle.figura.rfc} · Lic. {detalle.figura.num_licencia}
      </Text>
    </Stack>
  );
}
