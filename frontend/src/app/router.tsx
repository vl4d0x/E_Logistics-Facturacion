import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "../features/auth/LoginPage";
import { useAuth } from "../lib/useAuth";
import type { Rol } from "../lib/auth";
import { AdminLayout } from "../routes/admin/AdminLayout";
import { DashboardPage } from "../routes/admin/DashboardPage";
import { OperadorLayout } from "../routes/operador/OperadorLayout";
import { MisViajesPage } from "../routes/operador/MisViajesPage";

function RequireRole({ role, children }: { role: Rol; children: ReactNode }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (user.rol !== role) {
    return <Navigate to={user.rol === "admin" ? "/admin" : "/operador"} replace />;
  }
  return <>{children}</>;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.rol === "admin" ? "/admin" : "/operador"} replace />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/admin/*"
          element={
            <RequireRole role="admin">
              <AdminLayout />
            </RequireRole>
          }
        >
          <Route index element={<DashboardPage />} />
        </Route>
        <Route
          path="/operador/*"
          element={
            <RequireRole role="operador">
              <OperadorLayout />
            </RequireRole>
          }
        >
          <Route index element={<MisViajesPage />} />
        </Route>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}
