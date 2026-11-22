import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, descargarPdf, mensajesDeError } from "../api";
import { useAuth } from "../auth.jsx";
import { Errores, Estado } from "../components/ui.jsx";
import { clp, cod, fecha } from "../util.js";

export default function Cotizaciones() {
  const { esStaff } = useAuth();
  const [filtros, setFiltros] = useState({ cliente: "", estado: "", desde: "", hasta: "" });
  const [datos, setDatos] = useState(null);
  const [errores, setErrores] = useState([]);

  const cargar = async (f = filtros) => {
    setErrores([]);
    try {
      const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
      setDatos((await api.get("/cotizaciones/", { params })).data);
    } catch (e) { setErrores(mensajesDeError(e)); }
  };
  useEffect(() => { cargar(); /* eslint-disable-next-line */ }, []);

  const set = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const limpiar = () => { const v = { cliente: "", estado: "", desde: "", hasta: "" }; setFiltros(v); cargar(v); };

  return (
    <>
      <div className="encabezado">
        <h1>{esStaff ? "Cotizaciones" : "Mis cotizaciones"}</h1>
        {!esStaff && <Link className="btn" to="/nueva">+ Nueva cotización</Link>}
      </div>

      <form className="tarjeta filtros" onSubmit={(e) => { e.preventDefault(); cargar(); }}>
        {esStaff && <label className="campo"><span>Cliente o RUT</span><input value={filtros.cliente} onChange={set("cliente")} placeholder="Buscar…" /></label>}
        <label className="campo"><span>Estado</span>
          <select value={filtros.estado} onChange={set("estado")}><option value="">Todos</option><option value="PENDIENTE">Pendiente</option><option value="APROBADA">Aprobada</option><option value="RECHAZADA">Rechazada</option></select>
        </label>
        <label className="campo"><span>Desde</span><input type="date" value={filtros.desde} onChange={set("desde")} /></label>
        <label className="campo"><span>Hasta</span><input type="date" value={filtros.hasta} onChange={set("hasta")} /></label>
        <div className="acciones"><button className="btn">Filtrar</button><button type="button" className="btn sec" onClick={limpiar}>Limpiar</button></div>
      </form>

      <Errores lista={errores} />
      <div className="tarjeta sin-padding">
        <div className="tabla-wrap">
          <table>
            <thead><tr><th>N°</th><th>Fecha</th>{esStaff && <th>Cliente</th>}<th>Obra</th><th>Alcance</th><th className="der">Total neto</th><th>Estado</th><th>PDF</th></tr></thead>
            <tbody>
              {datos === null && <tr><td colSpan={8} className="vacio">Cargando…</td></tr>}
              {datos?.length === 0 && <tr><td colSpan={8} className="vacio">No hay cotizaciones con esos filtros.</td></tr>}
              {datos?.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/cotizaciones/${c.id}`}><strong>{cod(c.id)}</strong></Link></td>
                  <td>{fecha(c.fecha_solicitud)}</td>
                  {esStaff && <td>{c.cliente_nombre}</td>}
                  <td>{c.nombre_obra}<small className="sub">{c.ciudad}</small></td>
                  <td>{c.origen_materiales === "EMPRESA" ? "Obra vendida" : "Solo mano de obra"}</td>
                  <td className="der">{c.calculada ? clp(c.total) : <em className="suave">{c.requiere_medicion ? "Falta medir" : "Sin calcular"}</em>}</td>
                  <td><Estado valor={c.estado} /></td>
                  <td>{c.calculada
                    ? <button className="btn sec peq" onClick={() => descargarPdf(c.id).catch((e) => setErrores(mensajesDeError(e)))}>⬇ PDF</button>
                    : <span className="suave" title="Disponible cuando el presupuesto esté calculado">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
