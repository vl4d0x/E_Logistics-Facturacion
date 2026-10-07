// `05 §7.6` — Dashboard: pendientes, ingresos por periodo y por mes, por cobrar y cancelaciones en espera.
import { ActionIcon, Badge, Button, Drawer, Group, ScrollArea, Select, Stack, Text, UnstyledButton } from "@mantine/core";
import { IconChevronLeft, IconChevronRight, IconRefresh } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "../../components/Card";
import {
  COBRADO, horaLocal, mesLabel, pesos, POR_COBRAR, useEnEspera, useIngresos, usePendientes, usePorCobrar,
} from "./api";
import { MonthlyStackedBars, PeriodDonut } from "./charts";

function DashCard({ titulo, actualizado, onRefresh, children }: { titulo: string; actualizado?: string; onRefresh?: () => void; children: ReactNode }) {
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Text size="xs" fw={600} tt="uppercase" c="dimmed">{titulo}</Text>
        {actualizado && (
          <Group gap={4}>
            <Text size="xs" c="dimmed">Actualizado a las {horaLocal(actualizado)}</Text>
            <ActionIcon variant="subtle" size="sm" aria-label="Refrescar" onClick={onRefresh}><IconRefresh size={14} /></ActionIcon>
          </Group>
        )}
      </Group>
      {children}
    </Card>
  );
}

function CountTile({ titulo, valor, detalle, to, color }: { titulo: string; valor: number | string; detalle?: string; to: string; color?: string }) {
  return (
    <UnstyledButton component={Link} to={to} style={{ display: "block" }}>
      <Card style={{ height: "100%" }}>
        <Text size="xs" fw={600} tt="uppercase" c="dimmed">{titulo}</Text>
        <Text fz={32} fw={700} lh={1.2} c={color}>{valor}</Text>
        {detalle && <Text size="xs" c="dimmed">{detalle}</Text>}
      </Card>
    </UnstyledButton>
  );
}

function Leyenda({ color, texto, onClick }: { color: string; texto: string; onClick: () => void }) {
  return (
    <UnstyledButton onClick={onClick} aria-label={texto}>
      <Group gap={6}>
        <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: "inline-block" }} />
        <Text size="sm">{texto}</Text>
      </Group>
    </UnstyledButton>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const hoy = new Date();
  const [anio, setAnio] = useState(hoy.getFullYear());
  const [mesSel, setMesSel] = useState(hoy.getMonth() + 1);
  const [anioCobrar, setAnioCobrar] = useState("todos");
  const [verTodos, setVerTodos] = useState(false);
  const [drawer, setDrawer] = useState(false);

  const { data: pend } = usePendientes();
  const { data: ing } = useIngresos(anio, mesSel);
  const { data: cobrar } = usePorCobrar(anioCobrar);
  const { data: espera } = useEnEspera();
  const refrescar = (clave: string) => () => client.invalidateQueries({ queryKey: ["dashboard", clave] });

  const periodo = ing?.periodo;
  const ir = (ruta: string) => navigate(ruta);
  const aCobranza = (tab: string, mes: string) => ir(`/admin/cobranza?tab=${tab}&mes=${mes}`);
  const mesTexto = periodo ? mesLabel(periodo.mes) : "";

  const aniosOpciones = [{ value: "todos", label: "Todos los años" }, ...[0, 1, 2].map((d) => ({ value: String(hoy.getFullYear() - d), label: String(hoy.getFullYear() - d) }))];
  const items = cobrar ? (verTodos ? cobrar.items : cobrar.items.slice(0, 5)) : [];
  const totalSaldo = cobrar?.items.reduce((s, i) => s + Number(i.saldo), 0) ?? 0;

  return (
    <Stack gap="md">
      <div className="el-grid-tiles">
        <CountTile
          titulo="Por facturar" valor={pend?.por_facturar ?? "—"} to="/admin/servicios?vista=por_facturar"
          detalle={pend && pend.por_facturar_anticipados > 0 ? `${pend.por_facturar_anticipados} anticipadas` : undefined}
        />
        <CountTile titulo="Acuses faltantes" valor={pend?.acuses_faltantes ?? "—"} to="/admin/servicios?vista=por_facturar" />
        <CountTile
          titulo="REP por emitir" valor={pend?.rep_por_emitir.pagos ?? "—"} to="/admin/cobranza?tab=pagos&rep_pendiente=true"
          detalle={pend?.rep_por_emitir.vence ? `vence el ${pend.rep_por_emitir.vence}` : undefined}
          color={pend && pend.rep_por_emitir.pagos > 0 ? POR_COBRAR : undefined}
        />
        <CountTile titulo="Inspecciones con fallas" valor={pend?.inspecciones_con_fallas ?? "—"} to="/admin/servicios" />
      </div>

      <div className="el-grid-cards">
        <DashCard titulo="Ingresos por periodo" actualizado={ing?.actualizado_at} onRefresh={refrescar("ingresos")}>
          {periodo && (
            <Stack align="center" gap="sm">
              <Group align="center" gap="lg" wrap="nowrap">
                <PeriodDonut
                  datos={periodo} size={170} grosor={26} etiquetaCentro
                  onCobrado={() => aCobranza("pagadas", periodo.mes)} onPorCobrar={() => aCobranza("por_cobrar", periodo.mes)}
                  onCentro={() => ir(`/admin/facturas?mes_emision=${periodo.mes}`)}
                />
                <Stack gap="xs">
                  {ing.meses_previos.map((m) => (
                    <UnstyledButton key={m.mes} onClick={() => {
                      const [a, mm] = m.mes.split("-").map(Number);
                      setAnio(a); setMesSel(mm);
                    }} aria-label={`Ver ${mesLabel(m.mes)}`}>
                      <Stack gap={0} align="center">
                        <PeriodDonut datos={m} size={64} grosor={10} onCobrado={() => undefined} onPorCobrar={() => undefined} onCentro={() => undefined} />
                        <Text size="xs" c="dimmed">{mesLabel(m.mes)}</Text>
                      </Stack>
                    </UnstyledButton>
                  ))}
                </Stack>
              </Group>
              <Text size="sm" fw={600}>{mesTexto}</Text>
              <Group gap="lg">
                <Leyenda color={COBRADO} texto={`Cobrado ${pesos(periodo.cobrado)}`} onClick={() => aCobranza("pagadas", periodo.mes)} />
                <Leyenda color={POR_COBRAR} texto={`Por cobrar ${pesos(periodo.por_cobrar)}`} onClick={() => aCobranza("por_cobrar", periodo.mes)} />
              </Group>
            </Stack>
          )}
        </DashCard>

        <DashCard titulo="Ingresos por mes" actualizado={ing?.actualizado_at} onRefresh={refrescar("ingresos")}>
          <Group justify="center" mb="xs" gap="xs">
            <ActionIcon variant="subtle" aria-label="Año anterior" onClick={() => setAnio(anio - 1)}><IconChevronLeft size={16} /></ActionIcon>
            <Text fw={600}>{anio}</Text>
            <ActionIcon variant="subtle" aria-label="Año siguiente" onClick={() => setAnio(anio + 1)}><IconChevronRight size={16} /></ActionIcon>
          </Group>
          {ing && (
            <>
              <MonthlyStackedBars
                meses={ing.por_mes}
                onSegmento={(mes, tipo) => aCobranza(tipo === "cobrado" ? "pagadas" : "por_cobrar", mes)}
                onBarra={(mes) => ir(`/admin/facturas?mes_emision=${mes}`)}
              />
              <Group justify="center" gap="lg" mt="xs">
                <Text size="xs">Facturado <b>{pesos(ing.totales_anio.facturado)}</b></Text>
                <Leyenda color={COBRADO} texto={`Cobrado ${pesos(ing.totales_anio.cobrado)}`} onClick={() => ir(`/admin/cobranza?tab=pagadas&anio=${anio}`)} />
                <Leyenda color={POR_COBRAR} texto={`Por cobrar ${pesos(ing.totales_anio.por_cobrar)}`} onClick={() => ir(`/admin/cobranza?tab=por_cobrar&anio=${anio}`)} />
              </Group>
            </>
          )}
        </DashCard>

      </div>

      <div className="el-grid-cards">
        <DashCard titulo="Por cobrar" actualizado={cobrar?.actualizado_at} onRefresh={refrescar("por-cobrar")}>
          <Select data={aniosOpciones} value={anioCobrar} onChange={(v) => v && setAnioCobrar(v)} allowDeselect={false} size="xs" w={160} mb="sm" aria-label="Año" />
          <ScrollArea.Autosize mah={verTodos ? 360 : undefined}>
            <Stack gap={6}>
              {items.map((i, idx) => (
                <UnstyledButton key={i.cliente.id} onClick={() => ir(`/admin/cobranza?tab=por_cobrar&cliente=${i.cliente.id}`)}>
                  <Group justify="space-between" wrap="nowrap">
                    <Text size="sm" truncate>{idx + 1}. {i.cliente.nombre_comercial}</Text>
                    <Text size="sm" fw={600} c={POR_COBRAR}>{pesos(i.saldo)}</Text>
                  </Group>
                </UnstyledButton>
              ))}
              {cobrar && cobrar.items.length === 0 && <Text size="sm" c="dimmed">Sin saldos por cobrar.</Text>}
            </Stack>
          </ScrollArea.Autosize>
          {cobrar && cobrar.total_clientes > 5 && (
            <Button variant="subtle" size="xs" mt="xs" onClick={() => setVerTodos(!verTodos)}>
              {verTodos ? "Ver menos" : `Ver todos (${cobrar.total_clientes} clientes)`}
            </Button>
          )}
          {verTodos && <Text size="xs" c="dimmed" mt="xs">Total: <b>{pesos(totalSaldo)}</b></Text>}
        </DashCard>

        <DashCard titulo="En espera" actualizado={espera?.actualizado_at} onRefresh={refrescar("en-espera")}>
          <UnstyledButton onClick={() => setDrawer(true)} aria-label="Ver solicitudes en espera">
            <Text fz={44} fw={700} lh={1.1}>{espera?.total ?? "—"}</Text>
            <Text size="sm" c="dimmed">Solicitudes de cancelación</Text>
          </UnstyledButton>
        </DashCard>
      </div>

      <Drawer opened={drawer} onClose={() => setDrawer(false)} title="Solicitudes en espera" position="right">
        <Stack gap="sm">
          {espera?.items.map((i) => (
            <Card key={`${i.tipo}-${i.id}`} style={{ padding: 12 }}>
              <Group justify="space-between">
                <Badge variant="light" color={i.tipo === "rep" ? "grape" : "blue"}>{i.tipo === "rep" ? "REP" : "Factura"}</Badge>
                <Text size="sm" fw={600}>{pesos(i.total)}</Text>
              </Group>
              <Text size="sm" mt={4}>
                <Link to={i.tipo === "rep" ? `/admin/cobranza/pagos/${i.pago_id}` : `/admin/facturas/${i.factura_id}`} onClick={() => setDrawer(false)}>{i.folio || "Sin folio"}</Link> · {i.cliente}
              </Text>
              <Text size="xs" c="dimmed">
                Solicitada {i.solicitada_at ? new Date(i.solicitada_at).toLocaleDateString("es-MX") : "—"}
              </Text>
            </Card>
          ))}
          {espera?.items.length === 0 && <Text c="dimmed" size="sm">No hay cancelaciones en espera.</Text>}
        </Stack>
      </Drawer>
    </Stack>
  );
}
