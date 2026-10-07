import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ClienteDetailPage } from "../features/catalogos/ClienteDetailPage";
import { ClientesPage } from "../features/catalogos/ClientesPage";
import { CatalogosLayout } from "../features/catalogos/CatalogosLayout";
import { LugaresPage } from "../features/catalogos/LugaresPage";
import { OperadoresPage } from "../features/catalogos/OperadoresPage";
import { UnidadesPage } from "../features/catalogos/UnidadesPage";
import { ServicioDetailPage } from "../features/servicios/ServicioDetailPage";
import { FacturarPage } from "../features/facturacion/FacturarPage";
import { ServicioFormPage } from "../features/servicios/ServicioFormPage";
import { ServiciosPage } from "../features/servicios/ServiciosPage";
import { LoginPage } from "../features/auth/LoginPage";
import { useAuth } from "../lib/useAuth";
import type { Rol } from "../lib/auth";
import { AdminLayout } from "../routes/admin/AdminLayout";
import { DashboardPage } from "../routes/admin/DashboardPage";
import { UsuariosPage } from "../routes/admin/configuracion/UsuariosPage";
import { FacturasPage } from "../features/facturas/FacturasPage";
import { CobranzaPage } from "../features/cobranza/CobranzaPage";
import { PagoDetailPage } from "../features/cobranza/PagoDetailPage";
import { FacturaDetailPage } from "../features/facturas/FacturaDetailPage";
import { ConfiguracionLayout } from "../routes/admin/configuracion/ConfiguracionLayout";
import { PreciosPage } from "../routes/admin/configuracion/PreciosPage";
import { OperadorLayout } from "../routes/operador/OperadorLayout";
import { MisServiciosPage } from "../features/operacion/MisServiciosPage";
import { ServicioOperadorPage } from "../features/operacion/ServicioOperadorPage";
import { TerminarViajeOperadorPage } from "../features/operacion/TerminarViajeOperadorPage";

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
          <Route path="servicios/:id/facturar" element={<FacturarPage />} />
          <Route path="facturas" element={<FacturasPage />} />
          <Route path="facturas/:id" element={<FacturaDetailPage />} />
          <Route path="cobranza" element={<CobranzaPage />} />
          <Route path="cobranza/pagos/:id" element={<PagoDetailPage />} />
          <Route path="catalogos" element={<CatalogosLayout />}>
            <Route index element={<Navigate to="unidades" replace />} />
            <Route path="unidades" element={<UnidadesPage />} />
            <Route path="operadores" element={<OperadoresPage />} />
            <Route path="clientes" element={<ClientesPage />} />
            <Route path="clientes/:id" element={<ClienteDetailPage />} />
            <Route path="lugares" element={<LugaresPage />} />
          </Route>
          <Route path="configuracion" element={<ConfiguracionLayout />}>
            <Route index element={<Navigate to="usuarios" replace />} />
            <Route path="usuarios" element={<UsuariosPage />} />
            <Route path="precios" element={<PreciosPage />} />
          </Route>
        </Route>
        <Route
          path="/operador/*"
          element={
            <RequireRole role="operador">
              <OperadorLayout />
            </RequireRole>
          }
        >
          <Route index element={<MisServiciosPage />} />
          <Route path="servicios/:id" element={<ServicioOperadorPage />} />
          <Route path="viajes/:id/terminar" element={<TerminarViajeOperadorPage />} />
        </Route>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}
