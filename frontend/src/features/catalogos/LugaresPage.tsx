// `fase-1-catalogos.md` H1.5 — vista global de lugares.
import { Card } from "../../components/Card";
import { ImportarKmCard } from "./components/ImportarKmCard";
import { LugaresManager } from "./components/LugaresManager";

export function LugaresPage() {
  return (
    <Card>
      <ImportarKmCard />
      <LugaresManager />
    </Card>
  );
}
