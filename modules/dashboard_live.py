"""
modules/dashboard_live.py
Dashboard de Asistencia en Vivo. La vista estrella de la app.

Características:
- Header con eyebrow + título + fecha en español
- 5 KPI cards en vivo
- Leyenda de colores
- 2 bloques separados por país (Guatemala + Venezuela)
- Timeline horizontal de 5am a 9pm con barras por empleado
- Línea AHORA vertical actualizándose cada 60 segundos
- Refresh automático con st_autorefresh
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core.ui import (
    render_page_title, render_kpi_card, render_kpi_row, render_legend,
    render_timeline_header, render_timeline_now_overlay,
    render_employee_timeline_row, render_country_block,
)
from core.time_utils import (
    today_gt, now_gt, current_time_gt, format_date_long,
)
from core.config import COLORS, REFRESH_LIVE_DASHBOARD
from core.attendance_engine import (
    get_all_statuses, compute_daily_kpis,
)


TIMELINE_START_HOUR = 5
TIMELINE_END_HOUR = 21


def render():
    """Renderiza el dashboard completo."""
    # Auto-refresh cada 60 segundos
    st_autorefresh(interval=REFRESH_LIVE_DASHBOARD * 1000, key="dashboard_autorefresh")

    # Encabezado
    render_page_title(
        eyebrow="VISTA DIARIA",
        title="Asistencia",
        subtitle=format_date_long(today_gt()),
    )

    # Carga de datos
    try:
        statuses = get_all_statuses(today_gt())
    except Exception as e:
        st.error(f"⚠️ Error al cargar datos del Sheet: {e}")
        st.caption("Verifica que el Setup Inicial se haya ejecutado correctamente.")
        return

    if not statuses:
        st.warning("No hay empleados activos cargados. Ve a 🛠️ Setup Inicial.")
        return

    kpis = compute_daily_kpis(statuses)
    total = kpis["total"]

    # KPI Cards
    kpi_cards = [
        render_kpi_card(
            label="PERSONAL PROGRAMADO",
            value=str(kpis["programmed"]),
            value_sub=f"/ {total}",
            foot_text="activos hoy",
            foot_color=COLORS["working"],
        ),
        render_kpi_card(
            label="TRABAJANDO AHORA",
            value=str(kpis["working"]),
            foot_text="en línea",
            foot_color=COLORS["working"],
        ),
        render_kpi_card(
            label="EN ALMUERZO",
            value=str(kpis["lunch"]),
            foot_text="pausa de comida",
            foot_color=COLORS["lunch"],
        ),
        render_kpi_card(
            label="DÍA LIBRE",
            value=str(kpis["day_off"]),
            foot_text="descanso programado",
            foot_color=COLORS["day_off"],
        ),
        render_kpi_card(
            label="OTRAS AUSENCIAS",
            value=str(kpis["other_absences"]),
            foot_text="permiso · vacaciones · incapacidad",
            foot_color=COLORS["permit"],
        ),
    ]
    render_kpi_row(kpi_cards)

    # Leyenda
    render_legend([
        ("Trabajando", COLORS["working"]),
        ("Almuerzo", COLORS["lunch"]),
        ("Hora extra", COLORS["overtime"]),
        ("Llegada tarde", COLORS["late"]),
        ("Día libre", COLORS["day_off"]),
        ("Permiso", COLORS["permit"]),
        ("Vacaciones", COLORS["vacation"]),
        ("Incapacidad", COLORS["sick"]),
    ])

    # Separar por país
    gt_statuses = [s for s in statuses if s["employee"].get("pais") == "GT"]
    ve_statuses = [s for s in statuses if s["employee"].get("pais") == "VE"]

    gt_hours = sum(s["scheduled_hours"] for s in gt_statuses)
    ve_hours = sum(s["scheduled_hours"] for s in ve_statuses)

    # Overlay de "AHORA" único
    now_overlay_html = render_timeline_now_overlay(
        current_time_gt(), TIMELINE_START_HOUR, TIMELINE_END_HOUR,
    )

    # Header de columnas de tiempo
    timeline_header_html = render_timeline_header(TIMELINE_START_HOUR, TIMELINE_END_HOUR)

    # ----- Guatemala -----
    if gt_statuses:
        def sort_key(s):
            rol = s["employee"].get("rol", "")
            priority = {"Manager": 0, "Supervisora": 1}.get(rol, 2)
            return (priority, s["employee"].get("nombre", ""))
        gt_sorted = sorted(gt_statuses, key=sort_key)

        rows_html = "".join([
            render_employee_timeline_row(
                s["employee"], s, now_overlay_html,
                TIMELINE_START_HOUR, TIMELINE_END_HOUR,
            )
            for s in gt_sorted
        ])

        block_html = render_country_block(
            country_code="GT",
            country_name="Guatemala",
            tag="GT · 01",
            hours_value=f"{gt_hours:.0f}h",
            header_html=timeline_header_html,
            employee_rows_html=rows_html,
        )
        st.markdown(block_html, unsafe_allow_html=True)

    # ----- Venezuela -----
    if ve_statuses:
        ve_sorted = sorted(ve_statuses, key=lambda s: s["employee"].get("nombre", ""))

        rows_html = "".join([
            render_employee_timeline_row(
                s["employee"], s, now_overlay_html,
                TIMELINE_START_HOUR, TIMELINE_END_HOUR,
            )
            for s in ve_sorted
        ])

        block_html = render_country_block(
            country_code="VE",
            country_name="Venezuela",
            tag="VE · 02",
            hours_value=f"{ve_hours:.0f}h",
            header_html=timeline_header_html,
            employee_rows_html=rows_html,
        )
        st.markdown(block_html, unsafe_allow_html=True)

    # Last update indicator
    now = now_gt()
    st.markdown(
        f"""
        <div class="stt-last-update">
            <span class="stt-last-update-dot"></span>
            EN VIVO · Última actualización: {now.strftime('%I:%M:%S %p').lstrip('0')} ·
            Auto-refresh cada {REFRESH_LIVE_DASHBOARD}s
        </div>
        """,
        unsafe_allow_html=True,
    )
