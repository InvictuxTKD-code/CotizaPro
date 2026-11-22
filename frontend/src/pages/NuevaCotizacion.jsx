import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, mensajesDeError } from "../api";
import { Campo, Errores } from "../components/ui.jsx";
import ItemsEditor, { itemVacio } from "../components/ItemsEditor.jsx";

export default function NuevaCotizacion() {
  const nav = useNavigate();
  const [acabados, setAcabados] = useState([]);
  const [f, setF] = useState({ nombre_obra: "", direccion_obra: "", ciudad: "Valdivia", origen_materiales: "EMPRESA", requiere_medicion: false, num_pintores: "", semanas_obra: "", observaciones: "" });
  const [items, setItems] = useState([]);
  const [errores, setErrores] = useState([]);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api.get("/catalogo/acabados/").then(({ data }) => { setAcabados(data); setItems([itemVacio(data)]); }).catch((e) => setErrores(mensajesDeError(e)));
  }, []);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    setErrores([]);
    setEnviando(true);
    try {
      const cuerpo = {
        ...f,
        num_pintores: f.num_pintores === "" ? null : Number(f.num_pintores),
        semanas_obra: f.semanas_obra === "" ? null : Number(f.semanas_obra),
        detalles: f.requiere_medicion ? [] : items.map((i) => ({ ...i, tipo_acabado: Number(i.tipo_acabado) })),
      };
      const { data } = await api.post("/cotizaciones/", cuerpo);
      nav(`/cotizaciones/${data.id}`, { state: { avisos: data.avisos } });
    } catch (err) { setErrores(mensajesDeError(err)); window.scrollTo({ top: 0, behavior: "smooth" }); }
    finally { setEnviando(false); }
  };

  return (
    <form onSubmit={enviar}>
      <div className="encabezado"><h1>Solicitar cotización</h1></div>
      <Errores lista={errores} />

      <section className="tarjeta">
        <h2>1. Datos de la obra</h2>
        <div className="fila">
          <Campo etiqueta="Nombre de la obra"><input value={f.nombre_obra} onChange={set("nombre_obra")} required /></Campo>
          <Campo etiqueta="Ciudad"><input value={f.ciudad} onChange={set("ciudad")} required /></Campo>
        </div>
        <Campo etiqueta="Dirección de la obra"><input value={f.direccion_obra} onChange={set("direccion_obra")} required /></Campo>
      </section>

      <section className="tarjeta">
        <h2>2. ¿Quién pone los materiales?</h2>
        <div className="opciones">
          <label className={`opcion ${f.origen_materiales === "EMPRESA" ? "sel" : ""}`}>
            <input type="radio" name="origen" checked={f.origen_materiales === "EMPRESA"} onChange={() => setF({ ...f, origen_materiales: "EMPRESA" })} />
            <div><strong>M y C (obra vendida)</strong><small>El precio incluye materiales e insumos.</small></div>
          </label>
          <label className={`opcion ${f.origen_materiales === "CLIENTE" ? "sel" : ""}`}>
            <input type="radio" name="origen" checked={f.origen_materiales === "CLIENTE"} onChange={() => setF({ ...f, origen_materiales: "CLIENTE", num_pintores: "", semanas_obra: "" })} />
            <div><strong>Yo pongo los materiales</strong><small>Se cotiza solo la mano de obra.</small></div>
          </label>
        </div>
        {f.origen_materiales === "EMPRESA" && (
          <div className="fila">
            <Campo etiqueta="N° de pintores (opcional)" ayuda="Nos ayuda a estimar rodillos y brochas."><input type="number" min="0" value={f.num_pintores} onChange={set("num_pintores")} /></Campo>
            <Campo etiqueta="Semanas de obra (opcional)"><input type="number" min="1" value={f.semanas_obra} onChange={set("semanas_obra")} /></Campo>
          </div>
        )}
      </section>

      <section className="tarjeta">
        <h2>3. Trabajos a cotizar</h2>
        <label className="check"><input type="checkbox" checked={f.requiere_medicion} onChange={set("requiere_medicion")} /> No tengo las medidas: necesito que un supervisor mida en terreno</label>
        {!f.requiere_medicion && acabados.length > 0 && <ItemsEditor items={items} setItems={setItems} acabados={acabados} />}
        <Campo etiqueta="Observaciones (opcional)"><textarea rows={3} value={f.observaciones} onChange={set("observaciones")} /></Campo>
      </section>

      <div className="barra-accion"><button className="btn grande" disabled={enviando}>{enviando ? "Enviando…" : "Enviar solicitud"}</button></div>
    </form>
  );
}
