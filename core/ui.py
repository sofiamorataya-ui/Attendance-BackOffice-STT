"""
core/ui.py
Componentes UI reutilizables. Todos devuelven HTML/markdown listo para st.markdown.
"""
import streamlit as st
from core.config import COLORS, FLAGS


def inject_css():
    """Inyecta CSS global con la identidad visual STT."""
    css = """
    <style>
    /* === Fuentes === */
    @import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter Tight', -apple-system, sans-serif !important;
    }

    /* === Twemoji autoconvertido === */
    img.emoji {
        height: 1.2em;
        width: 1.2em;
        margin: 0 0.05em;
        vertical-align: -0.2em;
        display: inline-block;
    }

    /* === Fondo general === */
    .stApp {
        background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
    }

    /* === Header bar STT (top de cada vista) === */
    .stt-header {
        background: #0F172A;
        color: #FFFFFF;
        padding: 14px 28px;
        border-radius: 0;
        margin: -16px -16px 24px -16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid #DC2626;
        font-family: 'Inter Tight', sans-serif;
    }
    .stt-header-title {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #94A3B8;
    }
    .stt-header-user {
        font-size: 13px;
        font-weight: 500;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .stt-header-user-badge {
        background: #DC2626;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }

    /* === Section labels (--- VISTA DIARIA estilo) === */
    .stt-eyebrow {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #DC2626;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stt-eyebrow::before {
        content: "—";
        color: #DC2626;
        font-weight: 900;
    }

    /* === Big title === */
    .stt-title {
        font-family: 'Inter Tight', sans-serif;
        font-size: 44px;
        font-weight: 700;
        color: #0A0A0A;
        letter-spacing: -1.5px;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .stt-subtitle {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 24px;
    }

    /* === KPI Cards === */
    .stt-kpi-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
    }
    .stt-kpi {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 20px 22px;
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
        font-size: 42px;
        font-weight: 700;
        color: #0A0A0A;
        line-height: 1;
        letter-spacing: -2px;
    }
    .stt-kpi-value-sub {
        font-size: 18px;
        color: #94A3B8;
        font-weight: 400;
        margin-left: 4px;
    }
    .stt-kpi-foot {
        margin-top: 12px;
        font-size: 12px;
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

    /* === Reference legend === */
    .stt-legend {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px 18px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 24px;
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

    /* === Sede headers === */
    .stt-sede-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-bottom: 16px;
        overflow: hidden;
    }
    .stt-sede-header {
        padding: 14px 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E2E8F0;
        background: #FFFFFF;
    }
    .stt-sede-tag {
        display: inline-block;
        background: #F1F5F9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        margin-right: 12px;
    }
    .stt-sede-title {
        display: inline-block;
        font-size: 18px;
        font-weight: 700;
        color: #0A0A0A;
    }
    .stt-sede-hours {
        text-align: right;
    }
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

    /* === Avatar con bandera === */
    .stt-avatar-wrap {
        display: inline-flex;
        align-items: center;
        gap: 10px;
    }
    .stt-flag {
        font-size: 18px;
        line-height: 1;
    }
    .stt-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 11px;
        color: #334155;
        letter-spacing: 0.5px;
    }
    .stt-emp-name {
        font-weight: 600;
        color: #0A0A0A;
        font-size: 14px;
    }
    .stt-emp-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #94A3B8;
    }

    /* === Botones === */
    .stButton > button {
        background: #DC2626 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px !important;
        padding: 10px 20px !important;
        transition: background 0.15s ease !important;
    }
    .stButton > button:hover {
        background: #991B1B !important;
    }

    /* === Inputs (login) === */
    .stTextInput > div > div > input {
        border-radius: 6px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 12px !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #DC2626 !important;
        box-shadow: 0 0 0 1px #DC2626 !important;
    }

    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #FFFFFF;
        border-radius: 8px;
        padding: 6px;
        border: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        background: #0F172A !important;
        color: #FFFFFF !important;
    }

    /* === Hide Streamlit chrome === */
    #MainMenu, footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    /* ============================================================
       TIMELINE — Dashboard "Asistencia en Vivo"
       ============================================================ */
    .stt-country-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin-bottom: 16px;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }

    /* Header del bloque por país */
    .stt-country-header {
        padding: 16px 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E2E8F0;
    }
    .stt-country-tag {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        margin-right: 12px;
    }
    .stt-country-title {
        display: inline-block;
        font-size: 18px;
        font-weight: 700;
        color: #0A0A0A;
        vertical-align: middle;
    }
    .stt-country-flag-big {
        font-size: 22px;
        line-height: 1;
    }

    /* Headers de columnas del timeline (5am, 6, 7...) */
    .stt-timeline-header {
        display: grid;
        grid-template-columns: 200px 1fr;
        padding: 10px 22px;
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
    .stt-timeline-hour-mark sub {
        font-size: 8px;
        opacity: 0.7;
    }

    /* Filas de empleados */
    .stt-emp-row {
        display: grid;
        grid-template-columns: 200px 1fr;
        padding: 14px 22px;
        border-bottom: 1px solid #F1F5F9;
        align-items: center;
        min-height: 56px;
    }
    .stt-emp-row:last-child {
        border-bottom: none;
    }
    .stt-emp-row:hover {
        background: #FAFBFC;
    }

    /* Avatar grupo izquierdo */
    .stt-emp-info {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .stt-flag-pill {
        font-size: 16px;
        line-height: 1;
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
    .stt-emp-data {
        line-height: 1.3;
    }
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

    /* Track (línea horizontal donde van los segmentos) */
    .stt-track {
        position: relative;
        height: 28px;
        background: transparent;
    }
    /* Marcas verticales sutiles cada hora */
    .stt-track-grid {
        position: absolute;
        top: 0;
        bottom: 0;
        width: 1px;
        background: #F1F5F9;
    }

    /* Segmentos de horario */
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

    .stt-segment-label-left {
        text-align: left;
    }
    .stt-segment-label-right {
        margin-left: auto;
        text-align: right;
    }

    /* Pill de estado "Día libre" para filas sin segmentos */
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

    /* Línea AHORA vertical */
    .stt-now-line {
        position: absolute;
        top: -22px;
        bottom: -2px;
        width: 1.5px;
        background: #0A0A0A;
        z-index: 10;
        pointer-events: none;
    }
    .stt-now-badge {
        position: absolute;
        top: -22px;
        transform: translateX(-50%);
        background: #0A0A0A;
        color: #FFFFFF;
        padding: 3px 8px;
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

    /* Última actualización */
    .stt-last-update {
        text-align: right;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: #94A3B8;
        letter-spacing: 0.5px;
        margin-top: 8px;
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

    /* === Sidebar === */
    [data-testid="stSidebar"] {
        background: #0F172A;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: #94A3B8 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
    }

    /* ============================================================
       RESPONSIVE — top bar, título, login
       ============================================================ */

    /* TV 4K (≥2560px): texto más grande */
    @media (min-width: 2560px) {
        .stt-title { font-size: 56px; }
        .stt-subtitle { font-size: 13px; }
        .stt-eyebrow { font-size: 13px; }
        .stt-header-title { font-size: 15px; }
        .stt-header-user { font-size: 15px; }
    }

    /* Tablet (≤1023px) */
    @media (max-width: 1023px) {
        .stt-title { font-size: 36px; }
        .stt-header { padding: 12px 20px; }
        .stt-header-title { font-size: 12px; letter-spacing: 1.5px; }
    }

    /* Smartphone (≤767px) */
    @media (max-width: 767px) {
        .stt-title { font-size: 28px; letter-spacing: -1px; }
        .stt-subtitle { font-size: 10px; }
        .stt-eyebrow { font-size: 10px; letter-spacing: 2px; }
        .stt-header {
            padding: 10px 16px;
            margin: -16px -8px 16px -8px;
        }
        .stt-header-title {
            font-size: 11px;
            letter-spacing: 1.2px;
        }
        .stt-header-user { font-size: 11px; gap: 8px; }
        .stt-header-user-badge {
            font-size: 9px;
            padding: 3px 7px;
        }
    }

    /* Smartphone pequeño (≤480px) */
    @media (max-width: 480px) {
        .stt-title { font-size: 24px; }
        .stt-header-title { display: none; }
    }
    </style>

    <!-- Twemoji: convierte emojis nativos en imágenes (resuelve banderas en Windows) -->
    <script src="https://cdn.jsdelivr.net/npm/@twemoji/api@latest/dist/twemoji.min.js" crossorigin="anonymous"></script>
    <script>
    (function() {
        function runTwemoji() {
            if (typeof twemoji !== 'undefined') {
                twemoji.parse(document.body, {
                    folder: 'svg',
                    ext: '.svg',
                    base: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/'
                });
            }
        }
        // Run inmediatamente y observar cambios del DOM (Streamlit re-renderiza)
        runTwemoji();
        setTimeout(runTwemoji, 200);
        setTimeout(runTwemoji, 800);

        var observer = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length > 0) {
                    runTwemoji();
                    break;
                }
            }
        });
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
        }
    })();
    </script>
    """
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# COMPONENTES
# ============================================================
def render_top_bar(section_name: str, user_name: str, user_role: str):
    """Barra superior negra estilo de la imagen 1."""
    html = f"""
    <div class="stt-header">
        <div class="stt-header-title">{section_name}</div>
        <div class="stt-header-user">
            <span>{user_name}</span>
            <span class="stt-header-user-badge">{user_role}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_page_title(eyebrow: str, title: str, subtitle: str = ""):
    """Encabezado tipo 'VISTA DIARIA / Asistencia / Viernes 15 de Mayo, 2026'."""
    html = f"""
    <div class="stt-eyebrow">{eyebrow}</div>
    <div class="stt-title">{title}</div>
    """
    if subtitle:
        html += f'<div class="stt-subtitle">{subtitle}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_card(label: str, value: str, value_sub: str = "", foot_text: str = "", foot_color: str = COLORS["working"]) -> str:
    """Devuelve HTML de una sola KPI card. Para usar dentro de stt-kpi-row."""
    sub_html = f'<span class="stt-kpi-value-sub">{value_sub}</span>' if value_sub else ""
    foot_html = ""
    if foot_text:
        foot_html = f"""
        <div class="stt-kpi-foot">
            <span class="stt-kpi-dot" style="background:{foot_color}"></span>
            {foot_text}
        </div>
        """
    return f"""
    <div class="stt-kpi">
        <div class="stt-kpi-label">{label}</div>
        <div class="stt-kpi-value">{value}{sub_html}</div>
        {foot_html}
    </div>
    """


def render_kpi_row(cards: list[str]):
    """Renderiza una fila de KPI cards."""
    html = '<div class="stt-kpi-row">' + "".join(cards) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_legend(items: list[tuple[str, str]]):
    """
    Renderiza la barra de leyenda de colores.
    items: lista de (etiqueta, color)
    """
    swatches = "".join([
        f'<span class="stt-legend-item"><span class="stt-legend-swatch" style="background:{color}"></span>{label}</span>'
        for label, color in items
    ])
    html = f"""
    <div class="stt-legend">
        <span class="stt-legend-label">REFERENCIA</span>
        {swatches}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_employee_avatar(initials: str, color_bg: str, country_code: str, name: str, meta: str = "") -> str:
    """Devuelve HTML de un avatar con bandera + iniciales + nombre + meta."""
    flag = FLAGS.get(country_code, "")
    return f"""
    <div class="stt-avatar-wrap">
        <span class="stt-flag">{flag}</span>
        <span class="stt-avatar" style="background:{color_bg}">{initials}</span>
        <span>
            <div class="stt-emp-name">{name}</div>
            <div class="stt-emp-meta">{meta}</div>
        </span>
    </div>
    """


def render_sede_header(tag: str, title: str, hours_label: str, hours_value: str):
    """Encabezado de cada bloque tipo 'SEDE 01 / Tienda 7ma Avenida / HORAS PROGRAMADAS 18h'."""
    html = f"""
    <div class="stt-sede-header">
        <div>
            <span class="stt-sede-tag">{tag}</span>
            <span class="stt-sede-title">{title}</span>
        </div>
        <div class="stt-sede-hours">
            <div class="stt-sede-hours-label">{hours_label}</div>
            <div class="stt-sede-hours-value">{hours_value}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# COMPONENTES DEL TIMELINE (Dashboard Asistencia en Vivo)
# ============================================================
def render_timeline_header(start_hour: int = 5, end_hour: int = 21):
    """
    Fila de horas (5am, 6, 7... 9pm) con marcas alineadas exactamente
    a las divisiones verticales del track.
    """
    marks = []
    total_hours = end_hour - start_hour
    for h in range(start_hour, end_hour + 1):
        pct = ((h - start_hour) / total_hours) * 100
        if h == start_hour:
            label = f"{h if h < 12 else h-12}<sub>{'am' if h < 12 else 'pm'}</sub>"
        elif h == end_hour:
            display = h if h <= 12 else h - 12
            label = f"{display}<sub>{'am' if h < 12 else 'pm'}</sub>"
        elif h == 12:
            label = "12<sub>pm</sub>"
        else:
            display = h if h < 12 else h - 12
            label = str(display)

        marks.append(
            f'<span class="stt-timeline-hour-mark" style="left:{pct}%">{label}</span>'
        )

    return f"""
    <div class="stt-timeline-header">
        <div class="stt-timeline-header-left">PERSONAL</div>
        <div class="stt-timeline-hours">{"".join(marks)}</div>
    </div>
    """


def render_grid_lines(start_hour: int = 5, end_hour: int = 21) -> str:
    """
    Líneas verticales en CADA hora exacta del track.
    Más visibles que antes para que se vea bien la grilla horaria.
    """
    lines = []
    total = end_hour - start_hour
    for h in range(start_hour, end_hour + 1):
        pct = ((h - start_hour) / total) * 100
        # Línea más marcada en horas pares y mediodía
        is_emphasis = (h % 3 == 0) or (h == 12)
        klass = "stt-track-grid stt-track-grid-emphasis" if is_emphasis else "stt-track-grid"
        lines.append(f'<div class="{klass}" style="left:{pct}%"></div>')
    return "".join(lines)


def render_timeline_now_overlay(now_time, start_hour: int = 5, end_hour: int = 21) -> str:
    """
    Devuelve HTML del overlay 'AHORA · HH:MM' sobre el timeline.
    String vacío si la hora actual está fuera del rango.
    """
    cur_min = now_time.hour * 60 + now_time.minute
    start_min = start_hour * 60
    end_min = end_hour * 60

    if cur_min < start_min or cur_min > end_min:
        return ""

    pct = ((cur_min - start_min) / (end_min - start_min)) * 100
    label = now_time.strftime("%I:%M %p").lstrip("0")

    return f"""
    <div class="stt-now-badge" style="left:{pct}%">AHORA · {label}</div>
    <div class="stt-now-line" style="left:{pct}%">
        <div class="stt-now-dot"></div>
    </div>
    """


def render_employee_timeline_row(
    employee: dict,
    status_data: dict,
    now_overlay_html: str = "",
    start_hour: int = 5,
    end_hour: int = 21,
) -> str:
    """
    Devuelve HTML de UNA fila de empleado con su barra de horario.
    Usa <img> SVG directo de Twemoji (no depende de JS).
    """
    from core.flags import flag_img_inline

    flag_html = flag_img_inline(employee.get("pais", ""), size=14)
    initials = employee.get("iniciales", "??")
    avatar_color = employee.get("color_avatar", "#F1F5F9")
    name = employee.get("nombre", "")

    # Meta line: "9:00 AM · 7:00 PM · 9h" o "Día libre"
    if status_data["is_day_off"] or status_data["entrada"] is None:
        meta = status_data["status_label"]
    else:
        ent = status_data["entrada"].strftime("%I:%M %p").lstrip("0")
        sal = status_data["salida"].strftime("%I:%M %p").lstrip("0")
        hrs = status_data["scheduled_hours"]
        meta = f"{ent} · {sal} · {hrs:g}h"

    # Construir segmentos
    segments_html = ""
    if status_data["timeline_segments"]:
        # Empleado con horario hoy
        for seg in status_data["timeline_segments"]:
            seg_class = f"stt-segment-{seg['type']}"
            width = seg["end_pct"] - seg["start_pct"]

            label_html = ""
            if seg["label_left"]:
                label_html += f'<span class="stt-segment-label-left">{seg["label_left"]}</span>'
            if seg["type"] == "lunch":
                label_html += '<span class="stt-segment-label-left">ALMUERZO</span>'
            if seg["label_right"]:
                label_html += f'<span class="stt-segment-label-right">{seg["label_right"]}</span>'

            segments_html += (
                f'<div class="stt-segment {seg_class}" '
                f'style="left:{seg["start_pct"]}%; width:{width}%;">'
                f'{label_html}</div>'
            )
    else:
        # Sin segmentos: día libre, vacaciones, permiso, etc.
        from core.attendance_engine import Status
        status = status_data["status"]
        # Para vacaciones/permisos/incapacidad → barra completa del día
        if status in (Status.VACATION, Status.PERMIT, Status.SICK):
            type_map = {Status.VACATION: "vacation", Status.PERMIT: "permit", Status.SICK: "sick"}
            label_map = {Status.VACATION: "VACACIONES", Status.PERMIT: "PERMISO", Status.SICK: "INCAPACIDAD"}
            segments_html = (
                f'<div class="stt-segment stt-segment-{type_map[status]}" '
                f'style="left:0%; width:100%;">'
                f'<span class="stt-segment-label-left">{label_map[status]}</span></div>'
            )
        # Día libre → barra rayada con patrón diagonal (estilo Ismael Palma)
        elif status == Status.DAY_OFF:
            segments_html = '<div class="stt-segment-dayoff">DÍA LIBRE</div>'
        # Ausente → barra rayada con tinte rojo
        elif status == Status.ABSENT:
            segments_html = '<div class="stt-segment-absent">AUSENTE</div>'
        # Otros estados → pill clásico
        else:
            color = status_data["status_color"]
            label = status_data["status_label"].upper()
            segments_html = (
                f'<span class="stt-status-pill" '
                f'style="background:{status_data["status_bg"]}; color:{color};">'
                f'{label}</span>'
            )

    grid_html = render_grid_lines(start_hour, end_hour)

    # ============================================================
    # OVERLAYS DE INCIDENCIAS DEL DÍA (todas, activas + cerradas)
    # Cada una se pinta con el color de su tipo entre hora_inicio y hora_fin
    # ============================================================
    incident_overlay = ""
    incident_meta_extra = ""
    incident_badge = ""
    from core.time_utils import parse_time, time_to_position_pct, current_time_gt
    from datetime import time as _t

    day_start = _t(start_hour, 0)
    day_end = _t(end_hour, 0)

    overlays_html_parts = []
    day_incidents = status_data.get("day_incidents") or []
    for inc in day_incidents:
        try:
            hi = parse_time(inc.get("hora_inicio", ""))
            hf = parse_time(inc.get("hora_fin", ""))
            if not hi:
                continue
            if not hf:
                hf = current_time_gt()  # ACTIVA sin fin → hasta ahora
            start_pct = time_to_position_pct(hi, day_start, day_end)
            end_pct = time_to_position_pct(hf, day_start, day_end)
            if end_pct < start_pct:
                end_pct = start_pct + 0.5
            start_pct = max(start_pct, 0)
            end_pct = min(end_pct, 100)
            width = max(end_pct - start_pct, 1.5)

            color = inc.get("color", "#F97316")
            icon = inc.get("icon", "❓")
            label = inc.get("label", "").upper()
            is_active = str(inc.get("estado", "")).upper() == "ACTIVA"
            border_style = "1.5px solid " + color
            if is_active:
                border_style = "2px solid " + color

            # Calcular duración para el tooltip
            from core.incidents import calculate_duration_minutes, format_duration
            dur_min = 0
            if hi and hf:
                dur_min = calculate_duration_minutes(hi, hf)
            dur_str = format_duration(dur_min) if dur_min > 0 else "—"

            # Strings para el tooltip
            hi_display = hi.strftime("%H:%M") if hi else "?"
            hf_display = hf.strftime("%H:%M") if hf else "ahora"
            label_pretty = inc.get("label", "")
            nota = inc.get("nota", "") or ""
            estado_pretty = "ACTIVA · en curso" if is_active else "Cerrada"

            # Tooltip nativo HTML (atributo title) — funciona en TODOS los navegadores
            tooltip_lines = [
                f"{inc.get('icon', '')} {label_pretty}",
                f"Inicio: {hi_display}",
                f"Fin: {hf_display}",
                f"Duración: {dur_str}",
                f"Estado: {estado_pretty}",
            ]
            if nota:
                tooltip_lines.append(f"Nota: {nota}")
            tooltip_text = "\n".join(tooltip_lines).replace('"', "&quot;")

            # Tooltip custom CSS con data-attributes (más bonito)
            data_attrs = (
                f'data-inc-icon="{inc.get("icon", "")}" '
                f'data-inc-label="{label_pretty}" '
                f'data-inc-hi="{hi_display}" '
                f'data-inc-hf="{hf_display}" '
                f'data-inc-dur="{dur_str}" '
                f'data-inc-estado="{estado_pretty}"'
            )

            overlays_html_parts.append(
                f'<div class="stt-incident-overlay" '
                f'title="{tooltip_text}" '
                f'{data_attrs} '
                f'style="left:{start_pct}%; width:{width}%; '
                f'background:repeating-linear-gradient(45deg, {color}, '
                f'{color} 6px, {color}DD 6px, {color}DD 12px); '
                f'border:{border_style};">'
                f'<span class="stt-incident-label">'
                f'{icon} {label}'
                f'</span>'
                f'<div class="stt-incident-tooltip">'
                f'<div class="stt-tt-title">{inc.get("icon", "")} {label_pretty}</div>'
                f'<div class="stt-tt-row"><span class="stt-tt-k">Inicio:</span> <span class="stt-tt-v">{hi_display}</span></div>'
                f'<div class="stt-tt-row"><span class="stt-tt-k">Fin:</span> <span class="stt-tt-v">{hf_display}</span></div>'
                f'<div class="stt-tt-row"><span class="stt-tt-k">Duración:</span> <span class="stt-tt-v stt-tt-dur">{dur_str}</span></div>'
                f'<div class="stt-tt-row"><span class="stt-tt-k">Estado:</span> <span class="stt-tt-v">{estado_pretty}</span></div>'
                + (f'<div class="stt-tt-note">{nota}</div>' if nota else '') +
                f'</div>'
                f'</div>'
            )
        except Exception:
            continue

    incident_overlay = "".join(overlays_html_parts)

    # Badge al lado del nombre si hay AL MENOS UNA activa
    active_inc = status_data.get("active_incident")
    if active_inc:
        incident_badge = (
            f'<span class="stt-incident-badge" '
            f'style="background:{active_inc["color"]};color:#FFFFFF;">'
            f'🚨 {active_inc["label"].upper()}'
            f'</span>'
        )
        incident_meta_extra = (
            f' <span style="color:{active_inc["color"]};font-weight:600;">'
            f'· {active_inc["icon"]} {active_inc["duration_str"]}'
            f'</span>'
        )

    return f"""
    <div class="stt-emp-row">
        <div class="stt-emp-info">
            <span class="stt-flag-pill">{flag_html}</span>
            <span class="stt-avatar-circle" style="background:{avatar_color}">{initials}</span>
            <div class="stt-emp-data">
                <div class="stt-emp-data-name">{name}{incident_badge}</div>
                <div class="stt-emp-data-sub">{meta}{incident_meta_extra}</div>
            </div>
        </div>
        <div class="stt-track">
            {grid_html}
            {segments_html}
            {incident_overlay}
            {now_overlay_html}
        </div>
    </div>
    """


def render_country_block(country_code: str, country_name: str, tag: str,
                          hours_value: str, header_html: str,
                          employee_rows_html: str) -> str:
    """Encapsula un bloque por país (GT / VE) con header + filas. Bandera mini (no gigante)."""
    from core.flags import flag_img_inline
    flag_html = flag_img_inline(country_code, size=18)
    return f"""
    <div class="stt-country-card">
        <div class="stt-country-header">
            <div>
                <span class="stt-country-tag">{tag}</span>
                <span class="stt-country-flag-mini">{flag_html}</span>
                <span class="stt-country-title">{country_name}</span>
            </div>
            <div class="stt-sede-hours">
                <div class="stt-sede-hours-label">HORAS PROGRAMADAS</div>
                <div class="stt-sede-hours-value">{hours_value}</div>
            </div>
        </div>
        {header_html}
        {employee_rows_html}
    </div>
    """
