// `05-ui-spec §5 FuelGauge` — medidor de gasolina, aguja (octavos 0-8) o barras
// (0-N). Slider accesible (role="slider", flechas de teclado). Modo `input` o
// `readonly`. Emite el valor crudo; `nivel_combustible` (0-1) lo calcula el backend.
import { ActionIcon, Button, Group, Text } from "@mantine/core";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useRef } from "react";

const ETIQUETAS_OCTAVO = ["E", "", "¼", "", "½", "", "¾", "", "F"];

function anguloDesdeOctavo(octavos: number): number {
  // Semicírculo: 180° (izquierda, vacío) a 0° (derecha, lleno).
  return 180 - (octavos / 8) * 180;
}

function puntoEnArco(cx: number, cy: number, r: number, anguloGrados: number) {
  const rad = (anguloGrados * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

export function FuelGaugeAguja({
  octavos,
  onChange,
  readonly = false,
}: {
  octavos: number;
  onChange?: (octavos: number) => void;
  readonly?: boolean;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const cx = 110;
  const cy = 100;
  const r = 90;

  function octavoDesdeEvento(clientX: number, clientY: number): number {
    const svg = svgRef.current;
    if (!svg) return octavos;
    const rect = svg.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * 220 - cx;
    const y = cy - ((clientY - rect.top) / rect.height) * 110;
    let angulo = (Math.atan2(y, x) * 180) / Math.PI;
    angulo = Math.max(0, Math.min(180, angulo));
    const valor = Math.round(((180 - angulo) / 180) * 8);
    return Math.max(0, Math.min(8, valor));
  }

  function manejarPuntero(e: React.PointerEvent<SVGSVGElement>) {
    if (readonly || !onChange) return;
    (e.target as Element).setPointerCapture(e.pointerId);
    onChange(octavoDesdeEvento(e.clientX, e.clientY));
  }

  const agujaExtremo = puntoEnArco(cx, cy, r - 15, anguloDesdeOctavo(octavos));

  return (
    <div>
      <svg
        ref={svgRef}
        viewBox="0 0 220 115"
        width="100%"
        style={{ maxWidth: 260, touchAction: "none", cursor: readonly ? "default" : "pointer" }}
        role="slider"
        aria-label="Nivel de gasolina"
        aria-valuemin={0}
        aria-valuemax={8}
        aria-valuenow={octavos}
        aria-valuetext={`${octavos} de 8 octavos`}
        tabIndex={readonly ? -1 : 0}
        onPointerDown={manejarPuntero}
        onPointerMove={(e) => e.buttons === 1 && manejarPuntero(e)}
        onKeyDown={(e) => {
          if (readonly || !onChange) return;
          if (e.key === "ArrowRight" || e.key === "ArrowUp") onChange(Math.min(8, octavos + 1));
          if (e.key === "ArrowLeft" || e.key === "ArrowDown") onChange(Math.max(0, octavos - 1));
        }}
      >
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="var(--el-line)"
          strokeWidth={14}
          strokeLinecap="round"
        />
        {ETIQUETAS_OCTAVO.map((label, i) => {
          const p = puntoEnArco(cx, cy, r + 14, anguloDesdeOctavo(i));
          return (
            <text key={i} x={p.x} y={p.y} fontSize={11} textAnchor="middle" fill="var(--el-muted)">
              {label}
            </text>
          );
        })}
        <line
          x1={cx}
          y1={cy}
          x2={agujaExtremo.x}
          y2={agujaExtremo.y}
          stroke="var(--el-ink)"
          strokeWidth={3}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={6} fill="var(--el-ink)" />
      </svg>
      <Group justify="center" gap="md" mt={4}>
        {!readonly && onChange && (
          <ActionIcon
            variant="default"
            aria-label="Menos"
            onClick={() => onChange(Math.max(0, octavos - 1))}
          >
            <IconMinus size={14} />
          </ActionIcon>
        )}
        <Text size="sm" fw={600}>
          {octavoATexto(octavos)}
        </Text>
        {!readonly && onChange && (
          <ActionIcon
            variant="default"
            aria-label="Más"
            onClick={() => onChange(Math.min(8, octavos + 1))}
          >
            <IconPlus size={14} />
          </ActionIcon>
        )}
      </Group>
    </div>
  );
}

function octavoATexto(octavos: number): string {
  const mapa: Record<number, string> = {
    0: "Vacío",
    1: "⅛ de tanque",
    2: "¼ de tanque",
    3: "⅜ de tanque",
    4: "½ tanque",
    5: "⅝ de tanque",
    6: "¾ de tanque",
    7: "⅞ de tanque",
    8: "Lleno",
  };
  return mapa[octavos] ?? `${octavos}/8`;
}

export function FuelGaugeBarras({
  barras,
  total,
  onChange,
  readonly = false,
}: {
  barras: number;
  total: number;
  onChange?: (barras: number) => void;
  readonly?: boolean;
}) {
  return (
    <div>
      <Group
        gap={4}
        role="slider"
        aria-label="Nivel de gasolina"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={barras}
        aria-valuetext={`${barras} de ${total} barras`}
        tabIndex={readonly ? -1 : 0}
        onKeyDown={(e) => {
          if (readonly || !onChange) return;
          if (e.key === "ArrowRight" || e.key === "ArrowUp") onChange(Math.min(total, barras + 1));
          if (e.key === "ArrowLeft" || e.key === "ArrowDown") onChange(Math.max(0, barras - 1));
        }}
      >
        {Array.from({ length: total }, (_, i) => {
          const numero = i + 1;
          const llena = numero <= barras;
          return (
            <button
              key={i}
              type="button"
              disabled={readonly || !onChange}
              aria-hidden
              tabIndex={-1}
              onClick={() => onChange?.(numero)}
              style={{
                width: 20,
                height: 36,
                borderRadius: 4,
                border: "1px solid var(--el-line)",
                background: llena ? "var(--el-red)" : "var(--el-surface-2)",
                cursor: readonly || !onChange ? "default" : "pointer",
                padding: 0,
              }}
            />
          );
        })}
      </Group>
      <Group justify="space-between" mt={4}>
        <Text size="sm" fw={600}>
          {barras} de {total} barras
        </Text>
        {!readonly && onChange && (
          <Button variant="subtle" size="compact-xs" onClick={() => onChange(0)}>
            Vacío
          </Button>
        )}
      </Group>
    </div>
  );
}

export function FuelGauge({
  tipoMedidor,
  numBarras,
  lectura,
  onChange,
  readonly = false,
}: {
  tipoMedidor: "aguja" | "barras";
  numBarras: number | null;
  lectura: { octavos?: number; barras?: number } | null;
  onChange?: (lectura: { tipo: "aguja"; octavos: number } | { tipo: "barras"; barras: number; total: number }) => void;
  readonly?: boolean;
}) {
  if (tipoMedidor === "aguja") {
    return (
      <FuelGaugeAguja
        octavos={lectura?.octavos ?? 0}
        readonly={readonly}
        onChange={onChange ? (octavos) => onChange({ tipo: "aguja", octavos }) : undefined}
      />
    );
  }
  const total = numBarras ?? 8;
  return (
    <FuelGaugeBarras
      barras={lectura?.barras ?? 0}
      total={total}
      readonly={readonly}
      onChange={onChange ? (barras) => onChange({ tipo: "barras", barras, total }) : undefined}
    />
  );
}
