// Facturar con el Excel de registros: se sube el Excel una vez, se escribe el número de fila
// y la app arma el servicio con lo que encuentra en los catálogos. Solo se captura, por
// destino, el folio (o el escaneo), los kg y la mercancía.
import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Checkbox,
  FileButton,
  FileInput,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Skeleton,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconDownload,
  IconFileSpreadsheet,
  IconPlus,
  IconSearch,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../components/Card";
import { EnviarTodasButton } from "../facturas/components/EnviarTodasButton";
import { TotalConIva } from "../../components/TotalConIva";
import { api, ApiError } from "../../lib/api";
import { pesos } from "../../lib/money";
import { numberInputValue } from "../../lib/numberInput";
import { clientesApi, operadoresApi, unidadesApi, useMercancias } from "../catalogos/api";
import { LugarSelect } from "../servicios/components/LugarSelect";
import {
  descargarRegistro,
  fechaDMY,
  normalizarRef,
  useCrearDesdeFila,
  useRefsRepetidas,
  useServiciosCercanos,
  useFilasRecientes,
  usePropuesta,
  useRegistro,
  useSubirRegistro,
  type CrearDesdeFilaIn,
  type DatosFila,
  type FilaResumen,
  type Propuesta,
  type PropuestaLugar,
  type ServicioCercano,
  type ServicioConRef,
} from "./api";

const CP_GENERICO = "50000";

function fechaCorta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

function limpiarNombre(texto: string): string {
  return texto.replace(/\([^)]*\)?/g, " ").replace(/\s+/g, " ").trim().toUpperCase();
}

function nuevoKey(): string {
  return Math.random().toString(36).slice(2);
}

// --- Archivo ---------------------------------------------------------------------------

function ArchivoCard() {
  const { data: registro, isLoading } = useRegistro();
  const subir = useSubirRegistro();
  const [descargando, setDescargando] = useState(false);

  async function descargar() {
    setDescargando(true);
    try {
      const escritas = await descargarRegistro();
      if (escritas !== null) {
        notifications.show({
          color: "green",
          message: escritas
            ? `Se escribió el número de factura en ${escritas} fila${escritas === 1 ? "" : "s"}`
            : "No había facturas nuevas que escribir; se descargó el Excel tal cual",
        });
      }
    } finally {
      setDescargando(false);
    }
  }

  if (isLoading) return <Skeleton height={90} />;

  const boton = (texto: string) => (
    <FileButton
      accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      onChange={(f) => f && subir.mutate(f)}
    >
      {(props) => (
        <Button {...props} variant={registro ? "default" : "filled"} leftSection={<IconUpload size={16} />} loading={subir.isPending}>
          {texto}
        </Button>
      )}
    </FileButton>
  );

  return (
    <Card>
      <Group justify="space-between" align="flex-start" gap="sm">
        <Group gap="sm" wrap="nowrap" align="flex-start" style={{ minWidth: 0 }}>
          <IconFileSpreadsheet size={28} color="var(--el-success-text)" style={{ flexShrink: 0 }} />
          {registro ? (
            <div style={{ minWidth: 0 }}>
              <Text fw={600} truncate>
                {registro.nombre_archivo}
              </Text>
              <Text size="xs" c="dimmed">
                Hoja {registro.hoja} · {registro.total_filas.toLocaleString("es-MX")} filas (hasta la {registro.ultima_fila}) ·
                subido el {new Date(registro.subido_at).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })}
              </Text>
            </div>
          ) : (
            <div>
              <Text fw={600}>Sube tu Excel de registros</Text>
              <Text size="xs" c="dimmed">
                Se guarda hasta que subas uno nuevo. Se lee la hoja con FECHA, CLIENTE, OPERADOR, UNIDAD, ORIGEN, DESTINO,
                SUBTOTAL y FACTURA.
              </Text>
            </div>
          )}
        </Group>
        <Group gap="xs">
          {registro && (
            <Tooltip label="Copia de tu Excel con el número de factura escrito en la columna FACTURA de las filas que facturaste aquí">
              <Button variant="light" leftSection={<IconDownload size={16} />} onClick={descargar} loading={descargando}>
                Descargar con facturas
              </Button>
            </Tooltip>
          )}
          {boton(registro ? "Subir uno nuevo" : "Subir Excel")}
          <EnviarTodasButton />
        </Group>
      </Group>
    </Card>
  );
}

// --- Elegir fila -------------------------------------------------------------------------

function EstadoFila({ fila }: { fila: FilaResumen }) {
  if (fila.servicio?.factura_folio) return <Badge color="green" variant="light">Factura {fila.servicio.factura_folio}</Badge>;
  if (fila.datos.factura != null) return <Badge color="gray" variant="light">Factura {String(fila.datos.factura)}</Badge>;
  if (fila.servicio) return <Badge color="blue" variant="light">Servicio #{fila.servicio.numero}</Badge>;
  return <Badge color="yellow" variant="light">Sin factura</Badge>;
}

function ElegirFila({ fila, onElegir }: { fila: number | null; onElegir: (n: number) => void }) {
  const [valor, setValor] = useState<number | null>(fila);
  const [soloPendientes, setSoloPendientes] = useState(true);
  const { data: filas, isLoading } = useFilasRecientes(true, soloPendientes);

  return (
    <Card>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (valor) onElegir(valor);
        }}
      >
        <Group align="flex-end" gap="sm">
          <NumberInput
            label="Número de fila del Excel"
            placeholder="Ej. 5527"
            min={2}
            allowDecimal={false}
            allowNegative={false}
            value={valor ?? ""}
            onChange={(v) => setValor(numberInputValue(v))}
            w={200}
            autoFocus
          />
          <Button type="submit" leftSection={<IconSearch size={16} />} disabled={!valor}>
            Cargar fila
          </Button>
        </Group>
      </form>

      <Group justify="space-between" mt="lg" mb="xs">
        <Text size="sm" fw={600}>
          Filas recientes
        </Text>
        <Switch size="xs" label="Solo sin factura" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.currentTarget.checked)} />
      </Group>
      {isLoading ? (
        <Skeleton height={120} />
      ) : (
        <Table verticalSpacing={6} highlightOnHover className="el-cardtable">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Fila</Table.Th>
              <Table.Th>Fecha</Table.Th>
              <Table.Th>Cliente</Table.Th>
              <Table.Th>Destino</Table.Th>
              <Table.Th ta="right">Subtotal</Table.Th>
              <Table.Th>Estado</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(filas ?? []).map((f) => (
              <Table.Tr
                key={f.fila}
                style={{ cursor: "pointer", background: f.fila === fila ? "var(--el-surface-2, rgba(47,111,221,0.08))" : undefined }}
                onClick={() => {
                  setValor(f.fila);
                  onElegir(f.fila);
                }}
              >
                <Table.Td data-label="Fila" ff="monospace">
                  {f.fila}
                </Table.Td>
                <Table.Td data-label="Fecha">{fechaCorta(f.datos.fecha)}</Table.Td>
                <Table.Td data-label="Cliente">{f.datos.cliente ?? "—"}</Table.Td>
                <Table.Td data-label="Destino">
                  <Text size="sm" lineClamp={1}>
                    {f.datos.destino ?? "—"}
                  </Text>
                </Table.Td>
                <Table.Td ta="right" data-label="Subtotal">
                  {f.datos.subtotal != null ? pesos(Number(f.datos.subtotal)) : "—"}
                </Table.Td>
                <Table.Td>
                  <EstadoFila fila={f} />
                </Table.Td>
              </Table.Tr>
            ))}
            {filas?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text size="sm" c="dimmed">
                    No hay filas recientes {soloPendientes ? "sin factura" : ""}.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      )}
    </Card>
  );
}

// --- Lugar (origen / destino) --------------------------------------------------------------

interface LugarDraft {
  texto: string;
  modo: "catalogo" | "nuevo";
  lugarId: string | null;
  nuevoNombre: string;
  nuevoCp: string;
  confianza: PropuestaLugar["confianza"] | "manual";
  fuente: PropuestaLugar["fuente"] | "manual";
  candidatos: PropuestaLugar["candidatos"];
}

interface DestinoDraft extends LugarDraft {
  key: string;
  folio: string;
  sinAcuse: boolean;
  archivo: File | null;
  mercanciaId: string | null;
  pesoKg: number | null;
  cantidad: number | null;
}

function lugarDraft(p: PropuestaLugar | null, texto = ""): LugarDraft {
  return {
    texto: p?.texto ?? texto,
    modo: p?.lugar ? "catalogo" : "nuevo",
    lugarId: p?.lugar?.id ?? null,
    nuevoNombre: limpiarNombre(p?.texto ?? texto),
    nuevoCp: CP_GENERICO,
    confianza: p?.lugar ? p.confianza : "ninguna",
    fuente: p?.fuente ?? null,
    candidatos: p?.candidatos ?? [],
  };
}

function BadgeConfianza({ d }: { d: LugarDraft }) {
  if (d.modo === "nuevo") return <Badge color="gray" variant="light">Nuevo · RFC genérico</Badge>;
  if (d.fuente === "manual") return <Badge color="blue" variant="light">Elegido</Badge>;
  if (d.fuente === "recordado") return <Badge color="blue" variant="light">Recordado</Badge>;
  if (d.fuente === "predeterminado") return <Badge color="green" variant="light">Origen del cliente</Badge>;
  if (d.confianza === "alta") return <Badge color="green" variant="light">Encontrado</Badge>;
  if (d.confianza === "media") return <Badge color="yellow" variant="light">Revisa</Badge>;
  return <Badge color="gray" variant="light">No está en el catálogo</Badge>;
}

function LugarEditor({
  clienteId,
  draft,
  onChange,
  label,
}: {
  clienteId: string;
  draft: LugarDraft;
  onChange: (d: Partial<LugarDraft>) => void;
  label: string;
}) {
  const otros = draft.candidatos.filter((c) => c.id !== draft.lugarId && c.score >= 0.25).slice(0, 4);
  return (
    <Stack gap={6}>
      <SegmentedControl
        size="xs"
        value={draft.modo}
        onChange={(v) => onChange({ modo: v as LugarDraft["modo"] })}
        data={[
          { value: "catalogo", label: "Del catálogo" },
          { value: "nuevo", label: "No está: darlo de alta" },
        ]}
        style={{ alignSelf: "flex-start" }}
      />
      {draft.modo === "catalogo" ? (
        <>
          <LugarSelect
            clienteId={clienteId}
            label={label}
            value={draft.lugarId}
            onChange={(id) => onChange({ lugarId: id, fuente: "manual", confianza: "manual" })}
          />
          {otros.length > 0 && (
            <Group gap={6}>
              <Text size="xs" c="dimmed">
                {draft.lugarId ? "¿O es…?" : "¿Es alguno de estos?"}
              </Text>
              {otros.map((c) => (
                <Button
                  key={c.id}
                  size="compact-xs"
                  variant="light"
                  onClick={() => onChange({ lugarId: c.id, modo: "catalogo", fuente: "manual", confianza: "manual" })}
                >
                  {c.nombre}
                </Button>
              ))}
            </Group>
          )}
        </>
      ) : (
        <>
          <div className="el-grid-form">
            <TextInput
              label="Nombre del lugar"
              value={draft.nuevoNombre}
              onChange={(e) => onChange({ nuevoNombre: e.currentTarget.value })}
              error={!draft.nuevoNombre.trim() ? "Escribe el nombre" : undefined}
            />
            <TextInput
              label="Código postal"
              value={draft.nuevoCp}
              maxLength={5}
              onChange={(e) => onChange({ nuevoCp: e.currentTarget.value.replace(/\D/g, "") })}
              error={!/^\d{5}$/.test(draft.nuevoCp) ? "5 dígitos" : undefined}
            />
          </div>
          <Text size="xs" c="dimmed">
            Se da de alta en los lugares del cliente con RFC XAXX010101000 (genérico), Estado de México y 70 km.
          </Text>
        </>
      )}
    </Stack>
  );
}

// --- Avisos de REF repetida y servicios cercanos (errores comunes con Chemital) ---------------

function cuando(dias: number): string {
  if (dias === 0) return "mismo día";
  const n = Math.abs(dias);
  return dias < 0 ? `${n} día${n === 1 ? "" : "s"} antes` : `${n} día${n === 1 ? "" : "s"} después`;
}

function AvisoRefRepetida({ otros, enLaFila }: { otros: ServicioConRef[] | undefined; enLaFila: boolean }) {
  if (!otros?.length && !enLaFila) return null;
  return (
    <Alert color="yellow" variant="light" p="xs" icon={<IconAlertTriangle size={16} />}>
      <Stack gap={2}>
        {enLaFila && <Text size="sm">Esta REF ya la pusiste en otro destino de esta misma fila.</Text>}
        {otros?.map((s) => (
          <Text key={s.servicio_id} size="sm">
            Esta REF ya está en el{" "}
            <Anchor component={Link} to={`/admin/servicios/${s.servicio_id}`} target="_blank" size="sm">
              servicio #{s.numero}
            </Anchor>{" "}
            del {fechaDMY(s.fecha)}
            {s.destinos.length ? ` (${s.destinos.join(", ")})` : ""}
            {s.factura_folio ? ` · factura ${s.factura_folio}` : ""}.
          </Text>
        ))}
      </Stack>
    </Alert>
  );
}

function ServiciosCercanos({ cliente, dias, servicios }: { cliente: string; dias: number; servicios: ServicioCercano[] }) {
  if (servicios.length === 0) return null;
  return (
    <Alert
      color="yellow"
      variant="light"
      icon={<IconAlertTriangle size={18} />}
      title={`${servicios.length} servicio${servicios.length === 1 ? "" : "s"} de ${cliente} a ±${dias} días: revisa que no confundas las REF`}
    >
      <Table verticalSpacing={4} className="el-cardtable" fz="sm">
        <Table.Tbody>
          {servicios.map((s) => (
            <Table.Tr key={s.servicio_id}>
              <Table.Td data-label="Servicio">
                <Anchor component={Link} to={`/admin/servicios/${s.servicio_id}`} target="_blank" size="sm">
                  #{s.numero}
                </Anchor>
              </Table.Td>
              <Table.Td data-label="Fecha">
                {fechaDMY(s.fecha)} <Text span size="xs" c="dimmed">({cuando(s.dias)})</Text>
              </Table.Td>
              <Table.Td data-label="REF" ff="monospace">
                {s.refs.length ? s.refs.join(", ") : "—"}
              </Table.Td>
              <Table.Td data-label="Destinos">{s.destinos.join(", ") || "—"}</Table.Td>
              <Table.Td data-label="Factura">{s.factura_folio ?? "Sin factura"}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Alert>
  );
}

// --- Fila → servicio -------------------------------------------------------------------------

function ResumenExcel({ fila, datos }: { fila: number; datos: DatosFila }) {
  const campos: [string, unknown][] = [
    ["Fecha", fechaCorta(datos.fecha)],
    ["Cliente", datos.cliente],
    ["Operador", datos.operador],
    ["Unidad", datos.unidad],
    ["Origen", datos.origen],
    ["Destino", datos.destino],
    ["Subtotal", datos.subtotal != null ? pesos(Number(datos.subtotal)) : null],
    ["Notas", datos.notas],
  ];
  return (
    <Stack gap={4}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
        Fila {fila} del Excel
      </Text>
      <Group gap="lg" wrap="wrap" align="flex-start">
        {campos
          .filter(([, v]) => v != null && v !== "")
          .map(([k, v]) => (
            <div key={k} style={{ minWidth: 0 }}>
              <Text size="xs" c="dimmed">
                {k}
              </Text>
              <Text size="sm" fw={500}>
                {String(v)}
              </Text>
            </div>
          ))}
      </Group>
    </Stack>
  );
}

function FilaEditor({
  propuesta,
  onCambiarCliente,
}: {
  propuesta: Propuesta;
  onCambiarCliente: (id: string | null) => void;
}) {
  const navigate = useNavigate();
  const crear = useCrearDesdeFila(propuesta.fila);
  const { data: clientes } = clientesApi.useList("true", "");
  const { data: operadores } = operadoresApi.useList("true", "");
  const { data: unidades } = unidadesApi.useList("true", "");

  const clienteId = propuesta.cliente?.id ?? null;
  const { data: mercancias } = useMercancias(clienteId);
  const cliente = clientes?.items.find((c) => c.id === clienteId);

  const [operadorId, setOperadorId] = useState<string | null>(propuesta.operador?.id ?? null);
  const [unidadId, setUnidadId] = useState<string | null>(propuesta.unidad?.id ?? null);
  const [fecha, setFecha] = useState(propuesta.fecha ?? "");
  const [subtotal, setSubtotal] = useState<number | null>(propuesta.subtotal ? Number(propuesta.subtotal) : null);
  const [origen, setOrigen] = useState<LugarDraft>(lugarDraft(propuesta.origen, propuesta.datos.origen ?? ""));
  const [destinos, setDestinos] = useState<DestinoDraft[]>(() =>
    (propuesta.destinos ?? []).map((p, i) => ({
      ...lugarDraft(p),
      key: nuevoKey(),
      folio: "",
      sinAcuse: false,
      archivo: null,
      mercanciaId: propuesta.mercancia_sugerida_id,
      pesoKg: i === 0 ? propuesta.kg_sugerido : null,
      cantidad: 1,
    })),
  );
  const [intentado, setIntentado] = useState(false);
  const [subiendo, setSubiendo] = useState(false);

  const modoAcuse = propuesta.modo_acuse;
  const yaCreado = propuesta.servicio;

  // REF repetida: se consulta mientras escribe (con pausa) contra los servicios del cliente.
  const refsKey =
    modoAcuse === "referencia"
      ? destinos
          .filter((d) => !d.sinAcuse && d.folio.trim())
          .map((d) => d.folio.trim())
          .join("\u0001")
      : "";
  const [refsDebounced] = useDebouncedValue(refsKey, 400);
  const { data: repetidas } = useRefsRepetidas(
    clienteId,
    refsDebounced ? refsDebounced.split("\u0001") : [],
    yaCreado?.servicio_id,
  );
  const { data: cercanos } = useServiciosCercanos(clienteId, fecha, yaCreado?.servicio_id);
  function refEnLaFila(d: DestinoDraft): boolean {
    const n = normalizarRef(d.folio);
    return !!d.folio.trim() && destinos.some((x) => x.key !== d.key && !x.sinAcuse && x.folio.trim() && normalizarRef(x.folio) === n);
  }

  function cambiarDestino(key: string, cambios: Partial<DestinoDraft>) {
    setDestinos((ds) => ds.map((d) => (d.key === key ? { ...d, ...cambios } : d)));
  }

  function agregarDestino() {
    setDestinos((ds) => [
      ...ds,
      {
        ...lugarDraft(null),
        modo: "catalogo",
        key: nuevoKey(),
        folio: "",
        sinAcuse: false,
        archivo: null,
        mercanciaId: propuesta.mercancia_sugerida_id,
        pesoKg: null,
        cantidad: 1,
      },
    ]);
  }

  function errorLugar(d: LugarDraft): string | null {
    if (d.modo === "catalogo") return d.lugarId ? null : "Elige el lugar o márcalo como nuevo";
    if (!d.nuevoNombre.trim()) return "Escribe el nombre del lugar nuevo";
    return /^\d{5}$/.test(d.nuevoCp) ? null : "El código postal debe tener 5 dígitos";
  }

  function erroresDestino(d: DestinoDraft): string[] {
    const e: string[] = [];
    const l = errorLugar(d);
    if (l) e.push(l);
    if (!d.sinAcuse && modoAcuse === "referencia" && !d.folio.trim()) e.push("Captura la REF o marca que no tiene");
    if (!d.sinAcuse && modoAcuse === "escaneo" && !d.archivo) e.push("Sube el escaneo o marca que no tiene");
    if (!d.mercanciaId) e.push("Elige la mercancía");
    if (!(d.pesoKg && d.pesoKg > 0)) e.push("Captura los kg");
    return e;
  }

  const errores: string[] = [];
  if (!clienteId) errores.push("Elige el cliente");
  if (!operadorId) errores.push("Elige el operador");
  if (!unidadId) errores.push("Elige la unidad");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) errores.push("Captura la fecha");
  const errOrigen = errorLugar(origen);
  if (errOrigen) errores.push(`Origen: ${errOrigen}`);
  if (destinos.length === 0) errores.push("Agrega al menos un destino");
  destinos.forEach((d, i) => erroresDestino(d).forEach((e) => errores.push(`Destino ${i + 1}: ${e}`)));

  function lugarIn(d: LugarDraft) {
    return d.modo === "catalogo"
      ? { texto_excel: d.texto || null, lugar_id: d.lugarId }
      : { texto_excel: d.texto || null, nuevo: { nombre: d.nuevoNombre.trim(), codigo_postal: d.nuevoCp } };
  }

  async function crearServicio() {
    setIntentado(true);
    if (errores.length > 0 || !clienteId || !operadorId || !unidadId) return;
    const body: CrearDesdeFilaIn = {
      cliente_id: clienteId,
      operador_id: operadorId,
      unidad_id: unidadId,
      fecha,
      subtotal,
      origen: lugarIn(origen),
      destinos: destinos.map((d) => ({
        ...lugarIn(d),
        folio: modoAcuse === "referencia" && !d.sinAcuse ? d.folio.trim() : null,
        sin_acuse: d.sinAcuse,
        distancia_km: null,
        mercancias: [{ mercancia_frecuente_id: d.mercanciaId!, peso_kg: d.pesoKg!, cantidad: d.cantidad || 1 }],
      })),
    };
    const servicio = await crear.mutateAsync(body).catch(() => null);
    if (!servicio) return;
    // Escaneos: uno por destino, en el orden de los viajes de entrega.
    const entregas = servicio.viajes.filter((v) => v.tipo === "entrega").sort((a, b) => a.orden - b.orden);
    const pendientes = destinos.map((d, i) => ({ d, viaje: entregas[i] })).filter(({ d, viaje }) => d.archivo && !d.sinAcuse && viaje);
    if (pendientes.length) {
      setSubiendo(true);
      for (const { d, viaje } of pendientes) {
        const form = new FormData();
        form.append("file", d.archivo!);
        try {
          await api.post(`/api/v1/viajes/${viaje.id}/acuses`, form);
        } catch (err) {
          notifications.show({
            color: "red",
            title: `No se subió el escaneo de ${viaje.destino?.nombre ?? "un destino"}`,
            message: err instanceof ApiError ? err.message : "Súbelo desde Facturar.",
          });
        }
      }
      setSubiendo(false);
    }
    notifications.show({ color: "green", message: `Servicio #${servicio.numero} creado. Revisa y timbra.` });
    navigate(`/admin/servicios/${servicio.id}/facturar`);
  }

  return (
    <Stack gap="md">
      <Card>
        <Stack gap="sm">
          <ResumenExcel fila={propuesta.fila} datos={propuesta.datos} />
          {propuesta.avisos.length > 0 && (
            <Alert color="yellow" variant="light" icon={<IconAlertTriangle size={18} />} p="sm">
              <Stack gap={2}>
                {propuesta.avisos.map((a) => (
                  <Text key={a} size="sm">
                    {a}
                  </Text>
                ))}
              </Stack>
            </Alert>
          )}
          {yaCreado && (
            <Group gap="xs">
              <Button component={Link} to={`/admin/servicios/${yaCreado.servicio_id}/facturar`} size="xs" variant="light">
                Ir a Facturar el servicio #{yaCreado.numero}
              </Button>
              {yaCreado.factura_id && (
                <Anchor component={Link} to={`/admin/facturas/${yaCreado.factura_id}`} size="sm">
                  Ver la factura {yaCreado.factura_folio}
                </Anchor>
              )}
            </Group>
          )}
        </Stack>
      </Card>

      <Card>
        <Text fw={600} mb="sm">
          Datos del servicio
        </Text>
        <div className="el-grid-form">
          <Select
            label="Cliente"
            searchable
            data={(clientes?.items ?? []).map((c) => ({ value: c.id, label: c.nombre_comercial }))}
            value={clienteId}
            onChange={onCambiarCliente}
            description={`Excel: ${propuesta.datos.cliente ?? "—"}`}
            error={intentado && !clienteId ? "Elige el cliente" : undefined}
          />
          <TextInput label="Fecha del servicio" type="date" value={fecha} onChange={(e) => setFecha(e.currentTarget.value)} />
          <Select
            label="Operador"
            searchable
            data={(operadores?.items ?? []).map((o) => ({ value: o.id, label: o.nombre }))}
            value={operadorId}
            onChange={setOperadorId}
            description={`Excel: ${propuesta.datos.operador ?? "—"}`}
            error={intentado && !operadorId ? "Elige el operador" : undefined}
          />
          <Select
            label="Unidad"
            searchable
            data={(unidades?.items ?? []).map((u) => ({ value: u.id, label: `${u.apodo} · ${u.placa}` }))}
            value={unidadId}
            onChange={setUnidadId}
            description={`Excel: ${propuesta.datos.unidad ?? "—"}`}
            error={intentado && !unidadId ? "Elige la unidad" : undefined}
          />
          <div>
            <NumberInput
              label="Subtotal"
              prefix="$"
              thousandSeparator=","
              decimalScale={2}
              min={0}
              value={subtotal ?? ""}
              onChange={(v) => setSubtotal(numberInputValue(v))}
              description={propuesta.datos.total != null ? `Excel: total ${pesos(Number(propuesta.datos.total))}` : undefined}
            />
            <TotalConIva subtotal={subtotal} regimenReceptor={cliente?.regimen_receptor} />
          </div>
        </div>
      </Card>

      {clienteId && cercanos && (
        <ServiciosCercanos cliente={cliente?.nombre_comercial ?? "este cliente"} dias={cercanos.dias} servicios={cercanos.servicios} />
      )}

      {!clienteId ? (
        <Alert color="gray" variant="light">
          Elige el cliente para buscar el origen y los destinos en sus lugares.
        </Alert>
      ) : (
        <>
          <Card>
            <Group justify="space-between" mb="xs" wrap="nowrap">
              <Text fw={600} style={{ minWidth: 0 }} truncate>
                Origen · Excel: “{propuesta.datos.origen ?? "—"}”
              </Text>
              <BadgeConfianza d={origen} />
            </Group>
            <LugarEditor clienteId={clienteId} draft={origen} label="Origen" onChange={(c) => setOrigen((o) => ({ ...o, ...c }))} />
          </Card>

          {destinos.map((d, i) => {
            const errs = intentado ? erroresDestino(d) : [];
            return (
              <Card key={d.key}>
                <Group justify="space-between" mb="xs" wrap="nowrap" gap="xs">
                  <Text fw={600} style={{ minWidth: 0 }} truncate>
                    Destino {i + 1}
                    {d.texto ? ` · Excel: “${d.texto}”` : ""}
                  </Text>
                  <Group gap={6} wrap="nowrap">
                    <BadgeConfianza d={d} />
                    <Tooltip label="Quitar este destino">
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        aria-label="Quitar destino"
                        onClick={() => setDestinos((ds) => ds.filter((x) => x.key !== d.key))}
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Group>
                <Stack gap="sm">
                  <LugarEditor
                    clienteId={clienteId}
                    draft={d}
                    label="Destino"
                    onChange={(c) => cambiarDestino(d.key, c)}
                  />
                  <div className="el-grid-form">
                    {modoAcuse === "referencia" && (
                      <TextInput
                        label="REF / folio del cliente"
                        placeholder={d.sinAcuse ? "No tiene" : "Ej. 5151"}
                        value={d.folio}
                        disabled={d.sinAcuse}
                        onChange={(e) => cambiarDestino(d.key, { folio: e.currentTarget.value })}
                      />
                    )}
                    {modoAcuse === "escaneo" && (
                      <FileInput
                        label="Escaneo del acuse (PDF)"
                        placeholder={d.sinAcuse ? "No tiene" : "Elegir PDF"}
                        accept="application/pdf"
                        clearable
                        value={d.archivo}
                        disabled={d.sinAcuse}
                        onChange={(f) => cambiarDestino(d.key, { archivo: f })}
                      />
                    )}
                    {modoAcuse !== "ninguno" && (
                      <Checkbox
                        mt={modoAcuse ? 28 : 0}
                        label={modoAcuse === "escaneo" ? "No tiene escaneo" : "No tiene REF"}
                        description="No se pone nada en la REF"
                        checked={d.sinAcuse}
                        onChange={(e) => cambiarDestino(d.key, { sinAcuse: e.currentTarget.checked })}
                      />
                    )}
                    <Select
                      label="Mercancía"
                      searchable
                      data={(mercancias ?? []).filter((m) => m.activo).map((m) => ({ value: m.id, label: m.nombre_humano }))}
                      value={d.mercanciaId}
                      onChange={(v) => cambiarDestino(d.key, { mercanciaId: v })}
                      nothingFoundMessage="El cliente no tiene mercancías en el catálogo"
                    />
                    <Group gap="xs" grow wrap="nowrap">
                      <NumberInput
                        label="Kg"
                        min={0}
                        decimalScale={2}
                        value={d.pesoKg ?? ""}
                        onChange={(v) => cambiarDestino(d.key, { pesoKg: numberInputValue(v) })}
                      />
                      <NumberInput
                        label="Cantidad"
                        min={1}
                        decimalScale={0}
                        value={d.cantidad ?? ""}
                        onChange={(v) => cambiarDestino(d.key, { cantidad: numberInputValue(v) })}
                      />
                    </Group>
                  </div>
                  {modoAcuse === "referencia" && !d.sinAcuse && (
                    <AvisoRefRepetida
                      otros={d.folio.trim() ? repetidas?.[normalizarRef(d.folio)] : undefined}
                      enLaFila={refEnLaFila(d)}
                    />
                  )}
                  {errs.length > 0 && (
                    <Text size="xs" c="var(--el-red)">
                      {errs.join(" · ")}
                    </Text>
                  )}
                </Stack>
              </Card>
            );
          })}

          <Group justify="space-between" wrap="wrap" gap="sm">
            <Button variant="default" leftSection={<IconPlus size={16} />} onClick={agregarDestino}>
              Agregar destino
            </Button>
            <Button
              size="md"
              onClick={crearServicio}
              loading={crear.isPending || subiendo}
              disabled={!!yaCreado}
            >
              Crear servicio y facturar
            </Button>
          </Group>
          {intentado && errores.length > 0 && (
            <Alert color="red" variant="light" p="sm">
              {errores.join(" · ")}
            </Alert>
          )}
        </>
      )}
    </Stack>
  );
}

export function FacturarExcelPage() {
  const [params, setParams] = useSearchParams();
  const fila = Number(params.get("fila")) || null;
  const [clienteElegido, setClienteElegido] = useState<{ fila: number | null; id: string | null }>({ fila: null, id: null });
  const clienteOverride = clienteElegido.fila === fila ? clienteElegido.id : null;
  const { data: registro } = useRegistro();
  const { data: propuesta, error, isFetching } = usePropuesta(registro ? fila : null, clienteOverride);

  function elegirFila(n: number) {
    setParams({ fila: String(n) });
  }

  return (
    <Stack gap="md">
      <ArchivoCard />
      {registro && <ElegirFila key={fila ?? "nada"} fila={fila} onElegir={elegirFila} />}
      {fila !== null && registro && (
        <>
          {error ? (
            <Alert color="red" variant="light">
              {error instanceof ApiError ? error.message : "No se pudo leer la fila"}
            </Alert>
          ) : !propuesta || propuesta.fila !== fila ? (
            <Skeleton height={300} />
          ) : (
            <div style={{ opacity: isFetching ? 0.6 : 1 }}>
              <FilaEditor
                key={`${propuesta.fila}-${propuesta.cliente?.id ?? "sin"}`}
                propuesta={propuesta}
                onCambiarCliente={(id) => setClienteElegido({ fila, id })}
              />
            </div>
          )}
        </>
      )}
    </Stack>
  );
}
