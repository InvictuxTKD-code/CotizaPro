import { createContext, useContext, useEffect, useState } from "react";

const Ctx = createContext({ tema: "light", alternar: () => {} });

function inicial() {
  try {
    const g = localStorage.getItem("cotizapro_tema");
    if (g === "dark" || g === "light") return g;
  } catch { /* sin almacenamiento */ }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function TemaProvider({ children }) {
  const [tema, setTema] = useState(inicial);
  useEffect(() => {
    document.documentElement.dataset.tema = tema;
    try { localStorage.setItem("cotizapro_tema", tema); } catch { /* ignorar */ }
  }, [tema]);
  return <Ctx.Provider value={{ tema, alternar: () => setTema((t) => (t === "dark" ? "light" : "dark")) }}>{children}</Ctx.Provider>;
}

export const useTema = () => useContext(Ctx);

export function BotonTema({ flotante = false }) {
  const { tema, alternar } = useTema();
  const oscuro = tema === "dark";
  return (
    <button type="button" className={`btn-tema${flotante ? " flotante" : ""}`} onClick={alternar} aria-pressed={oscuro} title={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}>
      {oscuro ? "☀ Modo claro" : "☾ Modo oscuro"}
    </button>
  );
}
