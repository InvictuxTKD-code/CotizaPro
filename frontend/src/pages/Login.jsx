import ChatWidget from "../components/ChatWidget.jsx";
import { BotonTema } from "../tema.jsx";
import { useState } from "react";
import { Link } from "react-router-dom";
import { mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import { Campo, Errores } from "../components/ui.jsx";

export default function Login() {
  const { entrar, aviso } = useAuth();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [errores, setErrores] = useState([]);
  const [cargando, setCargando] = useState(false);

  const enviar = async (e) => {
    e.preventDefault();
    setErrores([]);
    setCargando(true);
    try { await entrar(correo.trim(), password); }
    catch (err) { setErrores(mensajesDeError(err)); }
    finally { setCargando(false); }
  };

  return (
    <div className="login-pagina">
      <BotonTema flotante />
      <ChatWidget />
      <form className="tarjeta login" onSubmit={enviar}>
        <div className="marca-login"><img src="/logo.png" alt="M y C Pinturas" /><strong>CotizaPro</strong><small>Cotizaciones e inventario · M y C Revestimientos y Pinturas SpA</small></div>
        <h1>Iniciar sesión</h1>
        {aviso && <div className="alerta info">{aviso}</div>}
        <Errores lista={errores} />
        <Campo etiqueta="Correo"><input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} autoComplete="username" required autoFocus /></Campo>
        <Campo etiqueta="Contraseña"><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></Campo>
        <button className="btn" disabled={cargando}>{cargando ? "Ingresando…" : "Ingresar"}</button>
        <p className="centro">¿Eres cliente nuevo? <Link to="/registro">Crea tu cuenta</Link></p>
      </form>
    </div>
  );
}
