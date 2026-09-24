import { IconLogout } from "@tabler/icons-react";
import { Group } from "@mantine/core";
import { Outlet } from "react-router-dom";
import { useAuth } from "../../lib/useAuth";
import styles from "./OperadorLayout.module.css";

// OfflineBanner / PendingBadge (`specs/05-ui-spec.md §5, §8`) llegan en Fase 2 con la
// cola offline real; este es solo el shell.
export function OperadorLayout() {
  const { user, logout } = useAuth();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.title}>Elogistics</span>
        <Group gap={10}>
          <span className={styles.userName}>{user?.nombre}</span>
          <button
            type="button"
            className={styles.logoutButton}
            onClick={logout}
            aria-label="Cerrar sesión"
          >
            <IconLogout size={18} stroke={1.8} />
          </button>
        </Group>
      </header>

      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
