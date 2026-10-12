// `05-ui-spec §8 Servicio` — stepper 1 Inspección → 2 Viajes → 3 Cierre.
import { Alert, Button, Group, NumberInput, Skeleton, Stack, Stepper, Text, Textarea } from "@mantine/core";
import { IconArrowLeft, IconCheck } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { numberInputValue } from "../../lib/numberInput";
import { useCerrarServicio, useIniciarServicio, useServicioOperador } from "./api";
import { ChecklistToggle } from "./components/ChecklistToggle";
import { FuelGauge } from "./components/FuelGauge";
import { FuelLoadForm } from "./components/FuelLoadForm";
import { OperatorReportCard } from "./components/OperatorReportCard";
import { ETIQUETAS_CHECKLIST, type CargaDraft, type Checklist, type LecturaMedidor, nuevaCargaDraft } from "./types";

type LecturaParcial = { tipo: "aguja"; octavos: number } | { tipo: "barras"; barras: number; total: number };

function PasoInspeccion({
  servicioId,
  tipoMedidor,
  numBarras,
}: {
  servicioId: string;
  tipoMedidor: "aguja" | "barras";
  numBarras: number | null;
}) {
  const [checklist, setChecklist] = useState<Record<keyof Checklist, boolean | null>>({
    unidad_limpia: null,
    fumigacion_vigente: null,
    botiquin: null,
    casco_chaleco: null,
    aceite_ok: null,
    anticongelante_ok: null,
    neumaticos_ok: null,
    extintor_ok: null,
  });
  const [lectura, setLectura] = useState<LecturaParcial>({ tipo: tipoMedidor, octavos: 0 } as LecturaParcial);
  const [odometro, setOdometro] = useState<number | null>(null);
  const [observaciones, setObservaciones] = useState("");
  const iniciar = useIniciarServicio(servicioId);

  const hayFallas = Object.values(checklist).some((v) => v === false);
  const completo = Object.values(checklist).every((v) => v !== null);

  function enviar() {
    iniciar.mutate({
      client_action_id: crypto.randomUUID(),
      realizada_at: new Date().toISOString(),
      checklist: checklist as Checklist,
      observaciones: observaciones || null,
      lectura_medidor: lectura as LecturaMedidor,
      odometro_km: odometro,
    });
  }

  return (
    <Stack gap="md">
      <Text fw={600}>Inspección de salida</Text>
      <Stack gap={2}>
        {(Object.keys(ETIQUETAS_CHECKLIST) as (keyof Checklist)[]).map((key) => (
          <ChecklistToggle
            key={key}
            label={ETIQUETAS_CHECKLIST[key]}
            value={checklist[key]}
            onChange={(value) => setChecklist((prev) => ({ ...prev, [key]: value }))}
          />
        ))}
      </Stack>
      <div>
        <Text size="sm" fw={600} mb={4}>
          Gasolina al salir
        </Text>
        <FuelGauge
          tipoMedidor={tipoMedidor}
          numBarras={numBarras}
          lectura={lectura}
          onChange={(v) => setLectura(v as LecturaParcial)}
        />
      </div>
      <NumberInput
        label="Odómetro (opcional)"
        suffix=" km"
        value={odometro ?? undefined}
        onChange={(v) => setOdometro(numberInputValue(v))}
      />
      <Textarea
        label="Observaciones (opcional)"
        placeholder={hayFallas ? "Describe lo que encontraste" : undefined}
        value={observaciones}
        onChange={(e) => setObservaciones(e.currentTarget.value)}
      />
      <Button size="lg" fullWidth disabled={!completo} loading={iniciar.isPending} onClick={enviar}>
        Iniciar servicio
      </Button>
    </Stack>
  );
}

function PasoViajes({ servicio }: { servicio: NonNullable<ReturnType<typeof useServicioOperador>["data"]> }) {
  const navigate = useNavigate();
  const siguienteId = servicio.viajes.find((v) => v.estado === "pendiente")?.id;

  return (
    <Stack gap="sm">
      <Text fw={600}>Viajes</Text>
      {servicio.viajes.map((v) => {
        const esSiguiente = v.id === siguienteId;
        const lugar = v.tipo === "recoleccion" ? v.origen : v.destino;
        return (
          <Card
            key={v.id}
            style={{
              border: esSiguiente ? "2px solid var(--el-ink)" : undefined,
              opacity: v.estado === "terminado" ? 0.6 : 1,
            }}
          >
            <Group justify="space-between">
              <Text fw={600}>
                Viaje {v.orden} · {v.tipo === "recoleccion" ? "Recolección" : v.tipo === "entrega" ? "Entrega" : "Recolección y entrega"}
              </Text>
              {v.estado === "terminado" && <IconCheck size={18} color="var(--el-success-text)" />}
            </Group>
            {lugar && (
              <Text size="sm" c="dimmed" mt={4}>
                {lugar.nombre}
                {lugar.calle ? ` · ${lugar.calle} ${lugar.num_exterior ?? ""}` : ""}
                {/* La referencia del lugar a veces trae correos del cliente: al operador no se le muestran. */}
                {lugar.referencia && !lugar.referencia.includes("@") ? ` · ${lugar.referencia}` : ""}
              </Text>
            )}
            {v.notas_admin && (
              <Text size="sm" mt={4}>
                Nota: {v.notas_admin}
              </Text>
            )}
            {v.estado === "pendiente" && (
              <Button
                mt="sm"
                disabled={!esSiguiente}
                onClick={() => navigate(`/operador/viajes/${v.id}/terminar`)}
              >
                Terminar viaje
              </Button>
            )}
          </Card>
        );
      })}
    </Stack>
  );
}

function PasoCierre({ servicio }: { servicio: NonNullable<ReturnType<typeof useServicioOperador>["data"]> }) {
  const [kms, setKms] = useState<Record<string, number | null>>(
    Object.fromEntries(servicio.viajes.map((v) => [v.id, v.distancia_km ?? null])),
  );
  const [lectura, setLectura] = useState<LecturaParcial>(
    { tipo: servicio.unidad.tipo_medidor, octavos: 0 } as LecturaParcial,
  );
  const [odometro, setOdometro] = useState<number | null>(null);
  const [cargoCombustible, setCargoCombustible] = useState<boolean | null>(null);
  const [cargas, setCargas] = useState<CargaDraft[]>([nuevaCargaDraft()]);
  const [observaciones, setObservaciones] = useState("");
  const cerrar = useCerrarServicio(servicio.id);

  const totalKm = Object.values(kms).reduce((acc: number, v) => acc + (v ?? 0), 0);
  const odometroInicio = servicio.inspeccion?.odometro_km ?? null;
  const completo = Object.values(kms).every((v) => v !== null) && cargoCombustible !== null;

  function enviar() {
    cerrar.mutate({
      client_action_id: crypto.randomUUID(),
      cerrado_at: new Date().toISOString(),
      km_por_viaje: Object.entries(kms).map(([viaje_id, km]) => ({ viaje_id, km: km ?? 0 })),
      lectura_medidor: lectura as LecturaMedidor,
      odometro_km: odometro,
      observaciones: observaciones || null,
      cargo_combustible: cargoCombustible ?? false,
      cargas:
        cargoCombustible && cargas.some((c) => c.litros && c.precioLitro && c.importe)
          ? cargas
              .filter((c) => c.litros && c.precioLitro && c.importe)
              .map((c) => ({
                id: c.id,
                litros: c.litros!,
                precio_litro: c.precioLitro!,
                importe: c.importe!,
                cargada_at: new Date().toISOString(),
              }))
          : [],
    });
  }

  return (
    <Stack gap="md">
      <Text fw={600}>Cierre del servicio</Text>
      <Stack gap={4}>
        {servicio.viajes.map((v) => (
          <Group key={v.id} justify="space-between">
            <Text size="sm">
              Viaje {v.orden} · {v.tipo === "recoleccion" ? "Recolección" : v.tipo === "entrega" ? "Entrega" : "Recolección y entrega"}
              {" · "}
              {(v.tipo === "recoleccion" ? v.origen : v.destino)?.nombre}
            </Text>
            <NumberInput
              w={110}
              suffix=" km"
              aria-label={`Km reportados del viaje ${v.orden}`}
              value={kms[v.id] ?? undefined}
              onChange={(val) => setKms((prev) => ({ ...prev, [v.id]: numberInputValue(val) }))}
            />
          </Group>
        ))}
        <Group justify="flex-end">
          <Text size="sm" fw={700}>
            Total: {totalKm} km
          </Text>
        </Group>
      </Stack>
      <NumberInput
        label="Odómetro al llegar (opcional)"
        suffix=" km"
        value={odometro ?? undefined}
        onChange={(v) => setOdometro(numberInputValue(v))}
        description={
          odometro != null && odometroInicio != null
            ? `Recorrido según odómetro: ${odometro - odometroInicio} km`
            : undefined
        }
      />
      <div>
        <Text size="sm" fw={600} mb={4}>
          Gasolina al llegar
        </Text>
        <FuelGauge
          tipoMedidor={servicio.unidad.tipo_medidor as "aguja" | "barras"}
          numBarras={servicio.unidad.num_barras}
          lectura={lectura}
          onChange={(v) => setLectura(v as LecturaParcial)}
        />
      </div>
      <ChecklistToggle
        label="¿Cargaste gasolina en este servicio?"
        value={cargoCombustible}
        onChange={setCargoCombustible}
      />
      {cargoCombustible && <FuelLoadForm cargas={cargas} onChange={setCargas} />}
      <Textarea
        label="Observaciones (opcional)"
        value={observaciones}
        onChange={(e) => setObservaciones(e.currentTarget.value)}
      />
      <Button size="lg" fullWidth disabled={!completo} loading={cerrar.isPending} onClick={enviar}>
        Terminar servicio
      </Button>
    </Stack>
  );
}

export function ServicioOperadorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: servicio } = useServicioOperador(id ?? null);

  if (!servicio) return <Skeleton height={300} />;

  const todosTerminados = servicio.viajes.every((v) => v.estado === "terminado");
  const paso = !servicio.inspeccion ? 0 : !todosTerminados ? 1 : servicio.cierre ? 3 : 2;

  return (
    <Stack gap="lg">
      <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate("/operador")} px={0}>
        Mis servicios
      </Button>

      <Card>
        <Text size="lg" fw={700}>
          Servicio #{servicio.numero} · {servicio.cliente.nombre_comercial}
        </Text>
        <Text size="sm" c="dimmed">
          {servicio.unidad.apodo} · {new Date(`${servicio.fecha}T00:00:00`).toLocaleDateString("es-MX")}
        </Text>
      </Card>

      <Stepper active={paso} allowNextStepsSelect={false}>
        <Stepper.Step label="Inspección" />
        <Stepper.Step label="Viajes" />
        <Stepper.Step label="Cierre" />
      </Stepper>

      {paso === 0 && (
        <PasoInspeccion
          servicioId={servicio.id}
          tipoMedidor={servicio.unidad.tipo_medidor as "aguja" | "barras"}
          numBarras={servicio.unidad.num_barras}
        />
      )}
      {paso === 1 && <PasoViajes servicio={servicio} />}
      {paso === 2 && <PasoCierre servicio={servicio} />}
      {paso === 3 && (
        <>
          <Alert color="green" icon={<IconCheck size={16} />}>
            Servicio terminado.
          </Alert>
          <OperatorReportCard servicio={servicio} />
        </>
      )}
    </Stack>
  );
}
