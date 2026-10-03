// `fase-1-catalogos.md` H1.3 — ficha del cliente con tabs (Tarifas llega en Fase 4).
import { Alert, Button, Skeleton, Tabs } from "@mantine/core";
import { IconAlertTriangle, IconArrowLeft } from "@tabler/icons-react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { clientesApi } from "./api";
import { ClienteFiscalForm } from "./components/ClienteFiscalForm";
import { LugaresManager } from "./components/LugaresManager";
import { MercanciasManager } from "./components/MercanciasManager";

export function ClienteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: cliente, isLoading, isError } = clientesApi.useGet(id ?? null);

  return (
    <Card>
      <Button
        variant="subtle"
        leftSection={<IconArrowLeft size={16} />}
        onClick={() => navigate("/admin/catalogos/clientes")}
        mb="md"
        px={0}
      >
        Clientes
      </Button>

      {isLoading && <Skeleton height={300} />}
      {isError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />}>
          No se pudo cargar el cliente.
        </Alert>
      )}

      {cliente && (
        <Tabs defaultValue="fiscales">
          <Tabs.List>
            <Tabs.Tab value="fiscales">Datos fiscales</Tabs.Tab>
            <Tabs.Tab value="mercancias">Mercancías</Tabs.Tab>
            <Tabs.Tab value="lugares">Lugares</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="fiscales" pt="lg">
            <ClienteFiscalForm
              cliente={cliente}
              onCancel={() => navigate("/admin/catalogos/clientes")}
              onSaved={() => {}}
            />
          </Tabs.Panel>

          <Tabs.Panel value="mercancias" pt="lg">
            <MercanciasManager clienteId={cliente.id} />
          </Tabs.Panel>

          <Tabs.Panel value="lugares" pt="lg">
            <LugaresManager clienteIdFijo={cliente.id} />
          </Tabs.Panel>
        </Tabs>
      )}
    </Card>
  );
}
