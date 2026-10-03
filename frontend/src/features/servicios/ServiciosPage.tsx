// `fase-2-servicios.md` H2.2 — lista de servicios por estado y fecha.
import { Alert, Badge, Button, Group, Select, Table, Tabs, Text, TextInput } from "@mantine/core";
import { IconAlertTriangle, IconPlus, IconSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/Card";
import { clientesApi, operadoresApi, unidadesApi } from "../catalogos/api";
import { useConteosServicios, useServicios, type FiltrosServicios } from "./api";
import type { ServicioListItem, Vista } from "./types";

const TABS: { value: Vista | "todos"; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "programados", label: "Programados" },
  { value: "en_curso", label: "En curso" },
  { value: "por_facturar", label: "Por facturar" },
  { value: "facturados", label: "Facturados" },
  { value: "cancelados", label: "Cancelados" },
];

const ESTADO_LABEL: Record<string, string> = {
  programado: "Programado",
  en_curso: "En curso",
  terminado: "Terminado",
  cancelado: "Cancelado",
};

function agruparPorFecha(items: ServicioListItem[]): [string, ServicioListItem[]][] {
  const grupos = new Map<string, ServicioListItem[]>();
  for (const item of items) {
    const lista = grupos.get(item.fecha) ?? [];
    lista.push(item);
    grupos.set(item.fecha, lista);
  }
  return [...grupos.entries()];
}

export function ServiciosPage() {
  const navigate = useNavigate();
  const [vista, setVista] = useState<Vista | "todos">("todos");
  const [q, setQ] = useState("");
  const [clienteId, setClienteId] = useState<string | null>(null);
  const [operadorId, setOperadorId] = useState<string | null>(null);
  const [unidadId, setUnidadId] = useState<string | null>(null);

  const filtros: FiltrosServicios = useMemo(
    () => ({
      vista: vista === "todos" ? undefined : vista,
      cliente_id: clienteId,
      operador_id: operadorId,
      unidad_id: unidadId,
      q,
    }),
    [vista, clienteId, operadorId, unidadId, q],
  );

  const { data, isLoading, isError } = useServicios(filtros);
  const { data: conteos } = useConteosServicios(filtros);
  const { data: clientesPage } = clientesApi.useList("true", "");
  const { data: operadoresPage } = operadoresApi.useList("true", "");
  const { data: unidadesPage } = unidadesApi.useList("true", "");

  const grupos = agruparPorFecha(data?.items ?? []);

  return (
    <Card>
      <Group justify="space-between" mb="md">
        <Tabs value={vista} onChange={(v) => v && setVista(v as Vista | "todos")}>
          <Tabs.List>
            {TABS.map((t) => (
              <Tabs.Tab key={t.value} value={t.value}>
                {t.label}
                {conteos && t.value !== "todos" && (
                  <Text span size="xs" c="dimmed" ml={6}>
                    ({conteos[t.value as Vista]})
                  </Text>
                )}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
        <Button leftSection={<IconPlus size={16} />} onClick={() => navigate("/admin/servicios/nuevo")}>
          Nuevo servicio
        </Button>
      </Group>

      <Group mb="md" wrap="wrap">
        <TextInput
          placeholder="Buscar por número, cliente o lugar…"
          leftSection={<IconSearch size={16} />}
          value={q}
          onChange={(e) => setQ(e.currentTarget.value)}
          w={260}
        />
        <Select
          placeholder="Cliente"
          clearable
          searchable
          data={(clientesPage?.items ?? []).map((c) => ({ value: c.id, label: c.nombre_comercial }))}
          value={clienteId}
          onChange={setClienteId}
          w={180}
        />
        <Select
          placeholder="Operador"
          clearable
          searchable
          data={(operadoresPage?.items ?? []).map((o) => ({ value: o.id, label: o.nombre }))}
          value={operadorId}
          onChange={setOperadorId}
          w={180}
        />
        <Select
          placeholder="Unidad"
          clearable
          searchable
          data={(unidadesPage?.items ?? []).map((u) => ({ value: u.id, label: u.apodo }))}
          value={unidadId}
          onChange={setUnidadId}
          w={180}
        />
      </Group>

      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} mb="md">
          No se pudieron cargar los servicios.
        </Alert>
      )}

      {grupos.map(([fecha, items]) => (
        <div key={fecha}>
          <Text size="xs" tt="uppercase" c="dimmed" fw={700} mt="md" mb={4}>
            {new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </Text>
          <Table verticalSpacing="sm">
            <Table.Tbody>
              {items.map((s) => (
                <Table.Tr
                  key={s.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/admin/servicios/${s.id}`)}
                >
                  <Table.Td w={60}>#{s.numero}</Table.Td>
                  <Table.Td>{s.cliente}</Table.Td>
                  <Table.Td>{s.ruta_resumen}</Table.Td>
                  <Table.Td>
                    {s.unidad_apodo} · {s.operador_nombre}
                  </Table.Td>
                  <Table.Td>
                    {s.viajes_terminados}/{s.viajes_total} viajes
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      variant="light"
                      color={s.acuses_completos === s.acuses_requeridos ? "gray" : "yellow"}
                    >
                      {s.acuses_completos}/{s.acuses_requeridos} acuses
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">{s.subtotal ? `$${s.subtotal}` : "—"}</Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      <Badge variant="light">{ESTADO_LABEL[s.estado]}</Badge>
                      {s.estado_facturacion === "facturado" ? (
                        <Badge color="green" variant="light">
                          Facturado
                        </Badge>
                      ) : (
                        (s.estado === "terminado" || s.timbrado_anticipado) && (
                          <Badge color="yellow" variant="light">
                            Por facturar
                          </Badge>
                        )
                      )}
                      {s.timbrado_anticipado && (
                        <Badge color="blue" variant="light">
                          Anticipada
                        </Badge>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      ))}

      {!isLoading && grupos.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Sin servicios {vista === "todos" ? "registrados" : "en esta vista"}.
        </Text>
      )}
    </Card>
  );
}
