import ChatWidget from "../components/ChatWidget.jsx";
import { BotonTema } from "../tema.jsx";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import { Campo, Errores } from "../components/ui.jsx";

export default function Registro() {
  const nav = useNavigate();
  const { entrar } = useAuth();
  const [f, setF] = useState({ tipo: "PARTICULAR", nombre: "", nombre_razon_social: "", rut: "", telefono: "", correo: "", password: "" });
  const [errores, setErrores] = useState([]);
  const [cargando, setCargando] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    setErrores([]);
    setCargando(true);
    try {
      await api.post("/auth/registro/", f);
      await entrar(f.correo, f.password);
      nav("/nueva");
    } catch (err) { setErrores(mensajesDeError(err)); }
    finally { setCargando(false); }
  };

  return (
    <div className="login-pagina">
      <BotonTema flotante />
      <ChatWidget />
      <form className="tarjeta login ancho" onSubmit={enviar}>
        <h1>Crear cuenta de cliente</h1>
        <Errores lista={errores} />
        <Campo etiqueta="Tipo de cliente">
          <select value={f.tipo} onChange={set("tipo")}><option value="PARTICULAR">Particular</option><option value="CONSTRUCTORA">Constructora / empresa</option></select>
        </Campo>
        <div className="fila">
          <Campo etiqueta="Tu nombre"><input value={f.nombre} onChange={set("nombre")} required /></Campo>
          <Campo etiqueta={f.tipo === "CONSTRUCTORA" ? "Razón social" : "Nombre para la cotización"}><input value={f.nombre_razon_social} onChange={set("nombre_razon_social")} required /></Campo>
        </div>
        <div className="fila">
          <Campo etiqueta="RUT" ayuda="Ej: 12.345.678-5"><input value={f.rut} onChange={set("rut")} required /></Campo>
          <Campo etiqueta="Teléfono"><input value={f.telefono} onChange={set("telefono")} /></Campo>
        </div>
        <Campo etiqueta="Correo"><input type="email" value={f.correo} onChange={set("correo")} required /></Campo>
        <Campo etiqueta="Contraseña" ayuda="Mínimo 8 caracteres, no solo números."><input type="password" value={f.password} onChange={set("password")} minLength={8} required autoComplete="new-password" /></Campo>
        <button className="btn" disabled={cargando}>{cargando ? "Creando…" : "Crear cuenta"}</button>
        <p className="centro"><Link to="/login">Ya tengo cuenta</Link></p>
      </form>
    </div>
  );
}
