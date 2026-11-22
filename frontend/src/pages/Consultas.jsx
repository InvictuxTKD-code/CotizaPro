import { useCallback, useEffect, useState } from "react";
import { api, mensajesDeError } from "../api";
import { Errores } from "../components/ui.jsx";
import { fechaHora } from "../util.js";

export default function Consultas() {
  const [lista, setLista] = useState(null);
  const [soloPend, setSoloPend] = useState(true);
  const [errores, setErrores] = useState([]);

  const cargar = useCallback(async () => {
    try { setLista((await api.get("/chat/derivadas/", { params: soloPend ? { pendientes: 1 } : {} })).data); }
    catch (e) { setErrores(mensajesDeError(e)); }
  }, [soloPend]);
  useEffect(() => { cargar(); }, [cargar]);

  const atender = async (id) => { try { await api.post(`/chat/derivadas/${id}/atender/`); await cargar(); } catch (e) { setErrores(mensajesDeError(e)); } };

  return (
    <>
      <div className="encabezado"><div><h1>Consultas derivadas</h1><small>Conversaciones que el asistente no pudo resolver o donde la persona pidió hablar con alguien.</small></div></div>
      <Errores lista={errores} />
      <label className="check"><input type="checkbox" checked={soloPend} onChange={(e) => setSoloPend(e.target.checked)} /> Mostrar solo pendientes de contacto</label>
      {lista === null && <p className="suave">Cargando…</p>}
      {lista?.length === 0 && <div className="tarjeta"><p className="vacio">No hay consultas {soloPend ? "pendientes" : "derivadas"}.</p></div>}
      {lista?.map((c) => (
        <div className="tarjeta" key={c.id}>
          <div className="encabezado" style={{ marginBottom: ".5rem" }}>
            <div>
              <strong>Consulta #{c.id}</strong> <small>· {fechaHora(c.fecha_inicio)}</small>
              <div className="suave">{c.persona ? `${c.persona.nombre} · ${c.persona.correo}` : "Visitante"}{c.contacto ? ` · Contacto: ` : ""}{c.contacto && <strong>{c.contacto}</strong>}{!c.persona && !c.contacto && " · sin datos de contacto"}</div>
            </div>
            {c.atendida ? <span className="badge aprobada">Atendida</span> : <button className="btn exito peq" onClick={() => atender(c.id)}>Marcar como atendida</button>}
          </div>
          <div className="chat-hilo">{c.mensajes.map((m) => <div key={m.id} className={`burbuja ${m.emisor === "USUARIO" ? "usuario" : "asistente"}`}>{m.contenido}</div>)}</div>
        </div>
      ))}
    </>
  );
}
