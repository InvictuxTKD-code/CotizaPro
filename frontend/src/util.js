export const clp = (n) => (n == null ? "—" : "$" + Math.round(Number(n)).toLocaleString("es-CL"));
export const num = (n, d = 2) => (n == null ? "—" : Number(n).toLocaleString("es-CL", { maximumFractionDigits: d }));
export const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—");
export const fechaHora = (iso) => (iso ? new Date(iso).toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" }) : "—");
export const cod = (id) => `COD-${String(id).padStart(3, "0")}`;
export const ROL = { CLIENTE: "Cliente", EJECUTIVO: "Supervisor", ADMINISTRADOR: "Administrador" };
