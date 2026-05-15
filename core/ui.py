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
    </style>
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
