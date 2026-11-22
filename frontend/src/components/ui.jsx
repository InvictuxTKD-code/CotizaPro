export function Estado({ valor }) {
  const t = { PENDIENTE: "Pendiente", APROBADA: "Aprobada", RECHAZADA: "Rechazada" }[valor] ?? valor;
  return <span className={`badge ${String(valor).toLowerCase()}`}>{t}</span>;
}

export function Errores({ lista }) {
  if (!lista?.length) return null;
  return <div className="alerta error" role="alert"><ul>{lista.map((m, i) => <li key={i}>{m}</li>)}</ul></div>;
}

export function Aviso({ lista, tipo = "info" }) {
  if (!lista?.length) return null;
  return <div className={`alerta ${tipo}`}><ul>{lista.map((m, i) => <li key={i}>{m}</li>)}</ul></div>;
}

export function Campo({ etiqueta, children, ayuda }) {
  return <label className="campo"><span>{etiqueta}</span>{children}{ayuda && <small>{ayuda}</small>}</label>;
}
