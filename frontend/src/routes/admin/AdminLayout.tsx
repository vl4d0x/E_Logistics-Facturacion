import {
  IconBooks,
  IconCoin,
  IconFileInvoice,
  IconLayoutDashboard,
  IconLogout,
  IconReceipt,
  IconSettings,
} from "@tabler/icons-react";
import type { ComponentType } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import styles from "./AdminLayout.module.css";

interface NavItem {
  label: string;
  subtitle: string;
  to: string;
  icon: ComponentType<{ size?: number | string; stroke?: number }>;
}

// `05-ui-spec §7`: "Dashboard · Servicios · Facturas · Cobranza · Catálogos · Configuración".
// Servicios/Facturas/Cobranza llegan en Fases 2/4/5 — se listan ya (como en Fase 0) para
// que la navegación no cambie de forma cuando se construyan; hoy no tienen pantalla.
const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", subtitle: "Ingresos y pendientes", to: "/admin", icon: IconLayoutDashboard },
  { label: "Servicios", subtitle: "Viajes, acuses y cierre", to: "/admin/servicios", icon: IconFileInvoice },
  { label: "Facturas", subtitle: "CFDI timbrados", to: "/admin/facturas", icon: IconReceipt },
  { label: "Cobranza", subtitle: "Pagos y REP", to: "/admin/cobranza", icon: IconCoin },
  {
    label: "Catálogos",
    subtitle: "Unidades, operadores, clientes, lugares",
    to: "/admin/catalogos",
    icon: IconBooks,
  },
  {
    label: "Configuración",
    subtitle: "Usuarios, precios y tarifas",
    to: "/admin/configuracion",
    icon: IconSettings,
  },
];

export function AdminLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const active =
    NAV_ITEMS.find((item) =>
      item.to === "/admin" ? location.pathname === "/admin" : location.pathname.startsWith(item.to),
    ) ?? NAV_ITEMS[0];

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoMark}>E</div>
          <span className={styles.logoText}>Elogistics</span>
        </div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/admin"}
              className={({ isActive }) =>
                isActive ? `${styles.navItem} ${styles.navItemActive}` : styles.navItem
              }
            >
              <item.icon size={18} stroke={1.8} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.userChip}>
          <span className={styles.userName}>{user?.nombre}</span>
          <button
            type="button"
            className={styles.logoutButton}
            onClick={logout}
            aria-label="Cerrar sesión"
          >
            <IconLogout size={18} stroke={1.8} />
          </button>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div>
            <div className={styles.topbarTitle}>{active.label}</div>
            <div className={styles.topbarSubtitle}>{active.subtitle}</div>
          </div>
        </header>

        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
