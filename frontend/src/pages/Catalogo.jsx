import { useCallback, useEffect, useState } from "react";
import { api, mensajesDeError } from "../api";
import { Campo, Errores } from "../components/ui.jsx";
import { clp, fechaHora } from "../util.js";

const vacio = { nombre: "", unidad: "M2", precio_unitario: "", precio_mano_obra: "", material: "", rendimiento_m2: "", manos_recomendadas: 2, activo: true };

export default function Catalogo() {
  const [trabajos, setTrabajos] = useState(null);
  const [materiales, setMateriales] = useState([]);
  const [bitacora, setBitacora] = useState([]);
  const [form, setForm] = useState(null); // {id?, ...campos}
  const [errores, setErrores] = useState([]);
  const [ok, setOk] = useState("");

  const cargar = useCallback(async () => {
    try {
      const [t, m, b] = await Promise.all([api.get("/acabados/"), api.get("/materiales/"), api.get("/auditoria/", { params: { accion: "CREAR_TRABAJO,EDITAR_TRABAJO,CREAR_MATERIAL,EDITAR_MATERIAL", limite: 10 } })]);
      setTrabajos(t.data); setMateriales(m.data); setBitacora(b.data);
    } catch (e) { setErrores(mensajesDeError(e)); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const editar = (t) => setForm({ ...t, material: t.material ?? "", precio_mano_obra: t.precio_mano_obra ?? "", rendimiento_m2: t.rendimiento_m2 ?? "" });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const guardar = async (e) => {
    e.preventDefault(); setErrores([]); setOk("");
    const { id, material_nombre, ...c } = form;
    const cuerpo = { ...c, material: c.material === "" ? null : Number(c.material), precio_mano_obra: c.precio_mano_obra === "" ? null : c.precio_mano_obra, rendimiento_m2: c.rendimiento_m2 === "" ? null : c.rendimiento_m2 };
    try {
      if (id) await api.patch(`/acabados/${id}/`, cuerpo); else await api.post("/acabados/", cuerpo);
      setOk(id ? "Trabajo actualizado. Las cotizaciones ya aprobadas conservan su precio original." : "Trabajo creado."); setForm(null); await cargar();
    } catch (err) { setErrores(mensajesDeError(err)); }
  };
  const alternar = async (t) => {
    setErrores([]); setOk("");
    try { await api.patch(`/acabados/${t.id}/`, { activo: !t.activo }); await cargar(); } catch (err) { setErrores(mensajesDeError(err)); }
  };

  return (
    <>
      <div className="encabezado"><h1>Catálogo de trabajos y precios</h1><button className="btn" onClick={() => setForm({ ...vacio })}>+ Nuevo trabajo</button></div>
      <p className="nota">Los cambios de precio aplican a cotizaciones nuevas y pendientes que se recalculen; las ya aprobadas no se modifican. Los trabajos no se eliminan: se desactivan. Los precios de materiales se editan en <strong>Inventario</strong>.</p>
      <Errores lista={errores} />
      {ok && <div className="alerta ok">{ok}</div>}

      {form && (
        <form className="tarjeta" onSubmit={guardar}>
          <h2>{form.id ? "Editar trabajo" : "Nuevo trabajo"}</h2>
          <div className="fila tres">
            <Campo etiqueta="Nombre"><input value={form.nombre} onChange={(e) => set("nombre", e.target.value)} required /></Campo>
            <Campo etiqueta="Unidad de cobro"><select value={form.unidad} onChange={(e) => set("unidad", e.target.value)}><option value="M2">m²</option><option value="ML">metro lineal</option></select></Campo>
            <Campo etiqueta="Manos recomendadas"><input type="number" min="1" value={form.manos_recomendadas} onChange={(e) => set("manos_recomendadas", e.target.value)} required /></Campo>
          </div>
          <div className="fila tres">
            <Campo etiqueta="Precio unitario neto ($)" ayuda="Obra vendida: incluye materiales."><input type="number" min="0" value={form.precio_unitario} onChange={(e) => set("precio_unitario", e.target.value)} required /></Campo>
            <Campo etiqueta="Solo mano de obra ($)" ayuda="Cuando el cliente pone los materiales."><input type="number" min="0" value={form.precio_mano_obra} onChange={(e) => set("precio_mano_obra", e.target.value)} /></Campo>
            <Campo etiqueta="Material que consume"><select value={form.material} onChange={(e) => set("material", e.target.value)}><option value="">— Ninguno —</option>{materiales.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}</select></Campo>
          </div>
          <div className="fila">
            <Campo etiqueta="Rendimiento (m² por galón por mano)" ayuda="Obligatorio si consume pintura."><input type="number" min="0" step="0.01" value={form.rendimiento_m2} onChange={(e) => set("rendimiento_m2", e.target.value)} /></Campo>
            <label className="check"><input type="checkbox" checked={form.activo} onChange={(e) => set("activo", e.target.checked)} /> Activo (visible para clientes)</label>
          </div>
          <div className="acciones"><button className="btn">Guardar</button><button type="button" className="btn sec" onClick={() => setForm(null)}>Cancelar</button></div>
        </form>
      )}

      <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
        <thead><tr><th>Trabajo</th><th>Unidad</th><th className="der">Precio unitario</th><th className="der">Solo mano de obra</th><th>Material</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          {trabajos === null && <tr><td colSpan={7} className="vacio">Cargando…</td></tr>}
          {trabajos?.map((t) => (
            <tr key={t.id} style={t.activo ? null : { opacity: 0.55 }}>
              <td><strong>{t.nombre}</strong></td><td>{t.unidad === "M2" ? "m²" : "ml"}</td>
              <td className="der">{clp(t.precio_unitario)}</td><td className="der">{t.precio_mano_obra == null ? "—" : clp(t.precio_mano_obra)}</td>
              <td>{t.material_nombre || "—"}</td>
              <td>{t.activo ? <span className="badge aprobada">Activo</span> : <span className="badge rechazada">Inactivo</span>}</td>
              <td className="der"><button className="btn sec peq" onClick={() => editar(t)}>Editar</button> <button className="btn sec peq" onClick={() => alternar(t)}>{t.activo ? "Desactivar" : "Activar"}</button></td>
            </tr>
          ))}
        </tbody>
      </table></div></div>

      <h2 className="espacio">Últimos cambios de precios y nombres</h2>
      <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
        <thead><tr><th>Fecha</th><th>Usuario</th><th>Cambio</th></tr></thead>
        <tbody>
          {bitacora.length === 0 && <tr><td colSpan={3} className="vacio">Sin cambios registrados.</td></tr>}
          {bitacora.map((b) => <tr key={b.id}><td>{fechaHora(b.fecha)}</td><td>{b.usuario_nombre}</td><td>{b.detalle}</td></tr>)}
        </tbody>
      </table></div></div>
    </>
  );
}
