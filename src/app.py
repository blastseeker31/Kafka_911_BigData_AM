from __future__ import annotations

import time
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import settings
from src.event_factory import CITIES, EMERGENCY_TYPES, SCENARIOS, create_batch, create_event
from src.kafka_io import EmergencyProducer
from src.storage import EmergencyStorage

st.set_page_config(page_title="Central 911 Honduras", page_icon="🚨", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp { background:#f6f8fb; color:#172033; } [data-testid="stHeader"] { background:#f6f8fb; }
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp [data-testid="stMarkdownContainer"] { color:#172033 !important; }
[data-baseweb="select"] *, [data-baseweb="input"] *, textarea, input { color:#172033 !important; background:#fff !important; }
[data-testid="stSidebar"] { color:#172033 !important; } [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color:#172033 !important; }
.stButton button, [data-testid="stFormSubmitButton"] button { color:#172033 !important; background:#fff !important; border:1px solid #b8c2cf !important; }
[data-testid="stFormSubmitButton"] button[kind="primary"], .stButton button[kind="primary"] { background:#c92f3d !important; color:#fff !important; border-color:#c92f3d !important; }
[data-testid="stFormSubmitButton"] button[kind="primary"] *, .stButton button[kind="primary"] * { color:#fff !important; }
[data-testid="stDataFrame"] { border:1px solid #d8e0e8; border-radius:8px; background:#fff; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e5eaf0; }
[data-testid="stMetric"] { background:#fff; border:1px solid #e4e9ef; padding:14px 16px; border-radius:10px; }
div[data-testid="stForm"] { background:#fff; border:1px solid #e4e9ef; padding:18px; border-radius:10px; }
.hero { padding:0 0 8px; } .eyebrow { color:#d12f3d; font-size:.75rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
.priority-5 { color:#b42318; font-weight:800; } .priority-4 { color:#b54708; font-weight:800; }
.login-wrap { max-width:440px; margin:7vh auto 0; } .login-mark { color:#d12f3d; font-size:2rem; font-weight:900; }
.muted { color:#637083; } .section-title { margin-top:6px; margin-bottom:4px; }
.nav-caption { color:#637083; font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin:4px 0 0; }
.queue-count { color:#637083; font-size:.85rem; margin:0 0 8px; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def producer() -> EmergencyProducer:
    return EmergencyProducer()

@st.cache_resource
def storage() -> EmergencyStorage:
    return EmergencyStorage()

def initialize_state() -> None:
    for key, value in {"authenticated": False, "page": "queue", "selected_report": None, "queue_page": 1}.items():
        st.session_state.setdefault(key, value)

def login_page() -> None:
    st.markdown("<div class='login-wrap'><div class='login-mark'>● 911 HN</div><p class='eyebrow'>Centro de despacho nacional</p><h1>Ingresar a la central</h1><p class='muted'>Registra, prioriza y despacha emergencias desde un solo lugar.</p>", unsafe_allow_html=True)
    with st.form("login"):
        username = st.text_input("Usuario", placeholder="Usuario de operador")
        password = st.text_input("Contraseña", type="password", placeholder="Contraseña")
        submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
    if submitted:
        if username == settings.app_user and password == settings.app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Demo: Alejandro / 911.")
    st.markdown("</div>", unsafe_allow_html=True)

def render_header() -> None:
    left, right = st.columns([5, 1])
    with left:
        st.markdown("<p class='eyebrow'>Operación en tiempo real · Honduras</p><h1 class='hero'>Central de Emergencias 911</h1>", unsafe_allow_html=True)
    with right:
        st.caption(f"Operador: {settings.app_user}")
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

def metrics(db: EmergencyStorage) -> None:
    summary = db.summary()
    cols = st.columns(5)
    cols[0].metric("Reportes nuevos", f"{summary['new']:,}")
    cols[1].metric("Críticos activos", f"{summary['critical']:,}")
    cols[2].metric("Unidades disponibles", f"{summary['units']:,}")
    cols[3].metric("Unidades ocupadas", f"{summary['occupied']:,}")
    cols[4].metric("Procesados", f"{summary['processed']:,}")

def emergency_form() -> None:
    st.markdown("<p class='eyebrow'>Acción rápida</p><h2 class='section-title'>Registrar emergencia</h2><p class='muted'>Los campos esenciales están aquí. Kafka procesa el reporte automáticamente.</p>", unsafe_allow_html=True)
    city_names = {c["name"]: c["id"] for c in CITIES}
    types = [x[0] for x in EMERGENCY_TYPES]
    with st.form("new-report", clear_on_submit=True):
        c1, c2 = st.columns(2)
        city = c1.selectbox("Ciudad", list(city_names))
        emergency_type = c2.selectbox("Tipo", types)
        neighborhood = st.text_input("Colonia o referencia", placeholder="Ej. Kennedy, frente al hospital")
        location = st.text_input("Ubicación exacta", placeholder="Calle, avenida, edificio o punto de referencia")
        p1, p2 = st.columns([1, 1.7])
        priority = p1.select_slider("Prioridad", options=[1, 2, 3, 4, 5], value=3, format_func=lambda x: {1:"1 · Baja",2:"2 · Moderada",3:"3 · Alta",4:"4 · Muy alta",5:"5 · Crítica"}[x])
        people = p2.number_input("Personas en riesgo", min_value=1, max_value=999, value=1, step=1)
        description = st.text_area("Descripción breve", placeholder="Qué ocurre, riesgos visibles y qué necesita el operador", height=86)
        submitted = st.form_submit_button("Registrar y poner en cola", use_container_width=True, type="primary")
    if submitted:
        if not neighborhood.strip() or not location.strip() or not description.strip():
            st.error("Completa colonia o referencia, ubicación y descripción.")
            return
        event = create_event(city_id=city_names[city], neighborhood=neighborhood.strip(), emergency_type=emergency_type, priority=priority, location=location.strip(), description=description.strip(), people_at_risk=int(people))
        try:
            result = producer().publish_many([event])
            if result["delivered"] == 1: st.success(f"{event['report_number']} registrado. Ya está en la cola.")
            else: st.error("No se confirmó el registro.")
        except Exception as exc: st.error(f"No se pudo registrar la emergencia: {exc}")

def queue(db: EmergencyStorage) -> None:
    st.markdown("<p class='eyebrow'>Despacho</p><h2 class='section-title'>Cola de reportes</h2><p class='muted'>Encuentra el siguiente reporte que necesita acción y abre su despacho en un clic.</p>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    search = f1.text_input("Buscar", placeholder="Número, ubicación o descripción")
    city = f2.selectbox("Ciudad", ["Todas"] + [c["name"] for c in CITIES])
    typ = f3.selectbox("Tipo", ["Todos"] + [x[0] for x in EMERGENCY_TYPES])
    status = f4.selectbox("Estado", ["Todos", "Nuevo", "Despachado", "En atención", "Cerrado"])
    g1, g2, g3 = st.columns([1, 1, 2])
    priority = g1.selectbox("Prioridad", ["Todas", "5", "4", "3", "2", "1"])
    sort = g2.selectbox("Ordenar", ["Más recientes", "Prioridad"])
    page_size = g3.selectbox("Reportes por página", [25, 50, 100])
    total_pages = max(1, (db.query_events(1, 1, search, city, typ, priority, status, sort)[1] + page_size - 1) // page_size)
    st.session_state.queue_page = min(st.session_state.queue_page, total_pages)
    events, total = db.query_events(st.session_state.queue_page, page_size, search, city, typ, priority, status, sort)
    if events:
        st.markdown(f"<p class='queue-count'>{total:,} reportes encontrados · página {st.session_state.queue_page} de {total_pages}</p>", unsafe_allow_html=True)
        options = {f"{e['report_number']} · P{e['priority']} · {e['city_name']} · {e['emergency_type']}": e["report_number"] for e in events}
        selected = st.selectbox("Reporte seleccionado", list(options), label_visibility="collapsed")
        if st.button("Abrir expediente y despachar", type="primary", use_container_width=True):
            st.session_state.selected_report = options[selected]
            st.session_state.page = "detail"
            st.rerun()
        frame = pd.DataFrame([{"Reporte": e["report_number"], "Ciudad": e["city_name"], "Colonia / referencia": e["neighborhood"], "Tipo": e["emergency_type"], "Prioridad": f"P{e['priority']}", "Riesgo": e["people_at_risk"], "Estado": e["status"]} for e in events])
        st.dataframe(frame, use_container_width=True, hide_index=True)
    else:
        st.info("No hay reportes con estos filtros. Prueba quitar un filtro o registra una nueva emergencia.")
    a, b, c = st.columns([1, 1, 1])
    if c.button("Siguiente ›", disabled=st.session_state.queue_page >= total_pages, use_container_width=True):
        st.session_state.queue_page += 1
        st.rerun()
    if a.button("‹ Anterior", disabled=st.session_state.queue_page <= 1, use_container_width=True):
        st.session_state.queue_page -= 1
        st.rerun()
    b.button(f"Página {st.session_state.queue_page} de {total_pages}", disabled=True, use_container_width=True)

def units_for_city(city_id: str) -> list[str]:
    city = next(c for c in CITIES if c["id"] == city_id)
    return [f"{kind} {city['id']}-{n:02d}" for kind, amount in city["units"].items() for n in range(1, min(amount, 8) + 1)]

def detail(db: EmergencyStorage) -> None:
    event = db.get_event(st.session_state.selected_report)
    if not event:
        st.error("El reporte ya no existe.")
        return
    if st.button("‹ Volver a la cola"):
        st.session_state.page = "queue"
        st.rerun()
    st.markdown(f"<p class='eyebrow'>Expediente operativo · {event['report_number']}</p><h1>{event['emergency_type']} <span class='priority-{event['priority']}'>P{event['priority']}</span></h1>", unsafe_allow_html=True)
    left, right = st.columns([1.1, .9], gap="large")
    with left:
        st.subheader("Información del reporte")
        st.info(f"**{event['city_name']} · {event['neighborhood']}**\n\n{event['location']}\n\n{event['description']}\n\nPersonas en riesgo: **{event['people_at_risk']}**")
        st.caption(f"Recibido: {event['occurred_at']} · Operador: {event.get('operator', settings.app_user)}")
        st.subheader("Historial de estados")
        st.write(" → ".join([f"✅ {s}" if s == event["status"] else s for s in ["Nuevo", "Despachado", "En atención", "Cerrado"]]))
    with right:
        st.subheader("Despachar recursos")
        statuses = ["Nuevo", "Despachado", "En atención", "Cerrado"]
        current = event.get("status", "Nuevo")
        city_units = units_for_city(event["city_id"])
        with st.form("dispatch"):
            status = st.selectbox("Estado", statuses, index=statuses.index(current) if current in statuses else 0)
            assigned = st.multiselect("Unidades (puedes elegir varias)", city_units, default=[u for u in event.get("assigned_units", []) if u in city_units])
            observation = st.text_area("Nota de despacho", value=event.get("observation", ""), height=100)
            submitted = st.form_submit_button("Guardar despacho", use_container_width=True, type="primary")
        if submitted:
            db.update_event(event["report_number"], status, assigned, observation)
            st.success("Despacho actualizado.")
            time.sleep(.3)
            st.rerun()

def massive(db: EmergencyStorage) -> None:
    st.markdown("<p class='eyebrow'>Simulación</p><h2 class='section-title'>Generador de reportes</h2><p class='muted'>Prueba cómo responde la central durante un pico sin tocar el flujo de atención manual.</p>", unsafe_allow_html=True)
    st.info("El generador publica reportes a Kafka; el consumidor los valida, deduplica y los incorpora a la cola.")
    st.markdown("#### Configuración del pico")
    with st.form("batch"):
        c1, c2, c3 = st.columns([1.2, 1, 1])
        scenario = c1.selectbox("Escenario operativo", list(SCENARIOS))
        count = c2.number_input("Cantidad de reportes", min_value=10, max_value=50000, value=1500, step=100)
        imperfection = c3.slider("Imperfecciones", 0.0, 10.0, 2.0, .5, format="%.1f%%")
        submitted = st.form_submit_button("Generar lote", type="primary")
    if submitted:
        try:
            result = producer().publish_many(create_batch(int(count), imperfection / 100, scenario))
            st.success(f"{result['delivered']:,} reportes enviados correctamente.")
            a, b, c = st.columns(3)
            a.metric("Enviados", f"{result['delivered']:,}")
            b.metric("Velocidad", f"{result['events_per_second']:,.0f}/s")
            c.metric("Errores", f"{result['errors']:,}")
            with st.expander("Ver detalles técnicos"):
                st.json(result)
        except Exception as exc: st.error(str(exc))
    st.divider()
    st.markdown("#### Preparar una nueva demostración")
    st.caption("Elimina los reportes, métricas y dead letters generados en MongoDB. No modifica Kafka ni la configuración del sistema.")
    confirm_reset = st.checkbox("Confirmo que quiero borrar los datos de prueba")
    if st.button("Eliminar datos de prueba", disabled=not confirm_reset):
        db.reset_demo_data()
        st.success("Datos de prueba eliminados. La central está lista para un nuevo runthrough.")
        time.sleep(.5)
        st.rerun()

def overview(db: EmergencyStorage) -> None:
    st.markdown("<p class='eyebrow'>Situación nacional</p><h2 class='section-title'>Resumen por ciudad</h2><p class='muted'>Compara demanda, disponibilidad y presión operativa de las tres ciudades atendidas.</p>", unsafe_allow_html=True)
    rows = db.city_rows()
    if not rows:
        st.info("Todavía no hay métricas de ciudad.")
        return
    frame = pd.DataFrame(rows)
    a, b, c = st.columns(3)
    a.metric("Ciudad con más reportes nuevos", frame.loc[frame["Nuevos"].idxmax(), "Ciudad"])
    b.metric("Reportes nuevos", f"{int(frame['Nuevos'].sum()):,}")
    c.metric("Unidades disponibles", f"{int(frame['Disponibles'].sum()):,}")
    chart = px.bar(frame, x="Ciudad", y=["Nuevos", "Activos"], barmode="group", labels={"value":"Reportes", "variable":"Indicador", "Ciudad":""}, color_discrete_map={"Nuevos":"#c92f3d", "Activos":"#315a8a"})
    chart.update_layout(height=340, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff", font_color="#172033", legend_title_text="")
    st.plotly_chart(chart, use_container_width=True)
    pressure = px.bar(frame, x="Ciudad", y=["Disponibles", "Ocupadas"], barmode="group", labels={"value":"Unidades", "variable":"Indicador", "Ciudad":""}, color_discrete_map={"Disponibles":"#2f855a", "Ocupadas":"#b54708"})
    pressure.update_layout(height=320, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff", font_color="#172033", legend_title_text="")
    st.plotly_chart(pressure, use_container_width=True)
    st.dataframe(frame, use_container_width=True, hide_index=True)

def main() -> None:
    initialize_state()
    if not st.session_state.authenticated:
        login_page()
        return
    try:
        db = storage()
        db.ping()
    except Exception as exc:
        st.error(f"MongoDB no está disponible: {exc}")
        st.stop()
    render_header()
    metrics(db)
    st.markdown("<p class='nav-caption'>Vistas de operación</p>", unsafe_allow_html=True)
    choice = st.radio("Navegación", ["Cola de reportes", "Resumen por ciudad", "Generación masiva"], horizontal=True, label_visibility="collapsed")
    if st.session_state.page == "detail":
        detail(db)
    elif choice == "Cola de reportes":
        form_col, queue_col = st.columns([.8, 1.5], gap="large")
        with form_col: emergency_form()
        with queue_col: queue(db)
    elif choice == "Resumen por ciudad": overview(db)
    else: massive(db)

if __name__ == "__main__": main()
