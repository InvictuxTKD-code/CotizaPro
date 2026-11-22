import axios from "axios";

// Tokens en sessionStorage: al cerrar la pestaña se cierra la sesión.
const guardar = (k, v) => { try { v == null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* sin storage */ } };
const leer = (k) => { try { return sessionStorage.getItem(k); } catch { return null; } };

export const tokens = {
  get access() { return leer("access"); },
  get refresh() { return leer("refresh"); },
  set(access, refresh) { guardar("access", access); if (refresh) guardar("refresh", refresh); },
  clear() { guardar("access", null); guardar("refresh", null); guardar("usuario", null); },
};

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((cfg) => {
  if (tokens.access) cfg.headers.Authorization = `Bearer ${tokens.access}`;
  return cfg;
});

let alExpirar = () => {};
export const onSesionExpirada = (fn) => { alExpirar = fn; };

let refrescando = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const original = err.config;
    const esAuth = original?.url?.startsWith("/auth/");
    if (err.response?.status === 401 && !original._reintento && !esAuth && tokens.refresh) {
      original._reintento = true;
      try {
        refrescando ??= axios.post("/api/auth/refresh/", { refresh: tokens.refresh }).finally(() => { refrescando = null; });
        const { data } = await refrescando;
        tokens.set(data.access, data.refresh);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        alExpirar();
      }
    } else if (err.response?.status === 401 && !esAuth) {
      alExpirar();
    }
    return Promise.reject(err);
  }
);

/** Convierte cualquier error de DRF en una lista de mensajes legibles. */
export function mensajesDeError(err) {
  const d = err?.response?.data;
  if (!d) return ["No se pudo conectar con el servidor."];
  if (typeof d === "string") return [d];
  const out = [];
  if (d.detalle) out.push(d.detalle);
  if (d.detail) out.push(d.detail);
  if (Array.isArray(d.faltantes)) {
    d.faltantes.forEach((f) => out.push(typeof f === "string" ? f : `${f.material}: se requieren ${f.requerido}, hay ${f.disponible}`));
  }
  const resto = (v, prefijo = "") => {
    if (Array.isArray(v)) v.forEach((x) => (typeof x === "object" ? resto(x, prefijo) : out.push(prefijo ? `${prefijo}: ${x}` : x)));
    else if (v && typeof v === "object") Object.entries(v).forEach(([k, x]) => resto(x, k.replace(/_/g, " ")));
    else if (v) out.push(prefijo ? `${prefijo}: ${v}` : String(v));
  };
  Object.entries(d).forEach(([k, v]) => { if (!["detalle", "detail", "faltantes"].includes(k)) resto(v, k.replace(/_/g, " ")); });
  return out.length ? out : ["Ocurrió un error inesperado."];
}

export async function descargarPdf(id) {
  const r = await api.get(`/cotizaciones/${id}/pdf/`, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `presupuesto-COD-${String(id).padStart(3, "0")}.pdf`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
