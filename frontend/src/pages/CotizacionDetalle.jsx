import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api, descargarPdf, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import ItemsEditor, { itemVacio } from "../components/ItemsEditor.jsx";
import { Aviso, Campo, Errores, Estado } from "../components/ui.jsx";
import { clp, cod, fechaHora, num } from "../util.js";

export default function CotizacionDetalle() {
  const { id } = useParams();
  const { esStaff, esAdmin } = useAuth();
  const { state } = useLocation();
  const [c, setC] = useState(null);
  const [errores, setErrores] = useState([]);
  const [avisos, setAvisos] = useState(state?.avisos ?? []);
  const [ok, setOk] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [medidas, setMedidas] = useState(null); // null = cerrado
  const [acabados, setAcabados] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [encuesta, setEncuesta] = useState(null); // {puntaje, comentario, enviada}

  const cargar = useCallback(async () => {
    try { setC((await api.get(`/cotizaciones/${id}/`)).data); }
    catch (e) { setErrores(mensajesDeError(e)); }
  }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const ejecutar = async (fn, mensajeOk) => {
    setErrores([]); setOk(""); setOcupado(true);
    try { const r = await fn(); if (r?.data?.id) setC(r.data); setOk(mensajeOk); return r; }
    catch (e) { setErrores(mensajesDeError(e)); }
    finally { setOcupado(false); }
  };

  const abrirMedidas = async () => {
    if (!acabados.length) setAcabados((await api.get("/catalogo/acabados/")).data);
    const lista = acabados.length ? acabados : (await api.get("/catalogo/acabados/")).data;
    setAcabados(lista);
    setMedidas({ items: [itemVacio(lista)], num_pintores: c.num_pintores ?? "", semanas_obra: c.semanas_obra ?? "" });
  };

  const guardarMedidas = (e) => {
    e.preventDefault();
    return ejecutar(async () => {
      const r = await api.put(`/cotizaciones/${id}/medidas/`, {
        detalles: medidas.items.map((i) => ({ ...i, tipo_acabado: Number(i.tipo_acabado) })),
        num_pintores: medidas.num_pintores === "" ? null : Number(medidas.num_pintores),
        semanas_obra: medidas.semanas_obra === "" ? null : Number(medidas.semanas_obra),
      });
      setMedidas(null); setAvisos([]);
      return r;
    }, "Medidas guardadas y presupuesto calculado.");
  };

  const aprobar = async () => {
    if (!window.confirm(`¿Aprobar la cotización ${cod(id)}?` + (c.origen_materiales === "EMPRESA" ? " Se descontarán los materiales del inventario." : ""))) return;
    const r = await ejecutar(() => api.post(`/cotizaciones/${id}/aprobar/`), "Cotización aprobada.");
    setAlertas(r?.data?.alertas_reposicion ?? []);
  };
  const rechazar = async () => {
    const motivo = window.prompt("Motivo del rechazo (opcional):");
    if (motivo === null) return;
    await ejecutar(() => api.post(`/cotizaciones/${id}/rechazar/`, { motivo }), "Cotización rechazada.");
  };

  if (!c) return <><Errores lista={errores} /><p className="suave">Cargando…</p></>;
  const pendiente = c.estado === "PENDIENTE";
  const vendida = c.origen_materiales === "EMPRESA";

  return (
    <>
      <p className="migas"><Link to="/">← Volver</Link></p>
      <div className="encabezado">
        <div><h1>Presupuesto {cod(c.id)} <Estado valor={c.estado} /></h1><p className="suave">{c.nombre_obra} · {c.direccion_obra}, {c.ciudad}</p></div>
        <div className="acciones">
          {c.calculada && <button className="btn" onClick={() => descargarPdf(c.id).then(() => { if (!esStaff && c.encuesta_puntaje == null) setEncuesta((x) => x ?? { puntaje: 0, comentario: "" }); }).catch((e) => setErrores(mensajesDeError(e)))}>⬇ Descargar PDF</button>}
          {esStaff && pendiente && <button className="btn sec" onClick={abrirMedidas} disabled={ocupado}>Cargar medidas</button>}
          {esStaff && pendiente && c.calculada && <button className="btn sec" onClick={() => ejecutar(() => api.post(`/cotizaciones/${id}/calcular/`), "Presupuesto recalculado.")} disabled={ocupado}>Recalcular</button>}
          {esStaff && pendiente && <button className="btn peligro" onClick={rechazar} disabled={ocupado}>Rechazar</button>}
          {esAdmin && pendiente && c.calculada && <button className="btn exito" onClick={aprobar} disabled={ocupado}>Aprobar</button>}
        </div>
      </div>

      <Errores lista={errores} />
      {!c.calculada && (
        <div className="alerta info">
          <strong>El PDF aún no está disponible.</strong>{" "}
          {c.requiere_medicion
            ? "Falta la medición en terreno: cuando un supervisor cargue las medidas se calculará el presupuesto y podrás descargarlo."
            : "El presupuesto todavía no se ha calculado."}
        </div>
      )}
      {encuesta && !encuesta.enviada && (
        <div className="tarjeta">
          <h2>¿Qué tan satisfecho quedaste con tu cotización?</h2>
          <div className="estrellas" role="radiogroup" aria-label="Nota de 1 a 5">
            {[1, 2, 3, 4, 5].map((n) => <button key={n} type="button" role="radio" aria-checked={encuesta.puntaje === n} className={n <= encuesta.puntaje ? "on" : ""} onClick={() => setEncuesta({ ...encuesta, puntaje: n })} title={`${n} de 5`}>★</button>)}
            <small>{encuesta.puntaje ? `${encuesta.puntaje} de 5` : "1 = nada satisfecho · 5 = muy satisfecho"}</small>
          </div>
          <Campo etiqueta="Comentario (opcional)"><input maxLength={300} value={encuesta.comentario} onChange={(e) => setEncuesta({ ...encuesta, comentario: e.target.value })} /></Campo>
          <div className="acciones">
            <button className="btn" disabled={!encuesta.puntaje} onClick={async () => { try { await api.post(`/cotizaciones/${id}/encuesta/`, { puntaje: encuesta.puntaje, comentario: encuesta.comentario }); setEncuesta(null); setOk("¡Gracias por tu opinión!"); await cargar(); } catch (e) { setErrores(mensajesDeError(e)); } }}>Enviar</button>
            <button className="btn sec" onClick={() => setEncuesta(null)}>Ahora no</button>
          </div>
        </div>
      )}
      {ok && <div className="alerta ok">{ok}</div>}
      <Aviso lista={avisos} />
      {alertas.length > 0 && <div className="alerta warn"><strong>Reposición:</strong> quedaron bajo el mínimo {alertas.map((a) => `${a.nombre} (${num(a.stock_actual)} ${a.unidad})`).join(", ")}. Avisar al bodeguero.</div>}

      {medidas && (
        <form className="tarjeta" onSubmit={guardarMedidas}>
          <h2>Medidas tomadas en terreno</h2>
          <p className="suave">Los ítems que ingreses reemplazan a los actuales y se recalcula el presupuesto.</p>
          <ItemsEditor items={medidas.items} setItems={(items) => setMedidas({ ...medidas, items })} acabados={acabados} />
          {vendida && (
            <div className="fila">
              <Campo etiqueta="N° de pintores"><input type="number" min="0" value={medidas.num_pintores} onChange={(e) => setMedidas({ ...medidas, num_pintores: e.target.value })} /></Campo>
              <Campo etiqueta="Semanas de obra"><input type="number" min="1" value={medidas.semanas_obra} onChange={(e) => setMedidas({ ...medidas, semanas_obra: e.target.value })} /></Campo>
            </div>
          )}
          <div className="acciones"><button className="btn" disabled={ocupado}>Guardar y calcular</button><button type="button" className="btn sec" onClick={() => setMedidas(null)}>Cancelar</button></div>
        </form>
      )}

      <div className="grid2">
        <section className="tarjeta">
          <h2>Cliente</h2>
          <p><strong>{c.cliente_nombre}</strong></p>
          <p className="suave">Solicitada el {fechaHora(c.fecha_solicitud)}{c.fecha_calculo && <><br />Calculada el {fechaHora(c.fecha_calculo)}</>}</p>
          <p>{vendida ? "Obra vendida: el precio incluye materiales e insumos." : "Solo mano de obra: los materiales los pone el cliente."}</p>
          {c.observaciones && <p className="obs">{c.observaciones}</p>}
        </section>
        <section className="tarjeta">
          <h2>Historial de estados</h2>
          <ol className="timeline">
            {c.historial.map((h, i) => (
              <li key={i}><Estado valor={h.estado_nuevo} /> <span className="suave">{fechaHora(h.fecha)} · {h.usuario}</span></li>
            ))}
          </ol>
        </section>
      </div>

      <section className="tarjeta sin-padding">
        <h2 className="pad">Detalle de los trabajos</h2>
        {c.detalles.length === 0 ? <p className="vacio">{c.requiere_medicion ? "Pendiente de medición en terreno: un supervisor cargará las medidas." : "Sin ítems."}</p> : (
          <div className="tabla-wrap"><table>
            <thead><tr><th>#</th><th>Trabajo</th><th>Un.</th><th className="der">Cantidad</th><th className="der">P. unitario</th><th className="der">Subtotal</th>{esStaff && vendida && <th className="der">Material estimado</th>}</tr></thead>
            <tbody>
              {c.detalles.map((d, i) => (
                <tr key={d.id}>
                  <td>{i + 1}</td>
                  <td>{d.acabado}<small className="sub">{d.descripcion}</small></td>
                  <td>{d.unidad === "ML" ? "ml" : "m²"}</td>
                  <td className="der">{num(d.cantidad)}</td>
                  <td className="der">{clp(d.precio_unitario)}</td>
                  <td className="der">{clp(d.subtotal)}</td>
                  {esStaff && vendida && <td className="der suave">{d.cantidad_material ? `${num(d.cantidad_material, 0)} gal` : "—"}</td>}
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        {c.calculada && (
          <div className="totales">
            {c.iva > 0 && <><div><span>Neto</span><span>{clp(c.neto)}</span></div><div><span>IVA</span><span>{clp(c.iva)}</span></div></>}
            <div className="total"><span>{c.iva > 0 ? "Total" : "Total neto"}</span><span>{clp(c.total)}</span></div>
            {!(c.iva > 0) && <small>Valores netos, no incluyen IVA.</small>}
          </div>
        )}
      </section>

      {esStaff && vendida && c.calculada && (
        <section className="tarjeta interno">
          <h2>Información interna <small>(no visible para el cliente)</small></h2>
          <div className="grid3">
            <div><span className="suave">Costo estimado de materiales e insumos</span><strong>{clp(c.costo_interno_materiales)}</strong></div>
            <div><span className="suave">Margen estimado</span><strong>{clp(c.neto - c.costo_interno_materiales)}</strong></div>
            <div><span className="suave">Insumos a descontar</span><strong>{c.insumos.length ? c.insumos.map((i) => `${num(i.cantidad, 0)} ${i.material}`).join(" · ") : "—"}</strong></div>
          </div>
          <small className="suave">El costo usa los precios cargados en el catálogo de materiales; el margen no considera mano de obra propia.</small>
        </section>
      )}
    </>
  );
}
