import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, onSesionExpirada, tokens } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

const MIN_INACTIVIDAD = Number(import.meta.env.VITE_INACTIVIDAD_MIN ?? 15); // HU01 criterio 4

function usuarioGuardado() {
  try { return JSON.parse(sessionStorage.getItem("usuario")); } catch { return null; }
}

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => (tokens.access ? usuarioGuardado() : null));
  const [aviso, setAviso] = useState("");
  const timer = useRef(null);

  const salir = useCallback((motivo = "") => {
    tokens.clear();
    setUsuario(null);
    setAviso(motivo);
  }, []);

  const entrar = async (correo, password) => {
    const { data } = await api.post("/auth/login/", { correo, password });
    tokens.set(data.access, data.refresh);
    try { sessionStorage.setItem("usuario", JSON.stringify(data.usuario)); } catch { /* ok */ }
    setAviso("");
    setUsuario(data.usuario);
    return data.usuario;
  };

  useEffect(() => { onSesionExpirada(() => salir("Tu sesión expiró. Ingresa nuevamente.")); }, [salir]);

  // Cierre automático por inactividad
  useEffect(() => {
    if (!usuario) return;
    const reiniciar = () => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => salir("Sesión cerrada por inactividad."), MIN_INACTIVIDAD * 60 * 1000);
    };
    const eventos = ["mousemove", "keydown", "click", "scroll", "touchstart"];
    eventos.forEach((e) => window.addEventListener(e, reiniciar, { passive: true }));
    reiniciar();
    return () => { eventos.forEach((e) => window.removeEventListener(e, reiniciar)); clearTimeout(timer.current); };
  }, [usuario, salir]);

  const esStaff = usuario && usuario.rol !== "CLIENTE";
  return <Ctx.Provider value={{ usuario, entrar, salir, aviso, setAviso, esStaff, esAdmin: usuario?.rol === "ADMINISTRADOR" }}>{children}</Ctx.Provider>;
}
