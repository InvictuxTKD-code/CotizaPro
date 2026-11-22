import { useEffect, useState } from "react";
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";
import { api, mensajesDeError } from "../api";
import { Errores } from "../components/ui.jsx";
import { useTema } from "../tema.jsx";
import { clp, fechaHora, num } from "../util.js";

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, LineElement, PointElement, Tooltip);

const PERIODOS = [[30, "30 días"], [90, "90 días"], [365, "12 meses"], [0, "Todo"]];

function paleta(oscuro) {
  return oscuro
    ? { texto: "#c3cedd", grilla: "#2a3a51", azul: "#5a9be0", dorado: "#e0b84f", verde: "#5cd196", rojo: "#ff8f87", ambar: "#f0c35c" }
    : { texto: "#4a5666", grilla: "#e3e8ef", azul: "#1f5fa8", dorado: "#b98a1e", verde: "#1d7a4d", rojo: "#b3261e", ambar: "#c58a00" };
}

function Kpi({ titulo, valor, sufijo = "", casos, meta, cumple, pendiente }) {
  return (
    <div className="kpi">
      <span>{titulo}</span>
      {pendiente ? <strong className="sin">Sin datos</strong> : <strong>{valor === null || valor === undefined ? "—" : `${valor}${sufijo}`}</strong>}
      {!pendiente && <small>{casos} caso{casos === 1 ? "" : "s"} medido{casos === 1 ? "" : "s"}</small>}
      <small className={`meta ${cumple === true ? "cumple" : cumple === false ? "no" : ""}`}>Meta: {meta}</small>
    </div>
  );
}

export default function Dashboard() {
  const { tema } = useTema();
  const c = paleta(tema === "dark");
  const [dias, setDias] = useState(90);
  const [d, setD] = useState(null);
  const [errores, setErrores] = useState([]);

  useEffect(() => {
    let vivo = true;
    api.get("/dashboard/", { params: { dias } }).then((r) => { if (vivo) { setD(r.data); setErrores([]); } }).catch((e) => vivo && setErrores(mensajesDeError(e)));
    return () => { vivo = false; };
  }, [dias]);

  const base = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: c.texto } }, tooltip: { callbacks: {} } },
    scales: { x: { ticks: { color: c.texto }, grid: { color: c.grilla } }, y: { ticks: { color: c.texto, precision: 0 }, grid: { color: c.grilla }, beginAtZero: true } },
  };
  const k = d?.kpi;
  const serie = d?.serie_mensual ?? [];
  const E = d?.resumen.por_estado;

  return (
    <>
      <div className="encabezado">
        <div><h1>Dashboard gerencial</h1><small>{d ? `Datos actualizados: ${fechaHora(d.generado)}` : "Cargando…"}</small></div>
        <div className="selector" role="group" aria-label="Periodo">
          {PERIODOS.map(([v, t]) => <button key={v} className={dias === v ? "on" : ""} onClick={() => setDias(v)}>{t}</button>)}
        </div>
      </div>
      <Errores lista={errores} />

      {d && (
        <>
          <div className="kpis">
            <div className="kpi"><span>Ventas aprobadas (neto)</span><strong>{clp(d.resumen.ventas_neto)}</strong><small>{d.resumen.aprobadas} {d.resumen.aprobadas === 1 ? "cotización aprobada" : "cotizaciones aprobadas"}{d.resumen.ticket_promedio ? ` · promedio ${clp(d.resumen.ticket_promedio)}` : ""}</small></div>
            <Kpi titulo="KPI-03 · Cotizaciones registradas" valor={k.registradas.valor} casos={k.registradas.casos} meta={k.registradas.meta} />
            <Kpi titulo="KPI-04 · Conversión a ventas" valor={k.conversion.valor} sufijo=" %" casos={k.conversion.casos} meta={k.conversion.meta} cumple={k.conversion.valor === null ? undefined : k.conversion.valor >= 60} />
            <Kpi titulo="KPI-01 · Tiempo de cotización" valor={k.tiempo_cotizacion_min.valor} sufijo=" min" casos={k.tiempo_cotizacion_min.casos} meta={k.tiempo_cotizacion_min.meta} cumple={k.tiempo_cotizacion_min.valor === null ? undefined : k.tiempo_cotizacion_min.valor <= 10} />
            <Kpi titulo="KPI-07 · Inventario automático" valor={k.inventario_automatico.valor} sufijo=" %" casos={k.inventario_automatico.casos} meta={k.inventario_automatico.meta} cumple={k.inventario_automatico.valor === null ? undefined : k.inventario_automatico.valor >= 100} />
            <Kpi titulo="KPI-05 · Consultas resueltas por chatbot" valor={k.chatbot.valor} sufijo=" %" casos={k.chatbot.casos} meta={k.chatbot.meta} cumple={k.chatbot.valor === null ? undefined : k.chatbot.valor >= 60} />
            <Kpi titulo="KPI-06 · Satisfacción del cliente" valor={k.satisfaccion.valor} sufijo=" %" casos={k.satisfaccion.casos} meta={k.satisfaccion.meta} cumple={k.satisfaccion.valor === null ? undefined : k.satisfaccion.valor >= 85} />
          </div>

          <div className="graficos">
            <div className="tarjeta">
              <h2>Solicitudes y ventas por mes</h2>
              <div className="caja-grafico">
                <Bar
                  data={{ labels: serie.map((s) => s.mes), datasets: [
                    { label: "Solicitudes", data: serie.map((s) => s.solicitudes), backgroundColor: c.azul, yAxisID: "y", borderRadius: 4 },
                    { label: "Aprobadas", data: serie.map((s) => s.aprobadas), backgroundColor: c.verde, yAxisID: "y", borderRadius: 4 },
                    { type: "line", label: "Ventas netas ($)", data: serie.map((s) => s.ventas), borderColor: c.dorado, backgroundColor: c.dorado, yAxisID: "y1", tension: 0 },
                  ] }}
                  options={{ ...base, scales: { ...base.scales, y1: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { color: c.texto, callback: (v) => clp(v) } } },
                    plugins: { ...base.plugins, tooltip: { callbacks: { label: (x) => (x.dataset.yAxisID === "y1" ? `Ventas: ${clp(x.parsed.y)}` : `${x.dataset.label}: ${x.parsed.y}`) } } } }}
                />
              </div>
            </div>
            <div className="tarjeta">
              <h2>Cotizaciones por estado</h2>
              <div className="caja-grafico">
                {d.resumen.solicitudes === 0 ? <p className="vacio">Sin cotizaciones en el periodo.</p> : (
                  <Doughnut
                    data={{ labels: ["Pendientes", "Aprobadas", "Rechazadas"], datasets: [{ data: [E.PENDIENTE, E.APROBADA, E.RECHAZADA], backgroundColor: [c.ambar, c.verde, c.rojo], borderColor: tema === "dark" ? "#162131" : "#fff", borderWidth: 2 }] }}
                    options={{ responsive: true, maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom", labels: { color: c.texto } } } }}
                  />
                )}
              </div>
            </div>
          </div>

          <div className="graficos">
            <div className="tarjeta">
              <h2>Trabajos más vendidos <small>(monto neto, cotizaciones aprobadas)</small></h2>
              <div className="caja-grafico">
                {d.top_trabajos.length === 0 ? <p className="vacio">Aún no hay ventas aprobadas en el periodo.</p> : (
                  <Bar
                    data={{ labels: d.top_trabajos.map((t) => t.trabajo), datasets: [{ label: "Monto neto", data: d.top_trabajos.map((t) => t.monto), backgroundColor: c.dorado, borderRadius: 4 }] }}
                    options={{ ...base, indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (x) => clp(x.parsed.x) } } },
                      scales: { x: { beginAtZero: true, ticks: { color: c.texto, callback: (v) => clp(v) }, grid: { color: c.grilla } }, y: { ticks: { color: c.texto }, grid: { display: false } } } }}
                  />
                )}
              </div>
            </div>
            <div className="tarjeta">
              <h2>Consumo de materiales <small>(por aprobaciones)</small></h2>
              <div className="caja-grafico">
                {d.inventario.consumo.length === 0 ? <p className="vacio">Sin salidas de inventario en el periodo.</p> : (
                  <Bar
                    data={{ labels: d.inventario.consumo.map((m) => m.material), datasets: [{ label: "Cantidad", data: d.inventario.consumo.map((m) => m.cantidad), backgroundColor: c.azul, borderRadius: 4 }] }}
                    options={{ ...base, indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { color: c.texto }, grid: { color: c.grilla } }, y: { ticks: { color: c.texto }, grid: { display: false } } } }}
                  />
                )}
              </div>
            </div>
          </div>

          <h2>Materiales que requieren reposición</h2>
          <div className="tarjeta sin-padding"><div className="tabla-wrap"><table>
            <thead><tr><th>Material</th><th className="der">Stock actual</th><th className="der">Mínimo</th></tr></thead>
            <tbody>
              {d.inventario.bajo_minimo.length === 0 && <tr><td colSpan={3} className="vacio">Todo el inventario está sobre el mínimo.</td></tr>}
              {d.inventario.bajo_minimo.map((m) => <tr key={m.id}><td><strong>{m.nombre}</strong></td><td className="der">{num(m.stock_actual)} {m.unidad}</td><td className="der">{num(m.stock_minimo)}</td></tr>)}
            </tbody>
          </table></div></div>
          <p className="nota" style={{ marginTop: ".8rem" }}>Con pocas solicitudes al mes los porcentajes deben leerse junto al número de casos medidos.</p>
        </>
      )}
    </>
  );
}
