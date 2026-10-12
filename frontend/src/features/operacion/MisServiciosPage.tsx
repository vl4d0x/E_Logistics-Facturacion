// `05-ui-spec §8 Mis servicios` — secciones Hoy / Próximos / Terminados (7 días).
import { hoyMexico } from "../../lib/fecha";
import { Badge, Group, Skeleton, Stack, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/Card";
import { useMisServicios } from "./api";
import type { ServicioDetalle } from "../servicios/types";

function estadoTexto(servicio: ServicioDetalle): string {
  if (servicio.estado === "terminado") return "Terminado";
  if (servicio.estado === "en_curso") {
    const total = servicio.viajes.length;
    const hechos = servicio.viajes.filter((v) => v.estado === "terminado").length;
    return `En curso · viaje ${Math.min(hechos + 1, total)} de ${total}`;
  }
  return "Por iniciar";
}

function rutaCorta(servicio: ServicioDetalle): string {
  const primero = servicio.viajes[0];
  const ultimo = servicio.viajes[servicio.viajes.length - 1];
  const origen = primero?.origen?.nombre ?? servicio.unidad.apodo;
  const destino = ultimo?.destino?.nombre ?? primero?.destino?.nombre;
  return destino ? `${origen} → ${destino}` : origen;
}

function ServicioCard({ servicio }: { servicio: ServicioDetalle }) {
  const navigate = useNavigate();
  return (
    <Card style={{ cursor: "pointer" }}>
      <div onClick={() => navigate(`/operador/servicios/${servicio.id}`)}>
        <Group justify="space-between">
          <Text fw={600}>#{servicio.numero} · {servicio.cliente.nombre_comercial}</Text>
          <Badge variant="light" color={servicio.estado === "terminado" ? "green" : "blue"}>
            {estadoTexto(servicio)}
          </Badge>
        </Group>
        <Text size="sm" c="dimmed" mt={4}>
          {servicio.unidad.apodo} · {rutaCorta(servicio)}
        </Text>
      </div>
    </Card>
  );
}

function Seccion({ titulo, servicios }: { titulo: string; servicios: ServicioDetalle[] }) {
  if (servicios.length === 0) return null;
  return (
    <Stack gap="sm">
      <Text fw={700} size="sm" c="dimmed" tt="uppercase">
        {titulo}
      </Text>
      {servicios.map((s) => (
        <ServicioCard key={s.id} servicio={s} />
      ))}
    </Stack>
  );
}

export function MisServiciosPage() {
  const { data: servicios, isLoading } = useMisServicios();

  if (isLoading) return <Skeleton height={200} />;

  const hoyStr = hoyMexico();
  const todos = servicios ?? [];
  const terminados = todos.filter((s) => s.estado === "terminado");
  const hoy = todos.filter((s) => s.estado !== "terminado" && s.fecha <= hoyStr);
  const proximos = todos.filter((s) => s.estado !== "terminado" && s.fecha > hoyStr);

  if (todos.length === 0) {
    return (
      <Card>
        <Text c="dimmed">No tienes servicios asignados por el momento.</Text>
      </Card>
    );
  }

  return (
    <Stack gap="xl">
      <Seccion titulo="Hoy" servicios={hoy} />
      <Seccion titulo="Próximos" servicios={proximos} />
      <Seccion titulo="Terminados (7 días)" servicios={terminados} />
    </Stack>
  );
}
