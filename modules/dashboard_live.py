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
    background: #E2E8F0;
    pointer-events: none;
}
.stt-track-grid-emphasis {
    background: #94A3B8;
    width: 1px;
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
    overflow: visible;
    cursor: help;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stt-incident-overlay:hover {
    transform: scale(1.03);
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    z-index: 50;
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
    pointer-events: none;
}

/* === Tooltip custom (hover) - debajo de la barra === */
.stt-incident-tooltip {
    position: absolute;
    top: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #0F172A;
    color: #FFFFFF;
    padding: 10px 14px;
    border-radius: 6px;
    font-family: 'Inter Tight', sans-serif;
    font-size: 11px;
    line-height: 1.5;
    white-space: nowrap;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    opacity: 0;
    pointer-events: none;
    z-index: 100;
    transition: opacity 0.15s ease;
    min-width: 180px;
}
.stt-incident-tooltip::after {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border-width: 6px;
    border-style: solid;
    border-color: transparent transparent #0F172A transparent;
}
.stt-incident-overlay:hover .stt-incident-tooltip {
    opacity: 1;
}
.stt-tt-title {
    font-weight: 700;
    font-size: 12px;
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid #334155;
}
.stt-tt-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin: 2px 0;
}
.stt-tt-k {
    color: #94A3B8;
    font-size: 10px;
    letter-spacing: 0.3px;
}
.stt-tt-v {
    color: #FFFFFF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
}
.stt-tt-dur {
    color: #FCD34D;
}
.stt-tt-note {
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid #334155;
    color: #CBD5E1;
    font-size: 10px;
    font-style: italic;
    max-width: 240px;
    white-space: normal;
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


# ============================================================
# DASHBOARD EN VIVO - LAYOUT REFACTORIZADO
# Filas Streamlit nativas para que el expander quede DEBAJO de cada empleado
# ============================================================
def _render_live_timeline(statuses):
    """
    Layout:
    - KPIs (1 iframe HTML)
    - Por cada país: header + timeline header + filas (cada empleado = 1 iframe + 1 expander Streamlit)
    """
    from core.incidents import calculate_duration_minutes
    from datetime import time as _t

    kpis = compute_daily_kpis(statuses)
    total = kpis["total"]
    incident_color = "#F97316"

    # ============================================================
    # SECCIÓN 1: KPIs (iframe único)
    # ============================================================
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

    legend_html = _build_legend([
        ("Trabajando", COLORS["working"]),
        ("Almuerzo", COLORS["lunch"]),
        ("Incidencia activa", incident_color),
        ("Hora extra", COLORS["overtime"]),
        ("Día libre", COLORS["day_off"]),
        ("Vacaciones / Permiso", COLORS["vacation"]),
    ])

    full_kpi_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        + DASHBOARD_CSS +
        '</head><body style="margin:0;padding:0;background:transparent;">'
        '<div class="stt-wrap">' + kpi_html + legend_html + '</div>'
        '</body></html>'
    )
    components.html(full_kpi_html, height=260, scrolling=False)

    # ============================================================
    # SECCIÓN 2: PRE-CALCULAR datos por país
    # ============================================================
    gt_statuses = [s for s in statuses if s["employee"].get("pais") == "GT"]
    ve_statuses = [s for s in statuses if s["employee"].get("pais") == "VE"]
    gt_hours = sum(s.get("scheduled_hours", 0) for s in gt_statuses if not s.get("is_day_off"))
    ve_hours = sum(s.get("scheduled_hours", 0) for s in ve_statuses if not s.get("is_day_off"))

    # Ordenar: managers/supervisores primero
    def _sort_key(s):
        emp = s["employee"]
        rol = emp.get("rol", "")
        priority = {"Manager": 0, "Supervisora": 1, "Supervisor": 1}.get(rol, 2)
        return (priority, emp.get("nombre", ""))

    gt_sorted = sorted(gt_statuses, key=_sort_key)
    ve_sorted = sorted(ve_statuses, key=_sort_key)

    # ============================================================
    # SECCIÓN 3: Renderizar cada país
    # ============================================================
    if gt_sorted:
        _render_country_section("GT", "Guatemala", "GT · 01", gt_hours, gt_sorted)

    if ve_sorted:
        _render_country_section("VE", "Venezuela", "VE · 02", ve_hours, ve_sorted)

    # Nota: el auto-refresh ya está activado en render() para el modo VIVO

    last_update_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        + DASHBOARD_CSS +
        '</head><body style="margin:0;padding:0;background:transparent;">'
        '<div class="stt-wrap"><div class="stt-last-update">'
        f'<span class="stt-live-dot"></span> EN VIVO · Última actualización: '
        f'{current_time_gt().strftime("%H:%M:%S")}'
        '</div></div></body></html>'
    )
    components.html(last_update_html, height=60, scrolling=False)


def _render_country_section(country_code: str, country_name: str, tag: str,
                             hours_value: float, sorted_statuses: list):
    """
    Renderiza un país: header + timeline header + por cada empleado [fila + expander].
    """
    # ---- Header del país (iframe) ----
    flag_img = flag_img_inline(country_code, size=18)
    country_header_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        + DASHBOARD_CSS +
        '</head><body style="margin:0;padding:0;background:transparent;">'
        '<div class="stt-wrap">'
        '<div class="stt-country-card">'
        '<div class="stt-country-header">'
        '<div>'
        f'<span class="stt-country-tag">{tag}</span>'
        f'<span class="stt-country-flag-mini">{flag_img}</span>'
        f'<span class="stt-country-title">{country_name}</span>'
        '</div>'
        '<div class="stt-sede-hours">'
        '<div class="stt-sede-hours-label">HORAS PROGRAMADAS</div>'
        f'<div class="stt-sede-hours-value">{hours_value:.0f}h</div>'
        '</div></div>'
        '</div></div></body></html>'
    )
    components.html(country_header_html, height=110, scrolling=False)

    # ---- Timeline header (las horas) ----
    timeline_hdr_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        + DASHBOARD_CSS +
        '</head><body style="margin:0;padding:0;background:transparent;">'
        '<div class="stt-wrap">'
        '<div class="stt-country-card" style="margin-top:-12px;padding-top:0;'
        'border-top:0;border-top-left-radius:0;border-top-right-radius:0;">'
        + render_timeline_header(TIMELINE_START_HOUR, TIMELINE_END_HOUR) +
        '</div></div></body></html>'
    )
    components.html(timeline_hdr_html, height=60, scrolling=False)

    # ---- Por cada empleado: fila visual + expander nativo ----
    for s in sorted_statuses:
        _render_employee_row_with_form(s)



def _render_employee_row_with_form(status_data: dict):
    """
    Fila completa de empleado:
    - Columna izquierda (95% ancho): iframe con la fila visual (nombre, avatar, segmentos, AHORA)
    - Columna derecha (5% ancho): botón 🚨 nativo de Streamlit
    Click en 🚨 → abre dialog popup con el form de incidencia.
    """
    from core.incidents import calculate_duration_minutes
    from datetime import time as _t
    from core.time_utils import parse_time as _parse_time

    emp = status_data["employee"]
    emp_id = int(emp["id"])
    emp_name = emp["nombre"]

    # Overlay de "AHORA" en esta fila (línea vertical)
    now_overlay_html = ""
    try:
        nt = current_time_gt()
        if _t(TIMELINE_START_HOUR, 0) <= nt <= _t(TIMELINE_END_HOUR, 0):
            from core.time_utils import time_to_position_pct
            pct = time_to_position_pct(nt, _t(TIMELINE_START_HOUR, 0), _t(TIMELINE_END_HOUR, 0))
            now_overlay_html = (
                f'<div style="position:absolute;top:0;bottom:0;left:220px;right:22px;'
                f'pointer-events:none;z-index:20;">'
                f'<div style="position:relative;height:100%;margin-left:22px;">'
                f'<div style="position:absolute;top:0;bottom:0;left:{pct}%;'
                f'width:1.5px;background:#0A0A0A;">'
                f'<div style="position:absolute;top:-2px;left:50%;transform:translateX(-50%);'
                f'background:#0A0A0A;color:#FFF;padding:3px 9px;border-radius:3px;'
                f"font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;"
                f'letter-spacing:1px;white-space:nowrap;">'
                f'AHORA · {nt.strftime("%I:%M %p").lstrip("0")}</div>'
                f'</div></div></div>'
            )
    except Exception:
        pass

    row_html_inner = render_employee_timeline_row(
        emp, status_data, "", TIMELINE_START_HOUR, TIMELINE_END_HOUR,
    )

    full_row_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        + DASHBOARD_CSS +
        '</head><body style="margin:0;padding:0;background:transparent;">'
        '<div class="stt-wrap">'
        '<div class="stt-country-card" style="border-top:0;border-radius:0;'
        'border-bottom:0;padding-top:0;padding-bottom:0;margin:0;">'
        '<div style="position:relative;">'
        + row_html_inner + now_overlay_html +
        '</div>'
        '</div></div></body></html>'
    )

    # Columnas: 1 grande para el iframe + 1 pequeña para el botón
    col_row, col_btn = st.columns([20, 1])

    with col_row:
        components.html(full_row_html, height=140, scrolling=False)

    active_inc = status_data.get("active_incident")

    with col_btn:
        st.markdown("<div style='padding-top:55px;'></div>", unsafe_allow_html=True)
        if active_inc:
            # Hay incidencia ACTIVA → botón "■" para terminarla
            button_clicked_terminate = st.button(
                "■",
                key=f"terminate_{emp_id}",
                help=f"Terminar incidencia activa de {emp_name}",
                type="primary",
            )
            button_clicked_open = False
        else:
            button_clicked_open = st.button(
                "🚨",
                key=f"open_dialog_{emp_id}",
                help=f"Registrar incidencia para {emp_name}",
            )
            button_clicked_terminate = False

    # ============================================================
    # ABRIR DIALOG SEGÚN BOTÓN PRESIONADO
    # ============================================================
    if button_clicked_open:
        _show_incident_dialog(emp_id, emp_name, status_data)
    if button_clicked_terminate:
        _show_terminate_dialog(emp_id, emp_name, status_data, active_inc)


@st.dialog("Terminar incidencia activa", width="large")
def _show_terminate_dialog_impl(emp_id: int, emp_name: str, status_data: dict, active_inc: dict):
    """Dialog para cerrar una incidencia activa con hora fin manual o ahora."""
    from core.incidents import calculate_duration_minutes, close_incident, get_active_incident_for_employee
    from core.time_utils import parse_time as _parse_time, current_time_gt

    st.markdown(f"### ■ Terminar incidencia de **{emp_name}**")

    if not active_inc:
        st.error("No se encontró la incidencia activa.")
        return

    icon = active_inc.get("icon", "❓")
    label = active_inc.get("label", "")
    color = active_inc.get("color", "#F97316")
    hi = active_inc.get("hora_inicio", "")
    dur = active_inc.get("duration_str", "")

    st.markdown(
        f'<div style="background:{color}15;border-left:4px solid {color};'
        f'padding:14px 18px;border-radius:0 6px 6px 0;margin:8px 0 16px 0;">'
        f'<div style="font-size:14px;color:#0A0A0A;">'
        f'<strong>{icon} {label}</strong> · Iniciada a las {hi} · '
        f'<strong style="color:{color};">{dur}</strong> en curso'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    now_hhmm = current_time_gt().strftime("%H:%M")

    # Botón "Terminar AHORA"
    if st.button(
        f"■  Terminar AHORA ({now_hhmm})",
        use_container_width=True,
        type="primary",
        key=f"term_now_{emp_id}",
    ):
        try:
            inc_obj = get_active_incident_for_employee(emp_id)
            if inc_obj is None:
                notify_error("La incidencia ya no existe.")
                return
            inc_id = inc_obj.get("id", "")
            result = close_incident(inc_id, current_user_display_name(), hora_fin=current_time_gt())
            if result["success"]:
                notify_success(
                    f"{emp_name} volvió. Duración: {format_duration(result['duration_minutes'])}",
                    title="Incidencia cerrada"
                )
                from core.sheets import invalidate_cache
                invalidate_cache()
                st.rerun()
            else:
                notify_error(result["message"])
        except Exception as e:
            notify_error(str(e))

    st.caption("— O terminar con hora fin manual —")

    hf_str = st.text_input(
        "Hora fin (HH:MM)",
        value=now_hhmm,
        max_chars=8,
        placeholder="08:00",
        key=f"term_hf_{emp_id}",
    )
    hf_parsed = _parse_time(hf_str)
    if hf_str and not hf_parsed:
        st.error(f"❌ Hora inválida: '{hf_str}'")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Cancelar", use_container_width=True, key=f"term_cancel_{emp_id}"):
            st.rerun()
    with col_b:
        if st.button(
            "✓ Terminar con esta hora",
            use_container_width=True,
            type="primary",
            disabled=not hf_parsed,
            key=f"term_submit_{emp_id}",
        ):
            try:
                inc_obj = get_active_incident_for_employee(emp_id)
                if inc_obj is None:
                    notify_error("La incidencia ya no existe.")
                    return
                inc_id = inc_obj.get("id", "")
                result = close_incident(inc_id, current_user_display_name(), hora_fin=hf_parsed)
                if result["success"]:
                    notify_success(
                        f"{emp_name} terminó {hf_parsed.strftime('%H:%M')}. Duración: {format_duration(result['duration_minutes'])}",
                        title="Incidencia cerrada"
                    )
                    from core.sheets import invalidate_cache
                    invalidate_cache()
                    st.rerun()
                else:
                    notify_error(result["message"])
            except Exception as e:
                notify_error(str(e))


def _show_terminate_dialog(emp_id: int, emp_name: str, status_data: dict, active_inc: dict):
    """Wrapper."""
    _show_terminate_dialog_impl(emp_id, emp_name, status_data, active_inc)


@st.dialog("Registrar incidencia", width="large")
def _show_incident_dialog_impl(emp_id: int, emp_name: str, status_data: dict):
    """
    Dialog popup nativo de Streamlit.
    Campos: tipo, hora inicio (texto), hora fin (texto), nota.
    Las horas se escriben directo con teclado: 07:15, 7:15, 715, etc.
    """
    from core.incidents import calculate_duration_minutes
    from core.time_utils import parse_time as _parse_time, current_time_gt

    st.markdown(f"### 🚨 Incidencia para **{emp_name}**")

    # Mostrar incidencias activas si las hay
    active_inc = status_data.get("active_incident")
    if active_inc:
        st.warning(
            f"⚠️ {emp_name} ya tiene una incidencia ACTIVA: "
            f"{active_inc['icon']} {active_inc['label']} desde {active_inc['hora_inicio']}. "
            f"Ciérrala primero o registra una nueva CERRADA con hora fin."
        )

    # Selector de tipo
    tipo = st.selectbox(
        "Tipo de incidencia",
        options=INCIDENT_TYPES,
        format_func=lambda x: f"{INCIDENT_ICONS.get(x, '?')}  {INCIDENT_LABELS.get(x, x)}",
        key=f"dlg_tipo_{emp_id}",
    )

    now_hhmm = current_time_gt().strftime("%H:%M")

    # CAMPOS DE TEXTO EDITABLES PARA LAS HORAS
    col_hi, col_hf = st.columns(2)
    with col_hi:
        hi_str = st.text_input(
            "Hora inicio (HH:MM)",
            value=now_hhmm,
            max_chars=8,
            placeholder="07:15",
            key=f"dlg_hi_{emp_id}",
            help="Escribe la hora en formato 24h. Ej: 07:15, 13:45",
        )
    with col_hf:
        hf_str = st.text_input(
            "Hora fin (HH:MM)",
            value=now_hhmm,
            max_chars=8,
            placeholder="08:00",
            key=f"dlg_hf_{emp_id}",
            help="Escribe la hora en formato 24h. Ej: 08:00, 14:30",
        )

    # Validar formato en vivo
    hi_parsed = _parse_time(hi_str)
    hf_parsed = _parse_time(hf_str)

    if hi_str and not hi_parsed:
        st.error(f"❌ Hora inicio inválida: '{hi_str}'. Usa formato HH:MM (ej. 07:15)")
    if hf_str and not hf_parsed:
        st.error(f"❌ Hora fin inválida: '{hf_str}'. Usa formato HH:MM (ej. 08:00)")

    nota = st.text_input(
        "Nota (opcional)",
        placeholder="Ej: Reportado por WhatsApp",
        max_chars=200,
        key=f"dlg_nota_{emp_id}",
    )

    # Vista previa de duración
    if hi_parsed and hf_parsed:
        preview_min = calculate_duration_minutes(hi_parsed, hf_parsed)
        if preview_min > 0:
            st.success(f"✅ Duración calculada: **{format_duration(preview_min)}** ({preview_min} min)")
        else:
            st.warning("⚠️ La hora fin debe ser posterior a la hora inicio.")

    st.divider()

    # ============================================================
    # BOTÓN: ▶ INICIAR AHORA (sin hora fin, queda ACTIVA)
    # ============================================================
    if not active_inc:  # Solo si NO hay incidencia activa
        if st.button(
            f"▶  Iniciar AHORA ({current_time_gt().strftime('%H:%M')})  ·  sin hora fin (queda activa)",
            use_container_width=True,
            key=f"dlg_start_now_{emp_id}",
            help="Inicia una incidencia con la hora actual. Después la cierras con 'Terminar'.",
        ):
            try:
                result = register_incident(
                    employee_id=emp_id,
                    employee_name=emp_name,
                    tipo=tipo,
                    hora_inicio=current_time_gt(),
                    hora_fin=None,  # ACTIVA
                    nota=nota,
                    registered_by=current_user_display_name(),
                )
                if result["success"]:
                    notify_success(
                        f"{emp_name} · {INCIDENT_LABELS.get(tipo)} · iniciada a las {current_time_gt().strftime('%H:%M')}",
                        title="Incidencia activa"
                    )
                    from core.sheets import invalidate_cache
                    invalidate_cache()
                    st.rerun()
                else:
                    notify_error(result["message"])
            except Exception as e:
                notify_error(str(e))

        st.caption("— O registrar con hora fin manual (cerrada) —")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Cancelar", use_container_width=True, key=f"dlg_cancel_{emp_id}"):
            st.rerun()

    with col_b:
        submit_disabled = not (hi_parsed and hf_parsed)
        if st.button(
            "✓ Registrar (con hora fin)",
            use_container_width=True,
            type="primary",
            disabled=submit_disabled,
            key=f"dlg_submit_{emp_id}",
        ):
            try:
                result = register_incident(
                    employee_id=emp_id,
                    employee_name=emp_name,
                    tipo=tipo,
                    hora_inicio=hi_parsed,
                    hora_fin=hf_parsed,
                    nota=nota,
                    registered_by=current_user_display_name(),
                )
                if result["success"]:
                    notify_success(
                        f"{emp_name} · {INCIDENT_LABELS.get(tipo)} · {format_duration(result['duracion_min'])}",
                        title="Incidencia registrada"
                    )
                    from core.sheets import invalidate_cache
                    invalidate_cache()
                    st.rerun()
                else:
                    notify_error(result["message"])
            except Exception as e:
                notify_error(str(e))


def _show_incident_dialog(emp_id: int, emp_name: str, status_data: dict):
    """Wrapper. Streamlit dialog API."""
    _show_incident_dialog_impl(emp_id, emp_name, status_data)
