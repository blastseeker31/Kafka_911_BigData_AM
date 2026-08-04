from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import settings
from src.event_factory import DISTRICTS, EMERGENCY_TYPES, SCENARIOS, create_batch, create_event
from src.kafka_io import EmergencyProducer
from src.storage import EmergencyStorage


st.set_page_config(page_title="Central 911", page_icon="🚨", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background: #07111f; color: #eef4fb; }
      [data-testid="stHeader"] { background: rgba(7,17,31,.78); }
      [data-testid="stMetric"] { background:#101e30; border:1px solid #263c55; padding:18px; border-radius:14px; }
      div[data-testid="stForm"] { background:#0d1928; border:1px solid #263c55; padding:20px; border-radius:16px; }
      .hero { padding: 4px 0 18px; }
      .hero h1 { margin:0; letter-spacing:-.04em; }
      .eyebrow { color:#ef4444; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
      .status-pill { display:inline-block; padding:6px 11px; border-radius:999px; background:#123252; color:#a9d4ff; }
      .detail-card { background:#0d1928; border:1px solid #263c55; padding:18px; border-radius:14px; margin-bottom:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def producer() -> EmergencyProducer:
    return EmergencyProducer()


@st.cache_resource
def storage() -> EmergencyStorage:
    return EmergencyStorage()


def initialize_state() -> None:
    defaults = {"authenticated": False, "page": "dashboard", "selected_report": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def login_page() -> None:
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown("<div style='height:11vh'></div>", unsafe_allow_html=True)
        st.markdown("<p class='eyebrow'>Central de operaciones</p>", unsafe_allow_html=True)
        st.title("911 · Sirviendo al pueblo")
        st.caption("Plataforma de gestión y monitoreo de emergencias en tiempo real")
        with st.form("login"):
            username = st.text_input("Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")
            submitted = st.form_submit_button("Ingresar al centro de control", use_container_width=True)
        if submitted:
            if username == settings.app_user and password == settings.app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Para la demo use Alejandro / 911.")


def render_header() -> None:
    title, actions = st.columns([4, 1])
    with title:
        st.markdown("<div class='hero'><p class='eyebrow'>Kafka · procesamiento en tiempo real</p><h1>Central de Emergencias 911</h1></div>", unsafe_allow_html=True)
    with actions:
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()


@st.fragment(run_every="2s")
def render_dashboard_metrics(db: EmergencyStorage) -> None:
    summary = db.summary()
    invalid = db.dead_letter_count()
    cols = st.columns(5)
    cols[0].metric("Emergencias activas", f"{summary['active']:,}")
    cols[1].metric("Emergencias críticas", f"{summary['critical']:,}")
    cols[2].metric("Unidades disponibles", f"{summary['units']:,}")
    cols[3].metric("Eventos procesados", f"{summary['processed']:,}")
    cols[4].metric("Eventos rechazados", f"{invalid:,}")
    st.caption("Indicadores actualizados automáticamente cada 2 segundos.")


def individual_generator() -> None:
    st.subheader("Registrar una emergencia")
    district_names = {item["name"]: item["id"] for item in DISTRICTS}
    types = [item[0] for item in EMERGENCY_TYPES]
    with st.form("individual-event", clear_on_submit=True):
        district_name = st.selectbox("Distrito", list(district_names))
        emergency_type = st.selectbox("Tipo de emergencia", types)
        location = st.text_input("Ubicación", placeholder="Dirección o punto de referencia")
        priority = st.select_slider("Prioridad", options=[1, 2, 3, 4, 5], value=3)
        description = st.text_area("Descripción", placeholder="Describa brevemente la situación")
        submitted = st.form_submit_button("Publicar emergencia en Kafka", use_container_width=True)
    if submitted:
        if not location.strip() or not description.strip():
            st.error("La ubicación y la descripción son obligatorias.")
            return
        event = create_event(
            district_id=district_names[district_name],
            emergency_type=emergency_type,
            priority=priority,
            location=location.strip(),
            description=description.strip(),
        )
        try:
            result = producer().publish_many([event])
            if result["delivered"] == 1:
                st.success(f"{event['report_number']} publicada correctamente.")
            else:
                st.error("Kafka no confirmó la entrega del evento.")
        except Exception as exc:
            st.error(f"No se pudo publicar en Kafka: {exc}")


def batch_generator() -> None:
    st.subheader("Simular un pico masivo")
    st.caption("Genera eventos con distribución desigual por distrito, tipo y prioridad. También puede introducir duplicados y registros incompletos controlados.")
    with st.form("batch-event"):
        scenario = st.selectbox("Escenario del pico", list(SCENARIOS))
        count = st.number_input("Cantidad de llamadas", min_value=10, max_value=50000, value=1000, step=100)
        imperfection = st.slider("Datos imperfectos controlados", 0.0, 10.0, 2.0, 0.5)
        submitted = st.form_submit_button("Disparar lote masivo", use_container_width=True)
    if submitted:
        with st.spinner(f"Publicando {count:,} llamadas en Kafka..."):
            try:
                events = create_batch(int(count), imperfection / 100, scenario=scenario)
                result = producer().publish_many(events)
                st.session_state.last_throughput = result
            except Exception as exc:
                st.error(f"El lote no pudo publicarse: {exc}")
                return
        st.success(f"Kafka confirmó {result['delivered']:,} de {result['queued']:,} eventos.")
        a, b, c = st.columns(3)
        a.metric("Throughput del generador", f"{result['events_per_second']:,.0f} eventos/s")
        b.metric("Tiempo de envío", f"{result['elapsed_seconds']:.2f} s")
        c.metric("Errores de entrega", f"{result['errors']:,}")


def active_events(db: EmergencyStorage) -> None:
    st.subheader("Emergencias recientes")
    events = db.recent_events(40)
    if not events:
        st.info("Todavía no hay eventos procesados. Registre una emergencia o dispare un lote.")
        return
    options = {
        f"{event['report_number']} · {event['emergency_type']} · {event['district_name']} · P{event['priority']}": event["report_number"]
        for event in events
    }
    selected = st.selectbox("Seleccione una emergencia para abrir su expediente", list(options))
    if st.button("Abrir detalle", use_container_width=True):
        st.session_state.selected_report = options[selected]
        st.session_state.page = "detail"
        st.rerun()

    table = pd.DataFrame(events)
    columns = ["report_number", "district_name", "emergency_type", "priority", "status", "location"]
    st.dataframe(table[columns], use_container_width=True, hide_index=True)


def balance_dashboard(db: EmergencyStorage) -> None:
    st.subheader("Balance de carga por distrito")
    rows = db.dashboard_rows()
    if not rows:
        st.warning("No hay métricas disponibles.")
        return
    frame = pd.DataFrame(rows)
    selected = st.selectbox("Distrito solicitado durante la defensa", frame["Distrito"].tolist())
    current = frame[frame["Distrito"] == selected].iloc[0]
    a, b, c, d = st.columns(4)
    a.metric("Llamadas activas", int(current["Activas"]))
    b.metric("Unidades disponibles", int(current["Unidades"]))
    c.metric("Balance", int(current["Balance"]))
    d.metric("Exposición", current["Exposición"])

    chart = px.bar(
        frame,
        x="Distrito",
        y=["Activas", "Unidades"],
        barmode="group",
        color_discrete_map={"Activas": "#ef4444", "Unidades": "#38bdf8"},
        labels={"value": "Cantidad", "variable": "Indicador"},
    )
    chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#dbeafe",
        legend_title_text="",
    )
    st.plotly_chart(chart, use_container_width=True)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def dashboard_page(db: EmergencyStorage) -> None:
    render_header()
    render_dashboard_metrics(db)
    st.divider()
    tab_control, tab_massive, tab_balance = st.tabs(["Centro de control", "Generador masivo", "Balance por distrito"])
    with tab_control:
        form_col, list_col = st.columns([0.85, 1.35], gap="large")
        with form_col:
            individual_generator()
        with list_col:
            active_events(db)
    with tab_massive:
        batch_generator()
        if "last_throughput" in st.session_state:
            result = st.session_state.last_throughput
            st.json(result)
    with tab_balance:
        balance_dashboard(db)

    with st.expander("Herramientas de demostración"):
        st.warning("Esta acción elimina únicamente los datos generados para la demo.")
        if st.button("Reiniciar datos de demostración"):
            db.reset_demo_data()
            st.success("Datos reiniciados.")
            time.sleep(0.5)
            st.rerun()


def detail_page(db: EmergencyStorage) -> None:
    report_number = st.session_state.selected_report
    event = db.get_event(report_number) if report_number else None
    if not event:
        st.error("La emergencia seleccionada ya no existe.")
        if st.button("Regresar al dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        return

    top_left, top_right = st.columns([4, 1])
    with top_left:
        if st.button("← Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        st.markdown("<p class='eyebrow'>Expediente operativo</p>", unsafe_allow_html=True)
        st.title(f"Emergencia {event['report_number']}")
    with top_right:
        st.metric("Cola activa", db.summary()["active"])

    info, action = st.columns([1.2, 0.8], gap="large")
    with info:
        st.subheader("Información de la llamada")
        for label, key in [
            ("Tipo", "emergency_type"),
            ("Distrito", "district_name"),
            ("Ubicación", "location"),
            ("Prioridad", "priority"),
            ("Descripción", "description"),
            ("Estado", "status"),
            ("Fecha y hora", "occurred_at"),
        ]:
            st.markdown(f"<div class='detail-card'><b>{label}</b><br>{event.get(key, '—')}</div>", unsafe_allow_html=True)

    with action:
        st.subheader("Despacho y seguimiento")
        statuses = ["Recibida", "Unidad asignada", "En camino", "Resuelta"]
        units = ["", "Ambulancia A-01", "Ambulancia A-02", "Patrulla P-01", "Patrulla P-02", "Bomberos B-01", "Rescate R-01"]
        current_status = event.get("status", "Recibida")
        current_unit = event.get("assigned_unit") or ""
        with st.form("update-detail"):
            status = st.selectbox("Estado", statuses, index=statuses.index(current_status) if current_status in statuses else 0)
            unit = st.selectbox("Unidad asignada", units, index=units.index(current_unit) if current_unit in units else 0)
            observation = st.text_area("Observación", value=event.get("observation", ""))
            submitted = st.form_submit_button("Guardar seguimiento", use_container_width=True)
        if submitted:
            db.update_event(report_number, status, unit, observation)
            st.success("Seguimiento actualizado.")
            st.rerun()

        st.markdown("#### Flujo operativo")
        current_index = statuses.index(current_status) if current_status in statuses else 0
        for index, value in enumerate(statuses):
            marker = "✅" if index <= current_index else "○"
            st.write(f"{marker} {value}")

    st.caption(f"Central La Ceiba · Operador: {event.get('operator', 'Alejandro')} · {datetime.now().strftime('%H:%M:%S')}")


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

    if st.session_state.page == "detail":
        detail_page(db)
    else:
        dashboard_page(db)


if __name__ == "__main__":
    main()
