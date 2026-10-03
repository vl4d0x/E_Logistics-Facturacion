import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ClienteDetailPage } from "../features/catalogos/ClienteDetailPage";
import { ClientesPage } from "../features/catalogos/ClientesPage";
import { CatalogosLayout } from "../features/catalogos/CatalogosLayout";
import { LugaresPage } from "../features/catalogos/LugaresPage";
import { OperadoresPage } from "../features/catalogos/OperadoresPage";
import { UnidadesPage } from "../features/catalogos/UnidadesPage";
import { ServicioDetailPage } from "../features/servicios/ServicioDetailPage";
import { ServicioFormPage } from "../features/servicios/ServicioFormPage";
import { ServiciosPage } from "../features/servicios/ServiciosPage";
import { LoginPage } from "../features/auth/LoginPage";
import { useAuth } from "../lib/useAuth";
import type { Rol } from "../lib/auth";
import { AdminLayout } from "../routes/admin/AdminLayout";
import { DashboardPage } from "../routes/admin/DashboardPage";
import { UsuariosPage } from "../routes/admin/configuracion/UsuariosPage";
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
          <Route path="servicios" element={<ServiciosPage />} />
          <Route path="servicios/nuevo" element={<ServicioFormPage />} />
          <Route path="servicios/:id" element={<ServicioDetailPage />} />
          <Route path="catalogos" element={<CatalogosLayout />}>
            <Route index element={<Navigate to="unidades" replace />} />
            <Route path="unidades" element={<UnidadesPage />} />
            <Route path="operadores" element={<OperadoresPage />} />
            <Route path="clientes" element={<ClientesPage />} />
            <Route path="clientes/:id" element={<ClienteDetailPage />} />
            <Route path="lugares" element={<LugaresPage />} />
          </Route>
          <Route path="configuracion" element={<Navigate to="usuarios" replace />} />
          <Route path="configuracion/usuarios" element={<UsuariosPage />} />
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
