// `05-ui-spec §7.5` — sub-navegación de Configuración: Usuarios, Precios y tarifas.
import { Tabs } from "@mantine/core";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const TABS = [
  { value: "usuarios", label: "Usuarios" },
  { value: "precios", label: "Precios y tarifas" },
];

export function ConfiguracionLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const activo = TABS.find((t) => location.pathname.includes(`/configuracion/${t.value}`))?.value ?? "usuarios";

  return (
    <div>
      <Tabs value={activo} onChange={(v) => v && navigate(`/admin/configuracion/${v}`)} mb="lg">
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
