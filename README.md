# CotizaPro

Aplicación web para automatizar cotizaciones e inventario de M y C Revestimientos y Pinturas SpA (proyecto de título INACAP).

**Stack (según informe):** React + Axios + Chart.js · Django + DRF + Simple JWT + ReportLab · PostgreSQL · Docker Compose + Nginx + Gunicorn · LLM por API.

## Arranque rápido (sin Docker, SQLite)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
pytest
```
## Frontend (desarrollo)
Requiere Node.js 20+. En otra terminal, con el backend corriendo en el puerto 8000:
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (redirige /api al backend)
```
## Con Docker (PostgreSQL)
```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python manage.py cargar_demo
# App en http://localhost:8080 · API en /api/ · admin en /admin/
```
Cuentas demo (clave `Demo12345!`): `admin@cotizapro.cl`, `supervisor@cotizapro.cl`, `cliente@cotizapro.cl`.

## Avance
- [x] Paso 1 — Base del backend, modelos, autenticación por roles (HU01)
- [x] Paso 2 — Motor de cálculo y cotizaciones (HU02, HU03, HU06)
- [x] Paso 3 — Inventario y aprobación (HU04) + PDF (HU08)
- [x] Paso 4 — Frontend React
- [ ] Paso 5 — Chatbot (HU05) y dashboard (HU07)

## Reglas de cálculo (validadas con Don Manuel)
- Precio unitario del ítem = **obra vendida** (incluye materiales e insumos). Total = cantidad × precio, igual que el Excel.
- Si el cliente pone los materiales se usa el precio de **solo mano de obra** del ítem (`precio_mano_obra`; cargar los reales en /admin).
- Galones = ceil(m² ÷ (34 ÷ 2 manos)); rodillo y brocha: 1 por pintor cada 2 semanas. Solo descuentan inventario y estiman el costo interno.
- Valores **netos**: el IVA no se agrega (activar con `IVA_PORCENTAJE=19` en `.env`).


## Asistente virtual (HU05)
- Funciona **sin clave** con respuestas predefinidas. Para activar Claude: en `.env` poner `ANTHROPIC_API_KEY=...` (`CHAT_PROVEEDOR=claude`). Para otro proveedor se agrega una clase en `apps/chat/proveedores.py`.
- Django rechaza pedir/calcular precios *antes* de consultar al modelo, anonimiza RUT/correo/teléfono y descarta respuestas del modelo que traigan montos de dinero.
- Consultas derivadas: pestaña **Consultas** (personal). KPI-05 y KPI-06 se ven en el Dashboard.
- Usuarios: el administrador puede **desactivar** o **eliminar** (solo sin historial; con historial se desactiva).
