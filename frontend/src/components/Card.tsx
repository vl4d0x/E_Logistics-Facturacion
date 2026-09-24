// `specs/05-ui-spec.md §5`: fondo --el-surface, borde 1px --el-line, radio 14, padding 16-20.
// Wrapper fino reutilizado en todas las fases — no reinventar tarjetas por pantalla.
import type { CSSProperties, ReactNode } from "react";

export function Card({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div
      style={{
        background: "var(--el-surface)",
        border: "1px solid var(--el-line)",
        borderRadius: 14,
        padding: "20px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
