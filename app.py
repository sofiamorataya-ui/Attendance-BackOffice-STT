"""
app.py — Attendance BackOffice STT
Entry point principal. Maneja login + routing entre módulos.
"""
import streamlit as st
from core.config import APP_NAME, COMPANY, APP_VERSION
from core.ui import inject_css, render_top_bar
from core.auth import (
    is_authenticated, login, logout, current_user,
)
from modules import dashboard_live, admin_seed


# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


# ============================================================
# PANTALLA DE LOGIN
# ============================================================
def render_login():
    """Pantalla de login centrada estilo STT."""
    # Centrado vertical y horizontal con columnas
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 80px 0 24px 0;">
                <div style="
                    display: inline-block;
                    background: #DC2626;
                    color: white;
                    padding: 14px 24px;
                    border-radius: 8px;
                    font-weight: 800;
                    letter-spacing: 4px;
                    font-size: 22px;
                    margin-bottom: 24px;
                ">STT</div>
                <h1 style="
                    font-family: 'Inter Tight', sans-serif;
                    font-size: 36px;
                    font-weight: 700;
                    color: #0A0A0A;
                    letter-spacing: -1px;
                    margin-bottom: 6px;
                ">Attendance BackOffice</h1>
                <p style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 11px;
                    color: #64748B;
                    letter-spacing: 1.5px;
                    text-transform: uppercase;
                ">STT Logistics Group</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(
                '<div style="padding: 8px 4px;">'
                '<div style="font-size: 11px; font-weight: 700; letter-spacing: 2px; '
                'text-transform: uppercase; color: #DC2626; margin-bottom: 16px;">— ACCESO</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            username = st.text_input(
                "Usuario", placeholder="sofi / evelyn",
                key="login_username", label_visibility="visible",
            )
            password = st.text_input(
                "Contraseña", type="password",
                key="login_password", label_visibility="visible",
            )

            if st.button("INGRESAR", use_container_width=True, type="primary"):
                ok, msg = login(username, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown(
            f'<div style="text-align: center; margin-top: 20px; '
            f'font-family: \'JetBrains Mono\', monospace; font-size: 10px; '
            f'color: #94A3B8; letter-spacing: 1px;">v{APP_VERSION} · {COMPANY}</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# SIDEBAR DE NAVEGACIÓN
# ============================================================
def render_sidebar():
    """Sidebar oscuro con navegación entre módulos."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 8px 0 24px 0; text-align: center;">
                <div style="
                    display: inline-block;
                    background: #DC2626;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 800;
                    letter-spacing: 3px;
                    font-size: 16px;
                ">STT</div>
                <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 9px;
                    color: #64748B;
                    letter-spacing: 1.5px;
                    margin-top: 8px;
                ">ATTENDANCE · BACKOFFICE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Menú principal
        modules_map = {
            "🟢 Asistencia en Vivo": "dashboard_live",
            "📋 Registro Asistencia": "attendance_log",
            "⏱️ Horas Extras": "overtime",
            "🏖️ Vacaciones": "vacations",
            "🚨 Permisos": "exceptions",
            "🇺🇸 Feriados US": "holidays",
            "🎂 Cumpleaños": "birthdays",
            "📅 Antigüedad": "tenure",
            "🛠️ Setup Inicial": "admin_seed",
        }

        choice = st.radio(
            "MENÚ",
            list(modules_map.keys()),
            label_visibility="collapsed",
        )

        st.session_state["current_module"] = modules_map[choice]

        st.divider()

        # Usuario actual + logout
        user = current_user()
        st.markdown(
            f"""
            <div style="padding: 8px 0;">
                <div style="font-size: 9px; letter-spacing: 1.5px;
                            color: #64748B; margin-bottom: 4px;">SESIÓN</div>
                <div style="font-size: 13px; font-weight: 600;
                            color: #FFFFFF;">{user['nombre_completo']}</div>
                <div style="font-size: 10px; font-family: 'JetBrains Mono', monospace;
                            color: #DC2626; margin-top: 2px;
                            text-transform: uppercase; letter-spacing: 1px;">
                    {user['rol']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()


# ============================================================
# ROUTER PRINCIPAL
# ============================================================
def route():
    """Renderiza el módulo activo."""
    user = current_user()
    module = st.session_state.get("current_module", "dashboard_live")

    # Mapeo de los nombres legibles para el top bar
    section_names = {
        "dashboard_live": "PANEL EJECUTIVO",
        "attendance_log": "REGISTRO DE ASISTENCIA",
        "overtime": "HORAS EXTRAS",
        "vacations": "VACACIONES",
        "exceptions": "PERMISOS Y AUSENCIAS",
        "holidays": "FERIADOS · US",
        "birthdays": "CUMPLEAÑOS",
        "tenure": "ANTIGÜEDAD",
        "admin_seed": "SETUP · ADMINISTRADOR",
    }

    render_top_bar(
        section_name=section_names.get(module, "PANEL"),
        user_name=user["nombre_completo"],
        user_role=user["rol"].upper(),
    )

    # Routing
    if module == "dashboard_live":
        dashboard_live.render()
    elif module == "admin_seed":
        admin_seed.render()
    else:
        # Placeholders de los módulos que vienen en próximas entregas
        from core.ui import render_page_title
        titles = {
            "attendance_log": ("REGISTRO", "Asistencia diaria"),
            "overtime": ("REPORTES", "Horas Extras"),
            "vacations": ("GESTIÓN", "Vacaciones"),
            "exceptions": ("REGISTRO", "Permisos y Ausencias"),
            "holidays": ("CALENDARIO", "Feriados de Estados Unidos"),
            "birthdays": ("EQUIPO", "Cumpleaños"),
            "tenure": ("EQUIPO", "Antigüedad en la empresa"),
        }
        eyebrow, title = titles.get(module, ("MÓDULO", "En construcción"))
        render_page_title(eyebrow=eyebrow, title=title)
        st.info("🚧 Este módulo se completa en próximas entregas.")


# ============================================================
# MAIN
# ============================================================
if not is_authenticated():
    render_login()
else:
    render_sidebar()
    route()
