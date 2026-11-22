import { ESTADOS } from '../util'

export const Estado = ({ valor }) => <span className={`estado ${valor}`}>{ESTADOS[valor] || valor}</span>

export const Aviso = ({ tipo = 'error', children }) =>
  children ? <div className={`aviso ${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>{children}</div> : null

export const Cargando = () => <p className="vacio" role="status">Cargando…</p>
