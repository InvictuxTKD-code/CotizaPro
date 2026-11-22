import { useCallback, useEffect, useState } from "react";
import { api, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import { Campo, Errores } from "../components/ui.jsx";
import { ROL, fechaHora } from "../util.js";

export default function Usuarios() {
  const { usuario } = useAuth();
  const [lista, setLista] = useState(null);
  const [nuevo, setNuevo] = useState(null);
  const [errores, setErrores] = useState([]);
  const [ok, setOk] = useState("");
  const [borrar, setBorrar] = useState(null); // id en confirmación

  const cargar = useCallback(async () => {
    try { setLista((await api.get("/usuarios/")).data); } catch (e) { setErrores(mensajesDeError(e)); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const accion = async (fn, m) => {
    setErrores([]); setOk("");
    try { await fn(); setOk(m); await cargar(); return true; } catch (e) { setErrores(mensajesDeError(e)); return false; }
  };

  return (
    <>
      <div className="encabezado"><h1>Usuarios y roles</h1><button className="btn" onClick={() => setNuevo({ nombre: "", correo: "", rol: "EJECUTIVO", password: "" })}>+ Nuevo usuario</button></div>
      <Errores lista={errores} />
      {ok && <div className="alerta ok">{ok}</div>}
      {nuevo && (
        <form className="tarjeta" onSubmit={async (e) => { e.preventDefault(); if (await accion(() => api.post("/usuarios/", nuevo), "Usuario creado.")) setNuevo(null); }}>
          <h2>Nuevo usuario</h2>
          <div className="fila">
            <Campo etiqueta="Nombre"><input value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required /></Campo>
            <Campo etiqueta="Correo"><input type="email" value={nuevo.correo} onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })} required /></Campo>
          </div>
          <div className="fila">
            <Campo etiqueta="Rol"><select value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>{Object.entries(ROL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Campo>
            <Campo etiqueta="Contraseña inicial" ayuda="Mínimo 8 caracteres."><input type="password" minLength={8} value={nuevo.password} onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })} required autoComplete="new-password" /></Campo>
          </div>
          <div className="acciones"><button className="btn">Crear</button><button type="button" className="btn sec" onClick={() => setNuevo(null)}>Cancelar</button></div>
        </form>
      )}
      <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
        <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Último acceso</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          {lista === null && <tr><td colSpan={6} className="vacio">Cargando…</td></tr>}
          {lista?.map((u) => (
            <tr key={u.id}>
              <td><strong>{u.nombre}</strong></td><td>{u.correo}</td>
              <td><select value={u.rol} disabled={u.id === usuario.id} onChange={(e) => accion(() => api.patch(`/usuarios/${u.id}/`, { rol: e.target.value }), "Rol actualizado.")}>{Object.entries(ROL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td>{fechaHora(u.ultimo_acceso)}</td>
              <td>{u.activo ? <span className="badge aprobada">Activo</span> : <span className="badge rechazada">Desactivado</span>}</td>
              <td className="der">{u.id !== usuario.id && (borrar === u.id ? (
                <span className="acciones" style={{ justifyContent: "flex-end" }}>
                  <small>¿Eliminar definitivamente?</small>
                  <button className="btn peligro peq" onClick={async () => { await accion(() => api.delete(`/usuarios/${u.id}/`), `Usuario ${u.nombre} eliminado.`); setBorrar(null); }}>Sí, eliminar</button>
                  <button className="btn sec peq" onClick={() => setBorrar(null)}>No</button>
                </span>
              ) : (
                <>
                  <button className="btn sec peq" onClick={() => accion(() => api.patch(`/usuarios/${u.id}/`, { activo: !u.activo }), u.activo ? "Usuario desactivado." : "Usuario activado.")}>{u.activo ? "Desactivar" : "Activar"}</button>{" "}
                  <button className="btn peligro peq" onClick={() => { setErrores([]); setOk(""); setBorrar(u.id); }}>Eliminar</button>
                </>
              ))}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>
    </>
  );
}
