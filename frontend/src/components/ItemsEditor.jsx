import { clp } from "../util.js";

export const itemVacio = (acabados) => ({ tipo_acabado: acabados[0]?.id ?? "", descripcion: "", textura: "NORMAL", cantidad: "" });

/** Tabla editable de ítems a cotizar (cantidad en m² o ml según el ítem). */
export default function ItemsEditor({ items, setItems, acabados }) {
  const set = (i, k, v) => setItems(items.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  const unidadDe = (id) => acabados.find((a) => String(a.id) === String(id))?.unidad ?? "M2";

  return (
    <div className="items">
      {items.map((it, i) => (
        <div className="item" key={i}>
          <label className="campo grande"><span>Trabajo</span>
            <select value={it.tipo_acabado} onChange={(e) => set(i, "tipo_acabado", e.target.value)} required>
              {acabados.map((a) => <option key={a.id} value={a.id}>{a.nombre} ({a.unidad === "ML" ? "ml" : "m²"})</option>)}
            </select>
          </label>
          <label className="campo grande"><span>Descripción / ubicación</span><input value={it.descripcion} onChange={(e) => set(i, "descripcion", e.target.value)} placeholder="Ej: Muros pasillo piso 2" required /></label>
          <label className="campo"><span>Superficie</span>
            <select value={it.textura} onChange={(e) => set(i, "textura", e.target.value)}><option value="LISA">Lisa</option><option value="NORMAL">Normal</option><option value="RUGOSA">Rugosa</option></select>
          </label>
          <label className="campo"><span>Cantidad ({unidadDe(it.tipo_acabado) === "ML" ? "ml" : "m²"})</span>
            <input type="number" min="0.01" step="0.01" value={it.cantidad} onChange={(e) => set(i, "cantidad", e.target.value)} required />
          </label>
          <button type="button" className="btn sec peq quitar" onClick={() => setItems(items.filter((_, j) => j !== i))} disabled={items.length === 1} aria-label="Quitar ítem">✕</button>
        </div>
      ))}
      <button type="button" className="btn sec" onClick={() => setItems([...items, itemVacio(acabados)])}>+ Agregar ítem</button>
    </div>
  );
}
