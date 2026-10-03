// `05-ui-spec §7.5` — sub-navegación de Catálogos: Unidades, Operadores, Clientes, Lugares.
import { Tabs } from "@mantine/core";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const TABS = [
  { value: "unidades", label: "Unidades" },
  { value: "operadores", label: "Operadores" },
  { value: "clientes", label: "Clientes" },
  { value: "lugares", label: "Lugares" },
];

export function CatalogosLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const activo = TABS.find((t) => location.pathname.includes(`/catalogos/${t.value}`))?.value ?? "unidades";

  return (
    <div>
      <Tabs
        value={activo}
        onChange={(value) => value && navigate(`/admin/catalogos/${value}`)}
        mb="lg"
      >
        <Tabs.List>
          {TABS.map((tab) => (
            <Tabs.Tab key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>
      </Tabs>
      <Outlet />
    </div>
  );
}
