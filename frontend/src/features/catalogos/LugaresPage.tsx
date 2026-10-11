// `fase-1-catalogos.md` H1.5 — vista global de lugares.
import { Card } from "../../components/Card";
import { LugaresManager } from "./components/LugaresManager";

export function LugaresPage() {
  return (
    <Card>
      <LugaresManager />
    </Card>
  );
}
