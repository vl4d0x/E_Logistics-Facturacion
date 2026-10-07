// `05-ui-spec §5 PriceField/SuggestionBreakdown/MoneyBreakdown` — el subtotal es lo
// que más se edita, va primero y más grande; debajo, por qué ese número y el total.
import { Badge, Button, Divider, Group, NumberInput, Stack, Text } from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { calcularImpuestos, subtotalDesdeTotal } from "../../../lib/money";
import { numberInputValue } from "../../../lib/numberInput";
import type { RegimenReceptor } from "../../catalogos/types";
import type { PrecioSugerido } from "../types";

const CONFIANZA_COLOR: Record<string, string> = { alta: "green", media: "blue", baja: "gray" };

export function PriceField({
  subtotal,
  onChange,
  onCommit,
  regimenReceptor,
  precioSugerido,
}: {
  subtotal: number | null;
  onChange: (subtotal: number | null) => void;
  onCommit: () => void;
  regimenReceptor: RegimenReceptor;
  precioSugerido: PrecioSugerido;
}) {
  const [capturarTotal, setCapturarTotal] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const montos = subtotal != null ? calcularImpuestos(subtotal, regimenReceptor) : null;
  const sugeridoMonto = precioSugerido.monto ? Number(precioSugerido.monto) : null;
  const difiereDeSugerido = sugeridoMonto != null && subtotal != null && subtotal !== sugeridoMonto;

  function manejarTotal(total: number | null) {
    if (total == null) return;
    onChange(subtotalDesdeTotal(total, regimenReceptor));
  }

  return (
    <div>
      <Text size="sm" fw={600} c="dimmed" mb={4}>
        Subtotal
      </Text>
      {capturarTotal ? (
        <NumberInput
          ref={inputRef}
          size="xl"
          prefix="$"
          decimalScale={2}
          fixedDecimalScale
          value={montos?.total ?? undefined}
          onChange={(v) => manejarTotal(numberInputValue(v))}
          onBlur={onCommit}
          styles={{ input: { fontSize: 36, fontWeight: 700, height: "auto" } }}
        />
      ) : (
        <NumberInput
          ref={inputRef}
          size="xl"
          prefix="$"
          decimalScale={2}
          fixedDecimalScale
          value={subtotal ?? undefined}
          onChange={(v) => onChange(numberInputValue(v))}
          onBlur={onCommit}
          onKeyDown={(e) => e.key === "Enter" && onCommit()}
          styles={{ input: { fontSize: 36, fontWeight: 700, height: "auto" } }}
        />
      )}
      <Button variant="subtle" size="compact-xs" mt={4} onClick={() => setCapturarTotal((v) => !v)}>
        {capturarTotal ? "Capturar el subtotal" : "Capturar el total con IVA"}
      </Button>

      <Stack gap={4} mt="sm">
        {precioSugerido.monto ? (
          <>
            {precioSugerido.desglose.map((l, i) => (
              <Group key={i} justify="space-between">
                <Text size="sm" c="dimmed">
                  {l.concepto}
                </Text>
                <Text size="sm">${l.monto}</Text>
              </Group>
            ))}
            <Group justify="space-between">
              <Group gap={6}>
                <Text size="sm" fw={600}>
                  = Subtotal sugerido
                </Text>
                {precioSugerido.confianza && (
                  <Badge size="xs" color={CONFIANZA_COLOR[precioSugerido.confianza]} variant="light">
                    confianza {precioSugerido.confianza}
                  </Badge>
                )}
              </Group>
              <Text size="sm" fw={600}>
                ${precioSugerido.monto}
              </Text>
            </Group>
            {difiereDeSugerido && (
              <Button
                variant="default"
                size="compact-xs"
                onClick={() => onChange(sugeridoMonto)}
                style={{ alignSelf: "flex-start" }}
              >
                Usar sugerido (${precioSugerido.monto})
              </Button>
            )}
          </>
        ) : (
          <Text size="sm" c="var(--el-faint)">
            Sin referencias para esta ruta
          </Text>
        )}
        {precioSugerido.ultimos_precios_ruta.length > 0 && (
          <Group gap={6}>
            <Text size="xs" c="dimmed">
              Últimos precios de esta ruta:
            </Text>
            {precioSugerido.ultimos_precios_ruta.map((p, i) => (
              <Button
                key={i}
                variant="default"
                size="compact-xs"
                onClick={() => onChange(Number(p.subtotal))}
              >
                ${p.subtotal} · {p.fecha}
              </Button>
            ))}
          </Group>
        )}
      </Stack>

      <Divider my="sm" />

      <Stack gap={4}>
        <Group justify="space-between">
          <Text size="sm">Subtotal</Text>
          <Text size="sm" ff="monospace">
            ${montos ? montos.subtotal.toFixed(2) : "0.00"}
          </Text>
        </Group>
        <Group justify="space-between">
          <Text size="sm">IVA 16%</Text>
          <Text size="sm" ff="monospace">
            ${montos ? montos.ivaTrasladado.toFixed(2) : "0.00"}
          </Text>
        </Group>
        <Group justify="space-between">
          <Text size="sm">{regimenReceptor === "moral" ? "Retención IVA 4%" : "Retención"}</Text>
          <Text size="sm" ff="monospace">
            {regimenReceptor === "moral" ? `−$${montos ? montos.ivaRetenido.toFixed(2) : "0.00"}` : "No aplica"}
          </Text>
        </Group>
        <Group justify="space-between">
          <Text fw={700}>Total</Text>
          <Text fw={700} ff="monospace">
            ${montos ? montos.total.toFixed(2) : "0.00"}
          </Text>
        </Group>
      </Stack>
    </div>
  );
}
