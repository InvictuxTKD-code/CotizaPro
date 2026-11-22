import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";

const LLAVE = "cotizapro_chat";
const SUGERENCIAS = ["¿Cómo puedo cotizar?", "¿Qué trabajos hacen?", "No tengo las medidas", "Hablar con una persona"];

function leer() { try { return JSON.parse(sessionStorage.getItem(LLAVE)) ?? null; } catch { return null; } }
function guardar(v) { try { v ? sessionStorage.setItem(LLAVE, JSON.stringify(v)) : sessionStorage.removeItem(LLAVE); } catch { /* sin storage */ } }

export default function ChatWidget() {
  const { usuario } = useAuth();
  const nav = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const [conv, setConv] = useState(leer); // {id, token}
  const [msgs, setMsgs] = useState([]);
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(false);
  const [derivada, setDerivada] = useState(false);
  const [accion, setAccion] = useState(null);
  const [contacto, setContacto] = useState("");
  const [contactoOk, setContactoOk] = useState(false);
  const [error, setError] = useState("");
  const fin = useRef(null);

  useEffect(() => {
    if (!abierto || msgs.length || !conv) return;
    api.get("/chat/historial/", { params: { conversacion: conv.id, token: conv.token } })
      .then((r) => { setMsgs(r.data.mensajes.map((m) => ({ de: m.emisor, texto: m.contenido }))); setDerivada(r.data.derivada); setContactoOk(Boolean(r.data.contacto)); })
      .catch(() => { guardar(null); setConv(null); });
  }, [abierto]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { fin.current?.scrollIntoView({ block: "end" }); }, [msgs, cargando, abierto]);

  const enviar = async (t) => {
    const contenido = (t ?? texto).trim();
    if (!contenido || cargando) return;
    setTexto(""); setError(""); setAccion(null); setCargando(true);
    setMsgs((m) => [...m, { de: "USUARIO", texto: contenido }]);
    try {
      const { data } = await api.post("/chat/mensaje/", { texto: contenido, ...(conv ? { conversacion: conv.id, token: conv.token } : {}) });
      const nueva = { id: data.conversacion, token: data.token };
      if (!conv) { setConv(nueva); guardar(nueva); }
      setMsgs((m) => [...m, { de: "ASISTENTE", texto: data.respuesta }]);
      setDerivada(data.derivada); setAccion(data.accion);
    } catch (e) { setError(mensajesDeError(e)[0] || "No pude responder ahora. Intenta de nuevo."); }
    finally { setCargando(false); }
  };

  const guardarContacto = async (e) => {
    e.preventDefault();
    try { await api.post("/chat/contacto/", { conversacion: conv.id, token: conv.token, contacto }); setContactoOk(true); }
    catch (err) { setError(mensajesDeError(err)[0]); }
  };
  const nueva = () => { guardar(null); setConv(null); setMsgs([]); setDerivada(false); setAccion(null); setContactoOk(false); setError(""); };
  const irCotizador = () => { setAbierto(false); nav(usuario ? "/nueva" : "/registro"); };

  return (
    <div className="chat">
      {abierto && (
        <section className="chat-panel" role="dialog" aria-label="Asistente virtual">
          <header><strong>Asistente M y C</strong><span><button type="button" onClick={nueva} title="Nueva conversación">↺</button><button type="button" onClick={() => setAbierto(false)} aria-label="Cerrar chat">✕</button></span></header>
          <div className="chat-msgs" aria-live="polite">
            <div className="burbuja asistente">¡Hola! Soy el asistente virtual de M y C. Resuelvo dudas sobre cómo cotizar y nuestros servicios. No entrego precios: los calcula el cotizador.</div>
            {msgs.map((m, i) => <div key={i} className={`burbuja ${m.de === "USUARIO" ? "usuario" : "asistente"}`}>{m.texto}</div>)}
            {cargando && <div className="burbuja asistente escribiendo">Escribiendo…</div>}
            {accion === "ir_cotizador" && <button type="button" className="btn peq" onClick={irCotizador}>{usuario ? "Ir a Nueva cotización" : "Registrarme para cotizar"}</button>}
            {derivada && !contactoOk && (
              <form className="chat-contacto" onSubmit={guardarContacto}>
                <small>Déjanos un correo o teléfono para que un Supervisor te contacte:</small>
                <div><input value={contacto} onChange={(e) => setContacto(e.target.value)} placeholder="correo o teléfono" maxLength={150} required /><button className="btn peq">Enviar</button></div>
              </form>
            )}
            {derivada && contactoOk && <div className="burbuja asistente">¡Listo! Un Supervisor te contactará.</div>}
            {error && <div className="alerta error">{error}</div>}
            <div ref={fin} />
          </div>
          {msgs.length === 0 && <div className="chat-sugerencias">{SUGERENCIAS.map((s) => <button key={s} type="button" onClick={() => enviar(s)}>{s}</button>)}</div>}
          <form className="chat-entrada" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
            <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu consulta…" maxLength={600} aria-label="Mensaje" />
            <button className="btn peq" disabled={cargando || !texto.trim()}>Enviar</button>
          </form>
        </section>
      )}
      <button type="button" className="chat-boton" onClick={() => setAbierto((a) => !a)} aria-expanded={abierto}>{abierto ? "Cerrar" : "💬 Asistente"}</button>
    </div>
  );
}
