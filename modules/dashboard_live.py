"""
modules/dashboard_live.py
Dashboard de Asistencia en Vivo - versión robusta con components.v1.html

El render completo se hace en UN SOLO bloque HTML autocontenido para evitar
que Streamlit fragmente y escape los divs/spans del timeline.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from core.ui import (
    render_page_title,
    render_timeline_header, render_timeline_now_overlay,
    render_employee_timeline_row, render_country_block,
)
from core.time_utils import (
    today_gt, now_gt, current_time_gt, format_date_long,
)
from core.config import (
    COLORS, REFRESH_LIVE_DASHBOARD,
    INCIDENT_TYPES, INCIDENT_LABELS, INCIDENT_ICONS, INCIDENT_COLORS,
)
from core.attendance_engine import get_all_statuses, compute_daily_kpis
from core.incidents import (
    get_active_incidents, register_incident, close_incident,
    get_current_duration_minutes, format_duration,
)
from core.auth import current_user_display_name
from core.flags import flag_emoji_unicode, flag_img_inline
from core.notifications import notify_success, notify_error


TIMELINE_START_HOUR = 5
TIMELINE_END_HOUR = 21


# ============================================================
# CSS AUTOCONTENIDO para el bloque renderizado con components.html
# ============================================================
DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

* { box-sizing: border-box; }

body {
    margin: 0;
    padding: 0;
    font-family: 'Inter Tight', -apple-system, sans-serif;
    background: transparent;
    color: #0A0A0A;
}

.stt-wrap { padding: 0; }

/* KPI Row */
.stt-kpi-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}
.stt-kpi {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 18px 20px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.stt-kpi-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 12px;
}
.stt-kpi-value {
    font-family: 'Inter Tight', sans-serif;
    font-size: 38px;
    font-weight: 700;
    color: #0A0A0A;
    line-height: 1;
    letter-spacing: -1.5px;
}
.stt-kpi-value-sub {
    font-size: 16px;
    color: #94A3B8;
    font-weight: 400;
    margin-left: 4px;
}
.stt-kpi-foot {
    margin-top: 12px;
    font-size: 11px;
    color: #64748B;
    display: flex;
    align-items: center;
    gap: 6px;
}
.stt-kpi-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

/* Legend */
.stt-legend {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 12px 18px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 22px;
    flex-wrap: wrap;
    font-size: 12px;
}
.stt-legend-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #64748B;
}
.stt-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #334155;
}
.stt-legend-swatch {
    width: 22px;
    height: 12px;
    border-radius: 2px;
    display: inline-block;
}

/* Country card */
.stt-country-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-bottom: 16px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.stt-country-header {
    padding: 16px 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #E2E8F0;
}
.stt-country-tag {
    display: inline-block;
    background: #F1F5F9;
    color: #475569;
    padding: 4px 10px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    margin-right: 12px;
    vertical-align: middle;
}
.stt-country-flag-mini {
    display: inline-block;
    margin-right: 6px;
    vertical-align: middle;
}
.stt-country-flag-mini img {
    width: 18px;
    height: 18px;
    display: inline-block;
    vertical-align: middle;
}
.stt-country-title {
    font-size: 18px;
    font-weight: 700;
    color: #0A0A0A;
    vertical-align: middle;
}
.stt-sede-hours { text-align: right; }
.stt-sede-hours-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #94A3B8;
    margin-bottom: 2px;
}
.stt-sede-hours-value {
    font-family: 'Inter Tight', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #0A0A0A;
}

/* Timeline header */
.stt-timeline-header {
    display: grid;
    grid-template-columns: 220px 1fr;
    padding: 12px 22px;
    border-bottom: 1px solid #F1F5F9;
    background: #FAFBFC;
}
.stt-timeline-header-left {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #94A3B8;
    align-self: center;
}
.stt-timeline-hours {
    position: relative;
    height: 18px;
}
.stt-timeline-hour-mark {
    position: absolute;
    top: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94A3B8;
    font-weight: 500;
    transform: translateX(-50%);
}
.stt-timeline-hour-mark sub { font-size: 8px; opacity: 0.7; }

/* Employee row */
.stt-emp-row {
    display: grid;
    grid-template-columns: 220px 1fr;
    padding: 16px 22px;
    border-bottom: 1px solid #F1F5F9;
    align-items: center;
    min-height: 60px;
    position: relative;
}
.stt-emp-row:last-child { border-bottom: none; }
.stt-emp-info {
    display: flex;
    align-items: center;
    gap: 10px;
}
.stt-flag-pill {
    display: inline-flex;
    align-items: center;
    line-height: 1;
}
.stt-flag-pill img {
    width: 14px;
    height: 14px;
    margin: 0;
}
.stt-avatar-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 11px;
    color: #475569;
    letter-spacing: 0.5px;
    flex-shrink: 0;
}
.stt-emp-data { line-height: 1.3; }
.stt-emp-data-name {
    font-weight: 600;
    color: #0A0A0A;
    font-size: 13px;
}
.stt-emp-data-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94A3B8;
    letter-spacing: 0.3px;
}

/* Track */
.stt-track {
    position: relative;
    height: 28px;
}
.stt-track-grid {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: #F1F5F9;
}

/* Segments */
.stt-segment {
    position: absolute;
    top: 6px;
    height: 16px;
    display: flex;
    align-items: center;
    padding: 0 8px;
    border-radius: 2px;
    font-family: 'Inter Tight', sans-serif;
    font-size: 10px;
    font-weight: 700;
    color: #FFFFFF;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
}
.stt-segment-work { background: #16A34A; }
.stt-segment-lunch { background: #DC2626; }
.stt-segment-vacation { background: #0891B2; }
.stt-segment-permit { background: #2563EB; }
.stt-segment-sick { background: #7C2D12; }
.stt-segment-overtime { background: #D97706; }
.stt-segment-label-left { text-align: left; }
.stt-segment-label-right { margin-left: auto; text-align: right; }

.stt-status-pill {
    position: absolute;
    top: 6px;
    left: 0;
    height: 16px;
    padding: 0 12px;
    display: inline-flex;
    align-items: center;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Día libre: barra completa con patrón rayado (estilo tu imagen 2) */
.stt-segment-dayoff {
    position: absolute;
    top: 4px;
    left: 0;
    right: 0;
    height: 20px;
    border: 1px dashed #CBD5E1;
    border-radius: 3px;
    background-image: repeating-linear-gradient(
        135deg,
        #F1F5F9 0px,
        #F1F5F9 6px,
        #FFFFFF 6px,
        #FFFFFF 12px
    );
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter Tight', sans-serif;
    font-size: 10px;
    font-weight: 700;
    color: #64748B;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

/* Ausente: similar al día libre pero con tinte rojo sutil */
.stt-segment-absent {
    position: absolute;
    top: 4px;
    left: 0;
    right: 0;
    height: 20px;
    border: 1px dashed #FCA5A5;
    border-radius: 3px;
    background-image: repeating-linear-gradient(
        135deg,
        #FEE2E2 0px,
        #FEE2E2 6px,
        #FFFFFF 6px,
        #FFFFFF 12px
    );
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter Tight', sans-serif;
    font-size: 10px;
    font-weight: 700;
    color: #991B1B;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

/* === INCIDENCIAS ACTIVAS === */
.stt-incident-overlay {
    position: absolute;
    top: 1px;
    height: 26px;
    border-radius: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
    box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    overflow: hidden;
}
.stt-incident-label {
    font-family: 'Inter Tight', sans-serif;
    font-size: 9px;
    font-weight: 700;
    color: #FFFFFF;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 0 8px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.stt-incident-badge {
    display: inline-block;
    margin-left: 8px;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: 'Inter Tight', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    vertical-align: middle;
}

/* NOW line - se renderiza UNA sola vez por country block como overlay absoluto */
.stt-country-body {
    position: relative;
}
.stt-now-overlay {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 220px;
    right: 22px;
    pointer-events: none;
    z-index: 10;
}
.stt-now-overlay-inner {
    position: relative;
    height: 100%;
    margin-left: 22px;
}
.stt-now-line {
    position: absolute;
    top: 8px;
    bottom: 0;
    width: 1.5px;
    background: #0A0A0A;
    z-index: 10;
}
.stt-now-badge {
    position: absolute;
    top: -8px;
    transform: translateX(-50%);
    background: #0A0A0A;
    color: #FFFFFF;
    padding: 4px 10px;
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    white-space: nowrap;
    z-index: 11;
}
.stt-now-dot {
    position: absolute;
    bottom: -3px;
    left: 50%;
    transform: translateX(-50%);
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #0A0A0A;
}

/* Last update */
.stt-last-update {
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94A3B8;
    letter-spacing: 0.5px;
    margin-top: 12px;
}
.stt-last-update-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #16A34A;
    margin-right: 6px;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ============================================================
   RESPONSIVE — Soporta de smartphone (360px) hasta TV 4K (3840px)
   ============================================================ */

/* TV 4K y monitores ultra-wide (≥2560px): escala TODO un poco más */
@media (min-width: 2560px) {
    .stt-wrap { max-width: 2400px; margin: 0 auto; }
    .stt-kpi-value { font-size: 52px; }
    .stt-kpi-label { font-size: 12px; }
    .stt-kpi-foot { font-size: 13px; }
    .stt-country-title { font-size: 22px; }
    .stt-sede-hours-value { font-size: 30px; }
    .stt-emp-data-name { font-size: 15px; }
    .stt-emp-data-sub { font-size: 12px; }
    .stt-segment { font-size: 12px; height: 20px; }
    .stt-timeline-hour-mark { font-size: 12px; }
    .stt-emp-row { min-height: 70px; padding: 20px 28px; }
}

/* Desktop wide (1440px–2559px): default sin cambios mayores */
@media (min-width: 1440px) and (max-width: 2559px) {
    .stt-kpi-value { font-size: 42px; }
}

/* Tablet landscape / laptop pequeño (1024px–1439px) */
@media (max-width: 1439px) {
    .stt-kpi-value { font-size: 34px; }
    .stt-kpi-label { font-size: 9px; letter-spacing: 1.2px; }
    .stt-kpi { padding: 16px 18px; }
    .stt-legend { gap: 16px; font-size: 11px; }
    .stt-country-title { font-size: 16px; }
    .stt-sede-hours-value { font-size: 22px; }
}

/* Tablet portrait (768px–1023px) */
@media (max-width: 1023px) {
    .stt-kpi-row {
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    }
    .stt-kpi-value { font-size: 30px; }
    .stt-timeline-header,
    .stt-emp-row {
        grid-template-columns: 180px 1fr;
        padding: 12px 16px;
    }
    .stt-now-overlay { left: 180px; right: 16px; }
    .stt-country-header { padding: 14px 16px; }
    .stt-emp-data-name { font-size: 12px; }
    .stt-emp-data-sub { font-size: 9px; }
    .stt-timeline-hour-mark { font-size: 9px; }
    .stt-segment { font-size: 9px; }
}

/* Smartphone horizontal y tablets pequeñas (600px–767px) */
@media (max-width: 767px) {
    .stt-kpi-row {
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }
    .stt-kpi { padding: 14px 14px; }
    .stt-kpi-value { font-size: 28px; }
    .stt-kpi-foot { font-size: 10px; }
    .stt-legend {
        gap: 12px;
        font-size: 10px;
        padding: 10px 14px;
    }
    .stt-legend-swatch { width: 16px; height: 10px; }
    .stt-timeline-header,
    .stt-emp-row {
        grid-template-columns: 140px 1fr;
        padding: 10px 12px;
    }
    .stt-country-header { padding: 12px 14px; }
    .stt-now-overlay { left: 140px; right: 12px; }
    .stt-avatar-circle { width: 28px; height: 28px; font-size: 10px; }
    .stt-flag-pill img { width: 13px; height: 13px; }
    .stt-emp-data-name { font-size: 11px; }
    .stt-emp-data-sub { font-size: 9px; }
    .stt-timeline-hour-mark { font-size: 8px; }
    .stt-segment { font-size: 8px; padding: 0 4px; }
    .stt-country-title { font-size: 14px; }
    .stt-country-flag-mini img { width: 14px; height: 14px; }
    .stt-sede-hours-value { font-size: 18px; }
    .stt-now-badge { font-size: 9px; padding: 3px 6px; }
}

/* Smartphone (≤599px): layout más vertical */
@media (max-width: 599px) {
    .stt-kpi-row {
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
        margin-bottom: 14px;
    }
    .stt-kpi-value { font-size: 24px; }
    .stt-kpi-label { font-size: 8px; letter-spacing: 1px; margin-bottom: 8px; }
    .stt-kpi-foot { font-size: 9px; margin-top: 8px; }
    .stt-legend {
        gap: 8px 12px;
        font-size: 9px;
        padding: 8px 12px;
    }
    .stt-timeline-header,
    .stt-emp-row {
        grid-template-columns: 110px 1fr;
        padding: 8px 10px;
    }
    .stt-now-overlay { left: 110px; right: 10px; }
    .stt-emp-info { gap: 6px; }
    .stt-avatar-circle { width: 24px; height: 24px; font-size: 9px; }
    .stt-emp-data-name { font-size: 10px; }
    .stt-emp-data-sub { font-size: 8px; }
    .stt-timeline-hour-mark { font-size: 7px; }
    .stt-segment {
        font-size: 7px;
        padding: 0 3px;
        height: 14px;
        top: 7px;
    }
    .stt-segment-dayoff,
    .stt-segment-absent {
        font-size: 8px;
        height: 16px;
        top: 6px;
        letter-spacing: 0.8px;
    }
}
</style>
"""


def _build_kpi_card(label, value, value_sub="", foot_text="", foot_color="#16A34A"):
    sub = f'<span class="stt-kpi-value-sub">{value_sub}</span>' if value_sub else ""
    foot = ""
    if foot_text:
        foot = (
            f'<div class="stt-kpi-foot">'
            f'<span class="stt-kpi-dot" style="background:{foot_color}"></span>'
            f'{foot_text}</div>'
        )
    return (
        f'<div class="stt-kpi">'
        f'<div class="stt-kpi-label">{label}</div>'
        f'<div class="stt-kpi-value">{value}{sub}</div>'
        f'{foot}'
        f'</div>'
    )


def _build_legend(items):
    swatches = "".join([
        f'<span class="stt-legend-item">'
        f'<span class="stt-legend-swatch" style="background:{c}"></span>{l}'
        f'</span>'
        for l, c in items
    ])
    return (
        f'<div class="stt-legend">'
        f'<span class="stt-legend-label">REFERENCIA</span>'
        f'{swatches}</div>'
    )


def _build_now_overlay(now_time, start_hour, end_hour):
    """Construye una sola línea AHORA por bloque, no por fila."""
    cur_min = now_time.hour * 60 + now_time.minute
    start_min = start_hour * 60
    end_min = end_hour * 60
    if cur_min < start_min or cur_min > end_min:
        return ""
    pct = ((cur_min - start_min) / (end_min - start_min)) * 100
    label = now_time.strftime("%I:%M %p").lstrip("0")
    return (
        f'<div class="stt-now-overlay">'
        f'<div class="stt-now-overlay-inner">'
        f'<div class="stt-now-badge" style="left:{pct}%">AHORA · {label}</div>'
        f'<div class="stt-now-line" style="left:{pct}%">'
        f'<div class="stt-now-dot"></div></div>'
        f'</div></div>'
    )


def render():
    """Renderiza el dashboard. Modo VIVO (hoy) o HISTÓRICO (día/sem/mes/año pasado)."""
    from core.filters import render_period_selector
    from core.config import INCIDENT_LABELS, INCIDENT_ICONS, INCIDENT_COLORS
    from core.incidents import load_incidents_df, compute_row_duration, format_duration

    # Header
    render_page_title(
        eyebrow="VISTA DIARIA",
        title="Asistencia",
        subtitle=format_date_long(today_gt()),
    )

    # ============================================================
    # FILTRO GLOBAL DE PERÍODO
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:8px 0 8px 0;">'
        '— FILTRO DE PERÍODO'
        '</div>',
        unsafe_allow_html=True,
    )
    period_kind, date_from, date_to, period_label = render_period_selector("dash")

    # Modo: VIVO (hoy = día único y date = today) o HISTÓRICO (cualquier otro caso)
    today = today_gt()
    is_live_mode = (period_kind == "day" and date_from == today)

    # Solo auto-refresh en modo VIVO
    if is_live_mode:
        st_autorefresh(interval=REFRESH_LIVE_DASHBOARD * 1000, key="dashboard_autorefresh")

    st.divider()

    # ============================================================
    # MODO VIVO: timeline de HOY + panel de incidencias
    # ============================================================
    if is_live_mode:
        try:
            statuses = get_all_statuses(today)
        except Exception as e:
            st.error(f"⚠️ Error al cargar datos del Sheet: {e}")
            st.caption("Verifica que el Setup Inicial se haya ejecutado correctamente.")
            return

        if not statuses:
            st.warning("No hay empleados activos. Ve a 🛠️ Setup Inicial.")
            return

        # Render del timeline (función auxiliar)
        _render_live_timeline(statuses)
        return

    # ============================================================
    # MODO HISTÓRICO: resumen de incidencias del período
    # ============================================================
    _render_historical_summary(date_from, date_to, period_label, period_kind)


def _render_historical_summary(date_from, date_to, period_label, period_kind):
    """Vista histórica: resumen de incidencias en el período seleccionado."""
    from core.incidents import load_incidents_df, compute_row_duration, format_duration
    from core.config import INCIDENT_LABELS, INCIDENT_ICONS, INCIDENT_COLORS
    from core.sheets import read_worksheet
    from core.config import WS_EMPLOYEES

    st.markdown(
        f'<div style="background:#FEF3C7;border-left:3px solid #D97706;'
        f'padding:12px 18px;border-radius:0 4px 4px 0;margin-bottom:16px;'
        f'font-size:12px;color:#92400E;">'
        f'📊 <strong>Modo histórico</strong> · Visualizando {period_label.lower()}. '
        f'Selecciona "Día" + fecha de hoy para volver al modo en vivo.'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Cargar empleados
    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy() if not employees_df.empty else pd.DataFrame()

    # Cargar incidencias del período
    df = load_incidents_df()
    if df.empty:
        st.info("📭 No hay incidencias registradas todavía.")
        return

    filtered = df[
        (df["fecha_parsed"] >= date_from) & (df["fecha_parsed"] <= date_to)
    ].copy()

    if filtered.empty:
        st.info(f"📭 Sin incidencias en {period_label.lower()}.")
        return

    filtered["duracion_calc"] = filtered.apply(compute_row_duration, axis=1)

    # KPIs del período
    total_inc = len(filtered)
    total_min = int(filtered["duracion_calc"].sum())
    empleados_afectados = filtered["empleado_id"].nunique()
    activas = int((filtered["estado"].astype(str).str.upper() == "ACTIVA").sum())

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">INCIDENCIAS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total_inc}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">{activas} activa{'s' if activas != 1 else ''}</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">TIEMPO TOTAL</div>
            <div style="font-size:36px;font-weight:700;color:#F97316;line-height:1;letter-spacing:-1.5px;">{format_duration(total_min)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">{total_min} min acumulados</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{empleados_afectados}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">con al menos 1 reporte</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PROMEDIO POR REPORTE</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{format_duration(total_min // total_inc) if total_inc else '0'}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">duración media</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Tabla de incidencias del período
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        '— DETALLE DEL PERÍODO</div>',
        unsafe_allow_html=True,
    )

    sorted_df = filtered.sort_values(["fecha_parsed", "hi_parsed"], ascending=False).reset_index(drop=True)
    rows_html = []
    for _, row in sorted_df.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name] if not employees_active.empty else pd.DataFrame()
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag_html = flag_img_inline(pais, size=14)

        tipo = str(row.get("tipo", ""))
        tipo_label = INCIDENT_LABELS.get(tipo, tipo)
        tipo_icon = INCIDENT_ICONS.get(tipo, "❓")
        tipo_color = INCIDENT_COLORS.get(tipo, "#64748B")

        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""
        hi = str(row.get("hora_inicio", "") or "")
        hf = str(row.get("hora_fin", "") or "")
        is_active = str(row.get("estado", "")).upper() == "ACTIVA"
        tiempo_str = f"{hi} → en curso" if is_active else (f"{hi} → {hf}" if hf else hi)
        duration_min = int(row.get("duracion_calc", 0) or 0)
        nota = (str(row.get("nota", "") or ""))[:60]

        rows_html.append(
            f'<tr>'
            f'<td class="hd-cell hd-mono">{fecha_str}</td>'
            f'<td class="hd-cell">{flag_html}<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong></td>'
            f'<td class="hd-cell"><span style="margin-right:4px;font-size:14px;">{tipo_icon}</span>'
            f'<span style="display:inline-block;padding:3px 8px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span></td>'
            f'<td class="hd-cell hd-mono">{tiempo_str}</td>'
            f'<td class="hd-cell" style="text-align:center;">'
            f'<strong style="font-size:14px;color:{tipo_color};font-family:\'JetBrains Mono\',monospace;">{format_duration(duration_min)}</strong></td>'
            f'<td class="hd-cell" style="font-size:11px;color:#475569;">{nota or "—"}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.hd-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.hd-table th{padding:12px 14px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.hd-cell{padding:12px 14px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.hd-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;">'
        '<table class="hd-table"><thead><tr>'
        '<th>Fecha</th><th>Empleado</th><th>Tipo</th>'
        '<th>Horario</th><th style="text-align:center;">Duración</th><th>Nota</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _render_live_timeline(statuses):
    """Renderiza el dashboard en modo VIVO (timeline + KPIs + panel incidencias por persona)."""
    # ============================================================
    # PANEL POR EMPLEADO: cada uno con su botón de registrar incidencia
    # ============================================================
    _render_per_employee_incidents(statuses)

    kpis = compute_daily_kpis(statuses)
    total = kpis["total"]

    # ============================================================
    # CONSTRUIR EL HTML COMPLETO COMO UN STRING ÚNICO
    # ============================================================
    parts = ['<div class="stt-wrap">']

    # --- KPIs ---
    incident_color = "#F97316"  # naranja para destacar incidencias
    kpi_html = '<div class="stt-kpi-row">' + "".join([
        _build_kpi_card("PERSONAL PROGRAMADO", str(kpis["programmed"]),
                        f"/ {total}", "activos hoy", COLORS["working"]),
        _build_kpi_card("TRABAJANDO AHORA", str(kpis["working"]),
                        "", "en línea", COLORS["working"]),
        _build_kpi_card("CON INCIDENCIA", str(kpis["with_incident"]),
                        "", "reportes activos", incident_color),
        _build_kpi_card("EN ALMUERZO", str(kpis["lunch"]),
                        "", "pausa de comida", COLORS["lunch"]),
        _build_kpi_card("DÍA LIBRE", str(kpis["day_off"]),
                        "", "descanso programado", COLORS["day_off"]),
        _build_kpi_card("OTRAS AUSENCIAS", str(kpis["other_absences"]),
                        "", "permiso · vacaciones · incapacidad", COLORS["permit"]),
    ]) + '</div>'
    parts.append(kpi_html)

    # --- Legend ---
    parts.append(_build_legend([
        ("Trabajando", COLORS["working"]),
        ("Almuerzo", COLORS["lunch"]),
        ("Incidencia activa", incident_color),
        ("Hora extra", COLORS["overtime"]),
        ("Llegada tarde", COLORS["late"]),
        ("Día libre", COLORS["day_off"]),
        ("Permiso", COLORS["permit"]),
        ("Vacaciones", COLORS["vacation"]),
        ("Incapacidad", COLORS["sick"]),
    ]))

    # --- Bloques por país ---
    gt_statuses = [s for s in statuses if s["employee"].get("pais") == "GT"]
    ve_statuses = [s for s in statuses if s["employee"].get("pais") == "VE"]

    gt_hours = sum(s["scheduled_hours"] for s in gt_statuses)
    ve_hours = sum(s["scheduled_hours"] for s in ve_statuses)

    now_overlay = _build_now_overlay(
        current_time_gt(), TIMELINE_START_HOUR, TIMELINE_END_HOUR,
    )
    timeline_header = render_timeline_header(TIMELINE_START_HOUR, TIMELINE_END_HOUR)

    def sort_key(s):
        rol = s["employee"].get("rol", "")
        priority = {"Manager": 0, "Supervisora": 1}.get(rol, 2)
        return (priority, s["employee"].get("nombre", ""))

    # Guatemala
    if gt_statuses:
        gt_sorted = sorted(gt_statuses, key=sort_key)
        rows = "".join([
            render_employee_timeline_row(
                s["employee"], s, "",  # No incluir overlay por fila
                TIMELINE_START_HOUR, TIMELINE_END_HOUR,
            )
            for s in gt_sorted
        ])
        from core.flags import flag_img_inline
        gt_flag_img = flag_img_inline("GT", size=18)
        parts.append(
            f'<div class="stt-country-card">'
            f'<div class="stt-country-header">'
            f'<div>'
            f'<span class="stt-country-tag">GT · 01</span>'
            f'<span class="stt-country-flag-mini">{gt_flag_img}</span>'
            f'<span class="stt-country-title">Guatemala</span>'
            f'</div>'
            f'<div class="stt-sede-hours">'
            f'<div class="stt-sede-hours-label">HORAS PROGRAMADAS</div>'
            f'<div class="stt-sede-hours-value">{gt_hours:.0f}h</div>'
            f'</div></div>'
            f'<div class="stt-country-body">'
            f'{timeline_header}{rows}'
            f'{now_overlay}'
            f'</div></div>'
        )

    # Venezuela
    if ve_statuses:
        ve_sorted = sorted(ve_statuses, key=lambda s: s["employee"].get("nombre", ""))
        rows = "".join([
            render_employee_timeline_row(
                s["employee"], s, "",
                TIMELINE_START_HOUR, TIMELINE_END_HOUR,
            )
            for s in ve_sorted
        ])
        from core.flags import flag_img_inline
        ve_flag_img = flag_img_inline("VE", size=18)
        parts.append(
            f'<div class="stt-country-card">'
            f'<div class="stt-country-header">'
            f'<div>'
            f'<span class="stt-country-tag">VE · 02</span>'
            f'<span class="stt-country-flag-mini">{ve_flag_img}</span>'
            f'<span class="stt-country-title">Venezuela</span>'
            f'</div>'
            f'<div class="stt-sede-hours">'
            f'<div class="stt-sede-hours-label">HORAS PROGRAMADAS</div>'
            f'<div class="stt-sede-hours-value">{ve_hours:.0f}h</div>'
            f'</div></div>'
            f'<div class="stt-country-body">'
            f'{timeline_header}{rows}'
            f'{now_overlay}'
            f'</div></div>'
        )

    # Last update
    now = now_gt()
    parts.append(
        f'<div class="stt-last-update">'
        f'<span class="stt-last-update-dot"></span>'
        f'EN VIVO · Última actualización: {now.strftime("%I:%M:%S %p").lstrip("0")} · '
        f'Auto-refresh cada {REFRESH_LIVE_DASHBOARD}s'
        f'</div>'
    )

    parts.append('</div>')  # cierre stt-wrap

    # ============================================================
    # RENDER EN UN ÚNICO IFRAME RESPONSIVO
    # ============================================================
    body_content = "".join(parts)
    full_html = (
        '<!DOCTYPE html>'
        '<html lang="es">'
        '<head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>STT Attendance</title>'
        + DASHBOARD_CSS +
        '</head>'
        '<body style="margin:0;padding:0;background:transparent;">'
        + body_content +
        '<script src="https://cdn.jsdelivr.net/npm/@twemoji/api@latest/dist/twemoji.min.js" crossorigin="anonymous"></script>'
        '<script>'
        'window.addEventListener("load", function(){'
        '  if (typeof twemoji !== "undefined") {'
        '    twemoji.parse(document.body, {folder:"svg", ext:".svg", '
        '      base:"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/"});'
        '  }'
        '});'
        '</script>'
        '</body>'
        '</html>'
    )

    # Cálculo dinámico de altura — ser GENEROSO para que NUNCA se corten empleados.
    # Activamos scrolling=True como red de seguridad por si la app responsive estira más.
    rows_count = len(statuses)
    gt_count = sum(1 for s in statuses if s["employee"].get("pais") == "GT")
    ve_count = sum(1 for s in statuses if s["employee"].get("pais") == "VE")

    # Alturas más generosas que las anteriores (causaron que Henry/Mark se cortaran)
    avg_row_height = 90       # +10 vs antes (80) para asegurar espacio
    kpis_height = 260         # +40 (KPIs ahora pueden incluir incidencias activas panel)
    country_overhead = 160    # +30 (header país + timeline header con más padding)
    last_update_height = 60
    safety_margin = 100       # generoso para evitar scrollbar interno o cortes

    total_height = (
        kpis_height
        + (country_overhead if gt_count else 0)
        + (gt_count * avg_row_height)
        + (country_overhead if ve_count else 0)
        + (ve_count * avg_row_height)
        + last_update_height
        + safety_margin
    )

    components.html(full_html, height=total_height, scrolling=True)



# ============================================================
# PANEL DE INCIDENCIAS POR EMPLEADO
# ============================================================
def _render_per_employee_incidents(statuses):
    """
    Una fila por empleado con expander para registrar incidencia inline.
    Cada fila: [bandera] [avatar] [nombre + rol] → click → form abajo con:
    Tipo + Hora Inicio + Hora Fin + Nota + Botón.
    """
    today = today_gt()
    active_df = get_active_incidents(today)
    num_active = len(active_df)

    # ============================================================
    # BANNER DE INCIDENCIAS ACTIVAS (si las hay)
    # ============================================================
    if num_active > 0:
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:#DC2626;margin:8px 0 12px 0;">'
            f'🚨 INCIDENCIAS ACTIVAS · {num_active}'
            f'</div>',
            unsafe_allow_html=True,
        )

        cards_html_parts = []
        for _, inc in active_df.iterrows():
            tipo = str(inc.get("tipo", "OTRO"))
            tipo_label = INCIDENT_LABELS.get(tipo, tipo)
            tipo_icon = INCIDENT_ICONS.get(tipo, "❓")
            tipo_color = INCIDENT_COLORS.get(tipo, "#64748B")

            emp_name = inc.get("empleado_nombre", "")
            emp_id = inc.get("empleado_id", "")
            emp_pais = ""
            for s in statuses:
                if str(s["employee"].get("id")) == str(emp_id):
                    emp_pais = s["employee"].get("pais", "")
                    break
            flag_html = flag_img_inline(emp_pais, size=14)

            hora_inicio = str(inc.get("hora_inicio", ""))
            duration_min = get_current_duration_minutes(hora_inicio)
            duration_str = format_duration(duration_min) if duration_min > 0 else "recién"
            nota = (str(inc.get("nota", "")) or "")[:60]

            cards_html_parts.append(f'''
            <div style="background:#FFFFFF;border:1px solid {tipo_color};border-radius:8px;
                        padding:14px 16px;display:flex;align-items:center;gap:12px;
                        box-shadow:0 2px 6px {tipo_color}22;">
                <div style="font-size:28px;line-height:1;">{tipo_icon}</div>
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap;">
                        {flag_html}
                        <strong style="font-size:14px;color:#0A0A0A;">{emp_name}</strong>
                        <span style="display:inline-block;padding:2px 7px;border-radius:3px;
                                     font-size:9px;font-weight:700;letter-spacing:0.5px;
                                     text-transform:uppercase;background:{tipo_color};color:#FFFFFF;">
                            {tipo_label}
                        </span>
                    </div>
                    <div style="font-size:11px;color:#64748B;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.3px;">
                        Desde {hora_inicio} · <strong style="color:{tipo_color};">{duration_str}</strong>
                        {f'· {nota}' if nota else ''}
                    </div>
                </div>
            </div>
            ''')

        st.markdown(
            '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));'
            'gap:10px;margin-bottom:16px;">' + "".join(cards_html_parts) + '</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # FILAS POR EMPLEADO con expander para registrar incidencia
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:8px 0 4px 0;">'
        '🚨 — REGISTRAR INCIDENCIA'
        '</div>'
        '<div style="font-size:12px;color:#64748B;margin-bottom:12px;">'
        'Click en el nombre de un empleado para abrir su formulario.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Ordenar: managers/supervisores primero, después por país y nombre
    def _sort_key(s):
        emp = s["employee"]
        rol = emp.get("rol", "")
        priority = {"Manager": 0, "Supervisora": 1, "Supervisor": 1}.get(rol, 2)
        return (priority, emp.get("pais", ""), emp.get("nombre", ""))

    sorted_statuses = sorted(statuses, key=_sort_key)

    # Una fila por empleado con expander
    for s in sorted_statuses:
        emp = s["employee"]
        emp_id = int(emp["id"])
        emp_name = emp["nombre"]
        pais = emp.get("pais", "")
        flag_uc = flag_emoji_unicode(pais)
        rol = emp.get("rol", "")

        # Label del expander: [bandera] [nombre] · [rol]
        expander_label = f"{flag_uc}  🚨  {emp_name}  ·  {rol}"

        with st.expander(expander_label, expanded=False):
            now_t = now_gt().time().replace(second=0, microsecond=0)

            col_tipo, col_hi, col_hf = st.columns([2, 1, 1])
            with col_tipo:
                tipo = st.selectbox(
                    "Tipo de incidencia",
                    options=INCIDENT_TYPES,
                    format_func=lambda x: f"{INCIDENT_ICONS.get(x, '?')}  {INCIDENT_LABELS.get(x, x)}",
                    key=f"row_inc_tipo_{emp_id}",
                )
            with col_hi:
                hora_inicio = st.time_input(
                    "Hora inicio",
                    value=now_t,
                    step=300,
                    key=f"row_inc_hi_{emp_id}",
                )
            with col_hf:
                hora_fin = st.time_input(
                    "Hora fin",
                    value=now_t,
                    step=300,
                    key=f"row_inc_hf_{emp_id}",
                )

            nota = st.text_input(
                "Nota (opcional)",
                placeholder="Ej: Reportado por WhatsApp",
                max_chars=200,
                key=f"row_inc_nota_{emp_id}",
            )

            # Vista previa de duración calculada
            from core.incidents import calculate_duration_minutes
            preview_min = calculate_duration_minutes(hora_inicio, hora_fin)
            if preview_min > 0:
                st.markdown(
                    f'<div style="background:#F0FDF4;border-left:3px solid #16A34A;'
                    f'padding:8px 14px;border-radius:0 4px 4px 0;font-size:12px;color:#15803D;'
                    f'margin:8px 0;">Duración calculada: <strong>{format_duration(preview_min)}</strong> '
                    f'({preview_min} min)</div>',
                    unsafe_allow_html=True,
                )
            elif preview_min <= 0:
                st.caption("⚠ La hora fin debe ser posterior a la hora inicio.")

            if st.button(
                f"Registrar incidencia para {emp_name}",
                use_container_width=True,
                type="primary",
                key=f"row_inc_submit_{emp_id}",
            ):
                try:
                    result = register_incident(
                        employee_id=emp_id,
                        employee_name=emp_name,
                        tipo=tipo,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        nota=nota,
                        registered_by=current_user_display_name(),
                    )
                    if result["success"]:
                        notify_success(
                            f"{emp_name} · {INCIDENT_LABELS.get(tipo)} · {format_duration(result['duracion_min'])}",
                            title="Incidencia registrada"
                        )
                        st.rerun()
                    else:
                        notify_error(result["message"])
                except Exception as e:
                    notify_error(str(e))
