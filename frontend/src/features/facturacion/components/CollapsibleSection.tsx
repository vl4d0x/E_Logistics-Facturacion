// `05-ui-spec §7.2` — secciones colapsadas en modo lectura: resumen + ✎ para editar.
import { Collapse, Group, Text, UnstyledButton } from "@mantine/core";
import { IconChevronDown, IconChevronRight, IconPencil } from "@tabler/icons-react";
import { useState } from "react";
import { Card } from "../../../components/Card";

export function CollapsibleSection({
  title,
  summary,
  children,
  forceOpen,
}: {
  title: string;
  summary: string;
  children: React.ReactNode;
  forceOpen?: boolean;
}) {
  const [manualOpen, setManualOpen] = useState(false);
  const open = manualOpen || Boolean(forceOpen);

  return (
    <Card style={forceOpen ? { border: "1px solid var(--el-warning-text)" } : undefined}>
      <UnstyledButton onClick={() => setManualOpen((v) => !v)} style={{ width: "100%" }}>
        <Group justify="space-between" wrap="nowrap">
          <Group gap={6} wrap="nowrap">
            {open ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
            <Text fw={600} size="sm">
              {title}
            </Text>
            {!open && (
              <Text size="sm" c="dimmed" truncate>
                {summary}
              </Text>
            )}
          </Group>
          <IconPencil size={14} color="var(--el-muted)" />
        </Group>
      </UnstyledButton>
      <Collapse expanded={open}>
        <div style={{ marginTop: 12 }}>{children}</div>
      </Collapse>
    </Card>
  );
}
