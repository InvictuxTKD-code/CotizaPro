import { useCallback, useEffect, useState } from "react";
import { api, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import { Campo, Errores } from "../components/ui.jsx";
import { clp, fechaHora, num } from "../util.js";

const vacio = { nombre: "", categoria: "", unidad: "unidad", precio_unitario: "", stock_minimo: "0" };

export default function Inventario() {
  const { esAdmin } = useAuth();
  const [materiales, setMateriales] = useState(null);
  const [movs, setMovs] = useState([]);
  const [soloBajo, setSoloBajo] = useState(false);
  const [errores, setErrores] = useState([]);
  const [ok, setOk] = useState("");
  const [nuevo, setNuevo] = useState(null);
  const [edit, setEdit] = useState(null);
  const [mov, setMov] = useState(null); // {material, tipo, cantidad, observacion}

  const cargar = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([api.get("/materiales/", { params: soloBajo ? { bajo_minimo: 1 } : {} }), api.get("/movimientos/")]);
      setMateriales(m.data); setMovs(h.data.slice(0, 15));
    } catch (e) { setErrores(mensajesDeError(e)); }
  }, [soloBajo]);
  useEffect(() => { cargar(); }, [cargar]);

  const accion = async (fn, mensaje) => {
    setErrores([]); setOk("");
    try { await fn(); setOk(mensaje); await cargar(); return true; }
    catch (e) { setErrores(mensajesDeError(e)); return false; }
  };

  const crear = async (e) => {
    e.preventDefault();
    if (await accion(() => api.post("/materiales/", nuevo), "Material creado. Registra una entrada para cargar su stock.")) setNuevo(null);
  };
  const guardarEdicion = async (e) => {
    e.preventDefault();
    const { id, nombre, categoria, unidad, precio_unitario, stock_minimo } = edit;
    if (await accion(() => api.patch(`/materiales/${id}/`, { nombre, categoria, unidad, precio_unitario, stock_minimo }), "Material actualizado. Las cotizaciones aprobadas no cambian.")) setEdit(null);
  };
  const registrarMov = async (e) => {
    e.preventDefault();
    if (await accion(() => api.post(`/materiales/${mov.material.id}/movimientos/`, { tipo: mov.tipo, cantidad: mov.cantidad, observacion: mov.observacion }), "Movimiento registrado.")) setMov(null);
  };

  return (
    <>
      <div className="encabezado">
        <h1>Inventario</h1>
        {esAdmin && <button className="btn" onClick={() => setNuevo({ ...vacio })}>+ Nuevo material</button>}
      </div>
      <Errores lista={errores} />
      {ok && <div className="alerta ok">{ok}</div>}

      {nuevo && (
        <form className="tarjeta" onSubmit={crear}>
          <h2>Nuevo material</h2>
          <div className="fila">
            <Campo etiqueta="Nombre"><input value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required /></Campo>
            <Campo etiqueta="Categoría" ayuda="Pintura, Rodillo, Brocha, Cinta…"><input value={nuevo.categoria} onChange={(e) => setNuevo({ ...nuevo, categoria: e.target.value })} required /></Campo>
          </div>
          <div className="fila tres">
            <Campo etiqueta="Unidad"><input value={nuevo.unidad} onChange={(e) => setNuevo({ ...nuevo, unidad: e.target.value })} required /></Campo>
            <Campo etiqueta="Precio unitario neto ($)"><input type="number" min="0" value={nuevo.precio_unitario} onChange={(e) => setNuevo({ ...nuevo, precio_unitario: e.target.value })} required /></Campo>
            <Campo etiqueta="Stock mínimo"><input type="number" min="0" step="0.01" value={nuevo.stock_minimo} onChange={(e) => setNuevo({ ...nuevo, stock_minimo: e.target.value })} required /></Campo>
          </div>
          <div className="acciones"><button className="btn">Crear</button><button type="button" className="btn sec" onClick={() => setNuevo(null)}>Cancelar</button></div>
        </form>
      )}

      {edit && (
        <form className="tarjeta" onSubmit={guardarEdicion}>
          <h2>Editar material</h2>
          <div className="fila">
            <Campo etiqueta="Nombre"><input value={edit.nombre} onChange={(e) => setEdit({ ...edit, nombre: e.target.value })} required /></Campo>
            <Campo etiqueta="Categoría"><input value={edit.categoria} onChange={(e) => setEdit({ ...edit, categoria: e.target.value })} required /></Campo>
          </div>
          <div className="fila tres">
            <Campo etiqueta="Unidad"><input value={edit.unidad} onChange={(e) => setEdit({ ...edit, unidad: e.target.value })} required /></Campo>
            <Campo etiqueta="Precio unitario neto ($)"><input type="number" min="0" value={edit.precio_unitario} onChange={(e) => setEdit({ ...edit, precio_unitario: e.target.value })} required /></Campo>
            <Campo etiqueta="Stock mínimo"><input type="number" min="0" step="0.01" value={edit.stock_minimo} onChange={(e) => setEdit({ ...edit, stock_minimo: e.target.value })} required /></Campo>
          </div>
          <div className="acciones"><button className="btn">Guardar</button><button type="button" className="btn sec" onClick={() => setEdit(null)}>Cancelar</button></div>
        </form>
      )}

      {mov && (
        <form className="tarjeta" onSubmit={registrarMov}>
          <h2>Movimiento de stock: {mov.material.nombre} <small>(actual: {num(mov.material.stock_actual)} {mov.material.unidad})</small></h2>
          <div className="fila tres">
            <Campo etiqueta="Tipo"><select value={mov.tipo} onChange={(e) => setMov({ ...mov, tipo: e.target.value })}><option value="ENTRADA">Entrada (compra / reposición)</option><option value="SALIDA">Salida manual</option><option value="AJUSTE">Ajuste (+ o −)</option></select></Campo>
            <Campo etiqueta="Cantidad" ayuda={mov.tipo === "AJUSTE" ? "Usa negativo para restar." : ""}><input type="number" step="0.01" value={mov.cantidad} onChange={(e) => setMov({ ...mov, cantidad: e.target.value })} required /></Campo>
            <Campo etiqueta="Observación"><input value={mov.observacion} onChange={(e) => setMov({ ...mov, observacion: e.target.value })} /></Campo>
          </div>
          <div className="acciones"><button className="btn">Registrar</button><button type="button" className="btn sec" onClick={() => setMov(null)}>Cancelar</button></div>
        </form>
      )}

      <label className="check"><input type="checkbox" checked={soloBajo} onChange={(e) => setSoloBajo(e.target.checked)} /> Mostrar solo materiales bajo el mínimo (reposición)</label>
      <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
        <thead><tr><th>Material</th><th>Categoría</th><th className="der">Precio</th><th className="der">Stock</th><th className="der">Mínimo</th><th>Estado</th>{esAdmin && <th></th>}</tr></thead>
        <tbody>
          {materiales === null && <tr><td colSpan={7} className="vacio">Cargando…</td></tr>}
          {materiales?.length === 0 && <tr><td colSpan={7} className="vacio">Sin materiales.</td></tr>}
          {materiales?.map((m) => (
            <tr key={m.id}>
              <td><strong>{m.nombre}</strong></td><td>{m.categoria}</td><td className="der">{clp(m.precio_unitario)} / {m.unidad}</td>
              <td className="der"><strong>{num(m.stock_actual)}</strong> {m.unidad}</td><td className="der">{num(m.stock_minimo)}</td>
              <td>{m.bajo_minimo ? <span className="badge rechazada">Reponer</span> : <span className="badge aprobada">OK</span>}</td>
              {esAdmin && <td className="der"><button className="btn sec peq" onClick={() => setEdit({ ...m })}>Editar</button> <button className="btn sec peq" onClick={() => setMov({ material: m, tipo: "ENTRADA", cantidad: "", observacion: "" })}>Mover stock</button></td>}
            </tr>
          ))}
        </tbody>
      </table></div></div>

      <h2 className="espacio">Últimos movimientos</h2>
      <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
        <thead><tr><th>Fecha</th><th>Material</th><th>Tipo</th><th className="der">Cantidad</th><th className="der">Stock resultante</th><th>Usuario</th><th>Origen</th></tr></thead>
        <tbody>
          {movs.length === 0 && <tr><td colSpan={7} className="vacio">Sin movimientos todavía.</td></tr>}
          {movs.map((h) => (
            <tr key={h.id}><td>{fechaHora(h.fecha)}</td><td>{h.material_nombre}</td><td>{h.tipo}</td><td className="der">{num(h.cantidad)}</td><td className="der">{num(h.stock_resultante)}</td><td>{h.usuario_nombre}</td><td>{h.cotizacion ? `Cotización #${h.cotizacion}` : h.observacion || "—"}</td></tr>
          ))}
        </tbody>
      </table></div></div>
    </>
  );
}
