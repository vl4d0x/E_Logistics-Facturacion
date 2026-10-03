// `05-ui-spec §5 ChecklistToggle` — fila con etiqueta + Sí/No grandes, sin preselección.
import { Button, Group, Text } from "@mantine/core";

export function ChecklistToggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (value: boolean) => void;
}) {
  return (
    <Group
      justify="space-between"
      py="xs"
      px="sm"
      style={{
        borderRadius: 8,
        background: value === false ? "var(--el-warning-bg)" : "transparent",
      }}
    >
      <Text size="sm">{label}</Text>
      <Group gap="xs">
        <Button
          variant={value === true ? "filled" : "default"}
          color={value === true ? undefined : "gray"}
          h={44}
          miw={64}
          onClick={() => onChange(true)}
        >
          Sí
        </Button>
        <Button
          variant={value === false ? "filled" : "default"}
          color={value === false ? "yellow" : "gray"}
          h={44}
          miw={64}
          onClick={() => onChange(false)}
        >
          No
        </Button>
      </Group>
    </Group>
  );
}
