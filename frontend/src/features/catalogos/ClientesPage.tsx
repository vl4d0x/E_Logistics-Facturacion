// `fase-1-catalogos.md` H1.3 — lista de clientes; la ficha con tabs vive en ClienteDetailPage.
import { Alert, Badge, Drawer, Table, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/Card";
import { type ActivoFiltro, clientesApi } from "./api";
import { CatalogToolbar } from "./components/CatalogToolbar";
import { ClienteFiscalForm } from "./components/ClienteFiscalForm";
import { RowActionsMenu } from "./components/RowActionsMenu";
import { SmartDeleteDialog } from "./components/SmartDeleteDialog";
import type { Cliente } from "./types";

export function ClientesPage() {
  const navigate = useNavigate();
  const [activo, setActivo] = useState<ActivoFiltro>("true");
  const [q, setQ] = useState("");
  const [drawerAbierto, setDrawerAbierto] = useState(false);
  const [eliminando, setEliminando] = useState<Cliente | null>(null);

  const { data, isLoading, isError } = clientesApi.useList(activo, q);
  const uso = clientesApi.useUso(eliminando?.id ?? null);
  const eliminar = clientesApi.useDelete();
  const restaurar = clientesApi.useRestore();

  return (
    <Card>
      <CatalogToolbar
        q={q}
        onQChange={setQ}
        activo={activo}
        onActivoChange={setActivo}
        onNuevo={() => setDrawerAbierto(true)}
        nuevoLabel="Nuevo cliente"
        placeholder="Buscar por nombre o RFC…"
      />

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar los clientes.
        </Alert>
      )}

      <Table verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Cliente</Table.Th>
            <Table.Th>RFC</Table.Th>
            <Table.Th>Régimen</Table.Th>
            <Table.Th>Modo de acuse</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data?.items.map((cliente) => (
            <Table.Tr
              key={cliente.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/admin/catalogos/clientes/${cliente.id}`)}
            >
              <Table.Td>
                <Text fw={600}>{cliente.nombre_comercial}</Text>
                <Text size="xs" c="dimmed">
                  {cliente.razon_social}
                </Text>
              </Table.Td>
              <Table.Td>{cliente.rfc}</Table.Td>
              <Table.Td style={{ textTransform: "capitalize" }}>{cliente.regimen_receptor}</Table.Td>
              <Table.Td style={{ textTransform: "capitalize" }}>{cliente.modo_acuse}</Table.Td>
              <Table.Td>
                <Badge color={cliente.activo ? "green" : "gray"} variant="light">
                  {cliente.activo ? "Activo" : "Archivado"}
                </Badge>
              </Table.Td>
              <Table.Td onClick={(e) => e.stopPropagation()}>
                <RowActionsMenu
                  activo={cliente.activo}
                  onEditar={() => navigate(`/admin/catalogos/clientes/${cliente.id}`)}
                  onEliminar={() => setEliminando(cliente)}
                  onRestaurar={() => restaurar.mutate(cliente.id)}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {!isLoading && data?.items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin clientes {activo === "false" ? "archivados" : "registrados"}.
        </Text>
      )}

      <Drawer
        opened={drawerAbierto}
        onClose={() => setDrawerAbierto(false)}
        title="Nuevo cliente"
        position="right"
        size="lg"
      >
        <ClienteFiscalForm
          cliente={null}
          onCancel={() => setDrawerAbierto(false)}
          onSaved={(creado) => {
            setDrawerAbierto(false);
            navigate(`/admin/catalogos/clientes/${creado.id}`);
          }}
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
    </Card>
  );
}
