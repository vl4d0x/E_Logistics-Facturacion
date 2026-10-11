// `fase-1-catalogos.md` H1.5 — lista + CRUD de lugares. Reutilizado en la vista global
// (`/admin/catalogos/lugares`) y en la tab "Lugares" de la ficha del cliente.
import { Alert, Badge, Drawer, Select, Table, Text } from "@mantine/core";
import { IconAlertTriangle, IconStar } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { type ActivoFiltro, clientesApi, useDeleteLugar, useLugarUso, useLugares, useRestoreLugar } from "../api";
import type { Cliente, Lugar } from "../types";
import { CatalogToolbar } from "./CatalogToolbar";
import { LugarForm } from "./LugarForm";
import { RowActionsMenu } from "./RowActionsMenu";
import { SmartDeleteDialog } from "./SmartDeleteDialog";

export function LugaresManager({ clienteIdFijo }: { clienteIdFijo?: string }) {
  const esGlobal = clienteIdFijo === undefined;
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [q, setQ] = useState("");
  const [filtroCliente, setFiltroCliente] = useState<string | null>(null);
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [editando, setEditando] = useState<Lugar | null>(null);
  const [eliminando, setEliminando] = useState<Lugar | null>(null);

  const clienteIdConsulta = clienteIdFijo ?? filtroCliente;
  const { data: lugares, isLoading, isError } = useLugares(clienteIdConsulta, q, esGlobal);
  const { data: clientesPage } = clientesApi.useList("true", "");
  const uso = useLugarUso(eliminando?.id ?? null);
  const eliminar = useDeleteLugar();
  const restaurar = useRestoreLugar();

  const clientesPorId = useMemo(() => {
    const map = new Map<string, Cliente>();
    for (const c of clientesPage?.items ?? []) map.set(c.id, c);
    return map;
  }, [clientesPage]);

  const visibles = (lugares ?? []).filter((l) => {
    if (!esGlobal && l.cliente_id !== clienteIdFijo) return false; // tab de cliente: solo lo suyo
    if (activo === "true") return l.activo;
    if (activo === "false") return !l.activo;
    return true;
  });

  return (
    <div>
      <CatalogToolbar
        q={q}
        onQChange={setQ}
        activo={activo}
        onActivoChange={setActivo}
        onNuevo={() => {
          setEditando(null);
          setDrawerAbierto(true);
        }}
        nuevoLabel="Nuevo lugar"
        placeholder="Buscar por nombre…"
      />

      {esGlobal && (
        <Select
          label="Filtrar por cliente"
          placeholder="Todos"
          clearable
          data={(clientesPage?.items ?? []).map((c) => ({ value: c.id, label: c.nombre_comercial }))}
          value={filtroCliente}
          onChange={setFiltroCliente}
          w={260}
          mb="md"
        />
      )}

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar los lugares.
        </Alert>
      )}

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            {esGlobal && <Table.Th>Cliente</Table.Th>}
            <Table.Th>CP</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th>Km</Table.Th>
            <Table.Th>Estatus</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {visibles.map((lugar) => (
            <Table.Tr key={lugar.id}>
              <Table.Td>
                <Text span>{lugar.nombre}</Text>
                {lugar.es_origen_predeterminado && (
                  <IconStar size={14} style={{ marginLeft: 6, verticalAlign: "middle" }} />
                )}
              </Table.Td>
              {esGlobal && (
                <Table.Td>
                  {lugar.cliente_id ? clientesPorId.get(lugar.cliente_id)?.nombre_comercial ?? "—" : (
                    <Text size="xs" c="dimmed">
                      Global
                    </Text>
                  )}
                </Table.Td>
              )}
              <Table.Td>{lugar.codigo_postal}</Table.Td>
              <Table.Td>{lugar.estado}</Table.Td>
              <Table.Td>{lugar.distancia_km != null ? `${lugar.distancia_km} km` : "—"}</Table.Td>
              <Table.Td>
                <Badge color={lugar.activo ? "green" : "gray"} variant="light">
                  {lugar.activo ? "Activo" : "Archivado"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <RowActionsMenu
                  activo={lugar.activo}
                  onEditar={() => {
                    setEditando(lugar);
                    setDrawerAbierto(true);
                  }}
                  onEliminar={() => setEliminando(lugar)}
                  onRestaurar={() => restaurar.mutate(lugar.id)}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {!isLoading && visibles.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin lugares {activo === "false" ? "archivados" : "registrados"}.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title={editando ? editando.nombre : "Nuevo lugar"}
        position="right"
        size="lg"
      >
        <LugarForm
          lugar={editando}
          clienteIdFijo={clienteIdFijo}
          clientes={esGlobal ? clientesPage?.items : undefined}
          onCancel={() => setDrawerAbierto(false)}
          onSaved={() => setDrawerAbierto(false)}
        />
      </Drawer>

      <SmartDeleteDialog
        opened={eliminando !== null}
        onClose={() => setEliminando(null)}
        uso={uso.data}
        isLoadingUso={uso.isLoading}
        isDeleting={eliminar.isPending}
        onConfirm={() =>
          eliminando && eliminar.mutate(eliminando.id, { onSuccess: () => setEliminando(null) })
        }
      />
    </div>
  );
}
