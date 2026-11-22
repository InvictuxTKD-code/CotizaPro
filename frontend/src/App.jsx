import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Registro from "./pages/Registro.jsx";
import Cotizaciones from "./pages/Cotizaciones.jsx";
import NuevaCotizacion from "./pages/NuevaCotizacion.jsx";
import CotizacionDetalle from "./pages/CotizacionDetalle.jsx";
import Inventario from "./pages/Inventario.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Consultas from "./pages/Consultas.jsx";
import Catalogo from "./pages/Catalogo.jsx";
import Usuarios from "./pages/Usuarios.jsx";

function Protegida({ roles }) {
  const { usuario } = useAuth();
  if (!usuario) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(usuario.rol)) return <Navigate to="/" replace />;
  return <Outlet />;
}

export default function App() {
  const { usuario } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={usuario ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/registro" element={usuario ? <Navigate to="/" replace /> : <Registro />} />
      <Route element={<Protegida />}>
        <Route element={<Layout />}>
          <Route index element={<Cotizaciones />} />
          <Route path="cotizaciones/:id" element={<CotizacionDetalle />} />
          <Route element={<Protegida roles={["CLIENTE"]} />}>
            <Route path="nueva" element={<NuevaCotizacion />} />
          </Route>
          <Route element={<Protegida roles={["EJECUTIVO", "ADMINISTRADOR"]} />}>
            <Route path="inventario" element={<Inventario />} />
            <Route path="consultas" element={<Consultas />} />
          </Route>
          <Route element={<Protegida roles={["ADMINISTRADOR"]} />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="catalogo" element={<Catalogo />} />
            <Route path="usuarios" element={<Usuarios />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
