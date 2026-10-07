import {
  IconBooks,
  IconCoin,
  IconFileInvoice,
  IconLayoutDashboard,
  IconLogout,
  IconReceipt,
  IconSettings,
} from "@tabler/icons-react";
import { Burger, Drawer } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useEffect, type ComponentType } from "react";
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

function Marca() {
  return (
    <div className={styles.logo}>
      <div className={styles.logoMark}>E</div>
      <span className={styles.logoText}>Elogistics</span>
    </div>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className={styles.nav}>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/admin"}
          onClick={onNavigate}
          className={({ isActive }) => (isActive ? `${styles.navItem} ${styles.navItemActive}` : styles.navItem)}
        >
          <item.icon size={18} stroke={1.8} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

function UsuarioChip() {
  const { user, logout } = useAuth();
  return (
    <div className={styles.userChip}>
      <span className={styles.userName}>{user?.nombre}</span>
      <button type="button" className={styles.logoutButton} onClick={logout} aria-label="Cerrar sesión">
        <IconLogout size={18} stroke={1.8} />
      </button>
    </div>
  );
}

// Responsivo (`05-ui-spec §3.1`): a partir de 992px el menú es una barra lateral fija; en tablet y
// teléfono se oculta y se abre desde la hamburguesa de la barra superior, en un cajón.
export function AdminLayout() {
  const location = useLocation();
  const [menuAbierto, menu] = useDisclosure(false);
  const active =
    NAV_ITEMS.find((item) =>
      item.to === "/admin" ? location.pathname === "/admin" : location.pathname.startsWith(item.to),
    ) ?? NAV_ITEMS[0];

  useEffect(() => {
    menu.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <Marca />
        <NavLinks />
        <UsuarioChip />
      </aside>

      <Drawer opened={menuAbierto} onClose={menu.close} size={280} padding="md" title={<Marca />} hiddenFrom="md">
        <div className={styles.drawerBody}>
          <NavLinks onNavigate={menu.close} />
          <UsuarioChip />
        </div>
      </Drawer>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <Burger opened={menuAbierto} onClick={menu.toggle} hiddenFrom="md" size="sm" aria-label="Abrir menú" />
            <div>
              <div className={styles.topbarTitle}>{active.label}</div>
              <div className={styles.topbarSubtitle}>{active.subtitle}</div>
            </div>
          </div>
        </header>

        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
