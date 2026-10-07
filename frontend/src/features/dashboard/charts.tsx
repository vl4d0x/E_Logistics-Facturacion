// Gráficas del dashboard en SVG puro (`05 §7.6`): sin dependencias nuevas, tooltips nativos.
import { COBRADO, mesCorto, mesLabel, pesos, POR_COBRAR, type Mes } from "./api";

const GAP = 2; // separación de 2px entre segmentos (marks-and-anatomy)

interface DonutProps {
  datos: Mes;
  size: number;
  grosor: number;
  etiquetaCentro?: boolean;
  onCobrado: () => void;
  onPorCobrar: () => void;
  onCentro: () => void;
}

export function PeriodDonut({ datos, size, grosor, etiquetaCentro, onCobrado, onPorCobrar, onCentro }: DonutProps) {
  const cobrado = Number(datos.cobrado);
  const porCobrar = Number(datos.por_cobrar);
  const total = cobrado + porCobrar;
  const r = (size - grosor) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const arco = (valor: number) => (total > 0 ? Math.max(0, (valor / total) * circ - (valor > 0 && total > valor ? GAP : 0)) : 0);
  const aCobrado = arco(cobrado);
  const aPorCobrar = arco(porCobrar);
  const label = mesLabel(datos.mes);

  return (
    <svg width={size} height={size} role="img" aria-label={`Ingresos de ${label}: cobrado ${pesos(cobrado)}, por cobrar ${pesos(porCobrar)}`}>
      <circle cx={c} cy={c} r={r} fill="none" stroke="var(--el-line)" strokeWidth={grosor} />
      <g transform={`rotate(-90 ${c} ${c})`}>
        {aCobrado > 0 && (
          <circle
            cx={c} cy={c} r={r} fill="none" stroke={COBRADO} strokeWidth={grosor}
            strokeDasharray={`${aCobrado} ${circ}`} style={{ cursor: "pointer" }} onClick={onCobrado}
          >
            <title>{`Cobrado ${pesos(cobrado)} — ver facturas pagadas de ${label} →`}</title>
          </circle>
        )}
        {aPorCobrar > 0 && (
          <circle
            cx={c} cy={c} r={r} fill="none" stroke={POR_COBRAR} strokeWidth={grosor}
            strokeDasharray={`${aPorCobrar} ${circ}`} strokeDashoffset={-((cobrado / total) * circ)}
            style={{ cursor: "pointer" }} onClick={onPorCobrar}
          >
            <title>{`Por cobrar ${pesos(porCobrar)} — ver facturas por cobrar de ${label} →`}</title>
          </circle>
        )}
      </g>
      {etiquetaCentro && (
        <g style={{ cursor: "pointer" }} onClick={onCentro}>
          <title>{`Facturado en ${label}: ${pesos(total)} — ver sus facturas →`}</title>
          <rect x={c - 48} y={c - 15} width={96} height={30} rx={15} fill="#1f1f1d" />
          <text x={c} y={c + 5} textAnchor="middle" fontSize={14} fontWeight={700} fill="#fff">
            {pesos(total)}
          </text>
        </g>
      )}
    </svg>
  );
}

interface BarsProps {
  meses: Mes[];
  onSegmento: (mes: string, tipo: "cobrado" | "por_cobrar") => void;
  onBarra: (mes: string) => void;
}

export function MonthlyStackedBars({ meses, onSegmento, onBarra }: BarsProps) {
  const W = 640;
  const H = 220;
  const base = H - 28;
  const alto = base - 12;
  const maximo = Math.max(1, ...meses.map((m) => Number(m.facturado)));
  const paso = W / meses.length;
  const ancho = Math.min(28, paso - 10);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Ingresos por mes: cobrado y por cobrar">
      <line x1={0} x2={W} y1={base} y2={base} stroke="var(--el-line)" />
      {meses.map((m, i) => {
        const x = i * paso + (paso - ancho) / 2;
        const hCob = (Number(m.cobrado) / maximo) * alto;
        const hPor = (Number(m.por_cobrar) / maximo) * alto;
        const titulo = `${mesLabel(m.mes)} · Facturado ${pesos(m.facturado)}`;
        return (
          <g key={m.mes}>
            {/* zona clicable de la barra completa → Facturas del mes */}
            <rect x={i * paso} y={0} width={paso} height={base} fill="transparent" style={{ cursor: "pointer" }} onClick={() => onBarra(m.mes)}>
              <title>{`${titulo} — ver sus facturas →`}</title>
            </rect>
            {hCob > 0 && (
              <rect x={x} y={base - hCob} width={ancho} height={Math.max(0, hCob - (hPor > 0 ? GAP : 0))} rx={3} fill={COBRADO} style={{ cursor: "pointer" }} onClick={() => onSegmento(m.mes, "cobrado")}>
                <title>{`${mesLabel(m.mes)} · Cobrado ${pesos(m.cobrado)} — ver pagadas →`}</title>
              </rect>
            )}
            {hPor > 0 && (
              <rect x={x} y={base - hCob - hPor} width={ancho} height={hPor} rx={3} fill={POR_COBRAR} style={{ cursor: "pointer" }} onClick={() => onSegmento(m.mes, "por_cobrar")}>
                <title>{`${mesLabel(m.mes)} · Por cobrar ${pesos(m.por_cobrar)} — ver por cobrar →`}</title>
              </rect>
            )}
            <text x={i * paso + paso / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--el-muted, #6b6b66)">
              {mesCorto(m.mes)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
