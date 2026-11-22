import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { ROL } from "../util.js";
import ChatWidget from "./ChatWidget.jsx";
import { BotonTema } from "../tema.jsx";

export default function Layout() {
  const { usuario, salir, esStaff, esAdmin } = useAuth();
  return (
    <div className="app">
      <header className="topbar">
        <div className="marca"><span className="placa"><img src="/logo.png" alt="M y C Pinturas" /></span><div><strong>CotizaPro</strong><small>M y C Revestimientos y Pinturas</small></div></div>
        <nav>
          {esAdmin && <NavLink to="/dashboard">Dashboard</NavLink>}
          <NavLink to="/" end>{esStaff ? "Cotizaciones" : "Mis cotizaciones"}</NavLink>
          {!esStaff && <NavLink to="/nueva">Nueva cotización</NavLink>}
          {esStaff && <NavLink to="/consultas">Consultas</NavLink>}
          {esStaff && <NavLink to="/inventario">Inventario</NavLink>}
          {esAdmin && <NavLink to="/catalogo">Catálogo</NavLink>}
          {esAdmin && <NavLink to="/usuarios">Usuarios</NavLink>}
        </nav>
        <div className="sesion">
          <div><strong>{usuario.nombre}</strong><small>{ROL[usuario.rol]}</small></div>
          <BotonTema />
          <button className="btn sec peq" onClick={() => salir()}>Salir</button>
        </div>
      </header>
      <main className="contenido"><Outlet /></main>
      {!esStaff && <ChatWidget />}
    </div>
  );
}
