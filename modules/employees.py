"""
modules/employees.py
Gestión de empleados: crear, editar, desactivar.
Maneja datos maestros + horarios semanales.
"""
import streamlit as st
import pandas as pd
from datetime import date, time
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import (
    read_worksheet, append_row, get_worksheet, invalidate_cache,
    WORKSHEET_HEADERS,
)
from core.config import WS_EMPLOYEES, WS_SCHEDULES, DAYS_ES, DAYS_FULL_ES, REFRESH_OTHER_TABS
from core.time_utils import today_gt, now_gt, parse_date, parse_time
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error


AVATAR_COLORS = [
    "#FEE2E2", "#FED7AA", "#FEF3C7", "#DCFCE7", "#CFFAFE",
    "#DBEAFE", "#E0E7FF", "#F3E8FF", "#FCE7F3", "#FEE2E2",
]


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="employees_refresh")

    render_page_title(
        eyebrow="ADMINISTRACIÓN",
        title="Empleados",
        subtitle="Gestión del equipo BackOffice",
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    tab_list, tab_new, tab_edit, tab_schedule = st.tabs([
        "👥  Directorio",
        "➕  Nuevo empleado",
        "✏️  Editar empleado",
        "📅  Editar horarios",
    ])

    with tab_list:
        _render_directory(employees_df)

    with tab_new:
        _render_new_employee_form(employees_df)

    with tab_edit:
        _render_edit_form(employees_df)

    with tab_schedule:
        _render_schedule_editor(employees_df)


def _render_directory(employees_df: pd.DataFrame):
    """Lista del directorio del equipo."""
    if employees_df.empty:
        st.info("📭 No hay empleados.")
        return

    # Mostrar activos primero
    active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()
    inactive = employees_df[
        ~employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#16A34A;margin:16px 0 12px 0;">'
        f'— ACTIVOS · {len(active)}</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for _, emp in active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        color = emp.get("color_avatar", "#F1F5F9")
        iniciales = emp.get("iniciales", "??")
        cumple = parse_date(str(emp.get("cumpleanos", "")))
        ingreso = parse_date(str(emp.get("fecha_ingreso", "")))

        cumple_str = cumple.strftime("%d/%m") if cumple else "—"
        ingreso_str = ingreso.strftime("%d/%m/%Y") if ingreso else "—"

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;
                    padding:18px;display:flex;align-items:center;gap:16px;margin-bottom:8px;">
            <span style="font-size:22px;">{flag}</span>
            <span style="width:44px;height:44px;border-radius:50%;background:{color};
                         display:inline-flex;align-items:center;justify-content:center;
                         font-weight:700;font-size:14px;color:#475569;">{iniciales}</span>
            <div style="flex:1;min-width:160px;">
                <div style="font-size:15px;font-weight:700;color:#0A0A0A;">{emp["nombre"]}</div>
                <div style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                            margin-top:2px;letter-spacing:0.3px;">
                    ID {emp["id"]} · {emp.get("rol", "")} · {emp.get("pais", "")}
                </div>
            </div>
            <div style="text-align:right;font-size:10px;color:#64748B;
                        font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;">
                <div>CUMPLE: <strong style="color:#0A0A0A;">{cumple_str}</strong></div>
                <div style="margin-top:2px;">INGRESO: <strong style="color:#0A0A0A;">{ingreso_str}</strong></div>
            </div>
        </div>
        ''')
    st.markdown("".join(cards_html), unsafe_allow_html=True)

    if not inactive.empty:
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:#94A3B8;margin:24px 0 12px 0;">'
            f'— INACTIVOS · {len(inactive)}</div>',
            unsafe_allow_html=True,
        )
        for _, emp in inactive.iterrows():
            st.caption(f"• {emp['nombre']} (ID {emp['id']}) — inactivo")


def _render_new_employee_form(employees_df: pd.DataFrame):
    """Form para agregar nuevo empleado."""
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #16A34A;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">Después de crear el empleado, '
        've a la pestaña "Editar horarios"</strong> para asignarle su horario semanal.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Calcular siguiente ID
    if not employees_df.empty:
        next_id = int(employees_df["id"].astype(int).max()) + 1
    else:
        next_id = 1

    with st.form("new_employee_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input("Nombre", key="emp_nuevo_nombre", max_chars=50)
        with col2:
            rol = st.selectbox("Rol", options=["Agente", "Supervisora", "Supervisor", "Manager"], key="emp_nuevo_rol")
        with col3:
            pais = st.selectbox("País", options=["GT", "VE", "US", "MX"], key="emp_nuevo_pais")

        col4, col5, col6 = st.columns(3)
        with col4:
            email = st.text_input("Email (opcional)", key="emp_nuevo_email", max_chars=100)
        with col5:
            cumpleanos = st.date_input(
                "Fecha de cumpleaños",
                value=date(2000, 1, 1),
                min_value=date(1950, 1, 1),
                max_value=today_gt(),
                format="DD/MM/YYYY",
                key="emp_nuevo_cumple",
            )
        with col6:
            fecha_ingreso = st.date_input(
                "Fecha de ingreso",
                value=today_gt(),
                min_value=date(2010, 1, 1),
                max_value=today_gt(),
                format="DD/MM/YYYY",
                key="emp_nuevo_ingreso",
            )

        col7, col8 = st.columns([1, 2])
        with col7:
            iniciales = st.text_input(
                "Iniciales (2 letras)",
                max_chars=2,
                key="emp_nuevo_inic",
                help="Ej: AL para Alessandro",
            )
        with col8:
            color_avatar = st.selectbox(
                "Color de avatar",
                options=AVATAR_COLORS,
                format_func=lambda c: f"●  {c}",
                key="emp_nuevo_color",
            )

        st.caption(f"Se asignará automáticamente el ID `{next_id}`")

        submitted = st.form_submit_button(
            "Crear empleado", use_container_width=True, type="primary",
        )

        if submitted:
            if not nombre.strip():
                notify_error("El nombre es obligatorio.")
            elif not iniciales.strip() or len(iniciales) > 2:
                notify_error("Las iniciales deben ser 1 o 2 letras.")
            else:
                try:
                    row = [
                        next_id, nombre.strip(), rol, pais, email.strip(),
                        cumpleanos.strftime("%Y-%m-%d"),
                        fecha_ingreso.strftime("%Y-%m-%d"),
                        iniciales.upper(), color_avatar, "TRUE",
                    ]
                    append_row(WS_EMPLOYEES, row)

                    # Crear horario base vacío (todos días libres por default)
                    for day in range(7):
                        sched_row = [
                            next_id, nombre.strip(), day, DAYS_ES[day],
                            "", "", "", "", "TRUE",  # día libre por default
                        ]
                        append_row(WS_SCHEDULES, sched_row)

                    notify_success(
                        f"{nombre} creado (ID {next_id}). "
                        "Ve a 'Editar horarios' para asignar su horario semanal.",
                        title="Empleado creado"
                    )
                except Exception as e:
                    notify_error(str(e))


def _render_edit_form(employees_df: pd.DataFrame):
    """Form para editar empleado existente."""
    if employees_df.empty:
        st.info("📭 No hay empleados para editar.")
        return

    emp_options = {}
    for _, emp in employees_df.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        is_active = str(emp.get("activo", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
        status_icon = "✓" if is_active else "✕"
        display = f"{status_icon} {flag}  {emp['nombre']} (ID {emp['id']})"
        emp_options[display] = emp.to_dict()

    selected_key = st.selectbox(
        "Empleado a editar",
        options=list(emp_options.keys()),
        key="edit_emp_select",
    )
    selected = emp_options[selected_key]

    with st.form("edit_employee_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input(
                "Nombre", value=selected["nombre"],
                key="edit_nombre", max_chars=50,
            )
        with col2:
            roles = ["Agente", "Supervisora", "Supervisor", "Manager"]
            current_rol = selected.get("rol", "Agente")
            rol = st.selectbox(
                "Rol", options=roles,
                index=roles.index(current_rol) if current_rol in roles else 0,
                key="edit_rol",
            )
        with col3:
            paises = ["GT", "VE", "US", "MX"]
            current_pais = selected.get("pais", "GT")
            pais = st.selectbox(
                "País", options=paises,
                index=paises.index(current_pais) if current_pais in paises else 0,
                key="edit_pais",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            email = st.text_input(
                "Email", value=selected.get("email", "") or "",
                key="edit_email", max_chars=100,
            )
        with col5:
            current_cumple = parse_date(str(selected.get("cumpleanos", ""))) or date(2000, 1, 1)
            cumpleanos = st.date_input(
                "Cumpleaños", value=current_cumple,
                min_value=date(1950, 1, 1), max_value=today_gt(),
                format="DD/MM/YYYY", key="edit_cumple",
            )
        with col6:
            current_ingreso = parse_date(str(selected.get("fecha_ingreso", ""))) or today_gt()
            fecha_ingreso = st.date_input(
                "Fecha de ingreso", value=current_ingreso,
                min_value=date(2010, 1, 1), max_value=today_gt(),
                format="DD/MM/YYYY", key="edit_ingreso",
            )

        col7, col8, col9 = st.columns(3)
        with col7:
            iniciales = st.text_input(
                "Iniciales", value=selected.get("iniciales", "")[:2],
                max_chars=2, key="edit_inic",
            )
        with col8:
            current_color = selected.get("color_avatar", AVATAR_COLORS[0])
            color_avatar = st.selectbox(
                "Color avatar",
                options=AVATAR_COLORS,
                index=AVATAR_COLORS.index(current_color) if current_color in AVATAR_COLORS else 0,
                format_func=lambda c: f"●  {c}",
                key="edit_color",
            )
        with col9:
            is_active = str(selected.get("activo", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
            activo = st.selectbox(
                "Estado",
                options=["TRUE", "FALSE"],
                index=0 if is_active else 1,
                format_func=lambda x: "✓ Activo" if x == "TRUE" else "✕ Inactivo",
                key="edit_activo",
            )

        submitted = st.form_submit_button(
            "Guardar cambios", use_container_width=True, type="primary",
        )

        if submitted:
            try:
                # Encontrar fila por ID
                sheet_idx = _find_employee_row_idx(selected["id"])
                if not sheet_idx:
                    notify_error("No se encontró el empleado.")
                else:
                    ws = get_worksheet(WS_EMPLOYEES)
                    ws.update(f"A{sheet_idx}:J{sheet_idx}", [[
                        selected["id"], nombre.strip(), rol, pais, email.strip(),
                        cumpleanos.strftime("%Y-%m-%d"),
                        fecha_ingreso.strftime("%Y-%m-%d"),
                        iniciales.upper(), color_avatar, activo,
                    ]], value_input_option="USER_ENTERED")
                    invalidate_cache()
                    notify_success(f"{nombre} actualizado.", title="Empleado actualizado")
                    st.rerun()
            except Exception as e:
                notify_error(str(e))


def _render_schedule_editor(employees_df: pd.DataFrame):
    """Editor de horarios semanales del empleado."""
    if employees_df.empty:
        st.info("📭 No hay empleados.")
        return

    active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    if active.empty:
        st.info("📭 No hay empleados activos.")
        return

    emp_options = {}
    for _, emp in active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = int(emp["id"])

    selected_key = st.selectbox(
        "Empleado",
        options=list(emp_options.keys()),
        key="sched_emp_select",
    )
    selected_id = emp_options[selected_key]
    selected_name = active[active["id"].astype(int) == selected_id].iloc[0]["nombre"]

    # Cargar horarios actuales
    try:
        sched_df = read_worksheet(WS_SCHEDULES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    emp_sched = sched_df[sched_df["empleado_id"].astype(int) == selected_id].copy() if not sched_df.empty else pd.DataFrame()

    st.markdown(
        f'<div style="font-size:13px;color:#64748B;margin:16px 0;'
        f'padding:12px 16px;background:#F8FAFC;border-left:3px solid #2563EB;'
        f'border-radius:0 4px 4px 0;">Configura el horario semanal de '
        f'<strong style="color:#0A0A0A">{selected_name}</strong>. '
        f'Marca "Día libre" si no trabaja ese día.</div>',
        unsafe_allow_html=True,
    )

    new_schedule = {}
    with st.form("schedule_form"):
        for day in range(7):
            day_name = DAYS_FULL_ES[day]
            existing = emp_sched[emp_sched["dia_semana"].astype(int) == day]
            if not existing.empty:
                existing_row = existing.iloc[0]
                is_libre_default = str(existing_row.get("es_dia_libre", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
                ent_default = parse_time(str(existing_row.get("hora_entrada", "")))
                sal_default = parse_time(str(existing_row.get("hora_salida", "")))
                ai_default = parse_time(str(existing_row.get("almuerzo_inicio", "")))
                af_default = parse_time(str(existing_row.get("almuerzo_fin", "")))
            else:
                is_libre_default = True
                ent_default = sal_default = ai_default = af_default = None

            st.markdown(
                f'<div style="margin-top:16px;font-size:12px;font-weight:700;'
                f'letter-spacing:1px;text-transform:uppercase;color:#0A0A0A;'
                f'border-bottom:1px solid #E2E8F0;padding-bottom:6px;">{day_name}</div>',
                unsafe_allow_html=True,
            )

            col_libre, col_ent, col_sal, col_ai, col_af = st.columns([1, 1, 1, 1, 1])
            with col_libre:
                is_libre = st.checkbox(
                    "Día libre",
                    value=is_libre_default,
                    key=f"sched_libre_{day}",
                )
            with col_ent:
                ent = st.time_input(
                    "Entrada",
                    value=ent_default if ent_default else time(8, 0),
                    key=f"sched_ent_{day}",
                    step=300,
                    disabled=is_libre,
                )
            with col_sal:
                sal = st.time_input(
                    "Salida",
                    value=sal_default if sal_default else time(17, 0),
                    key=f"sched_sal_{day}",
                    step=300,
                    disabled=is_libre,
                )
            with col_ai:
                ai = st.time_input(
                    "Almuerzo inicio",
                    value=ai_default if ai_default else time(13, 0),
                    key=f"sched_ai_{day}",
                    step=300,
                    disabled=is_libre,
                )
            with col_af:
                af = st.time_input(
                    "Almuerzo fin",
                    value=af_default if af_default else time(14, 0),
                    key=f"sched_af_{day}",
                    step=300,
                    disabled=is_libre,
                )

            new_schedule[day] = {
                "is_libre": is_libre,
                "ent": ent if not is_libre else None,
                "sal": sal if not is_libre else None,
                "ai": ai if not is_libre else None,
                "af": af if not is_libre else None,
            }

        submitted = st.form_submit_button(
            "Guardar horario completo", use_container_width=True, type="primary",
        )

        if submitted:
            try:
                ws = get_worksheet(WS_SCHEDULES)
                all_rows = ws.get_all_values()
                headers = all_rows[0] if all_rows else []

                # Estrategia: borrar todas las filas del empleado y reescribir
                # Primero: encontrar índices a borrar (desde abajo para no romper indices)
                idx_emp_id = headers.index("empleado_id") if "empleado_id" in headers else 0
                idx_dia = headers.index("dia_semana") if "dia_semana" in headers else 2

                rows_to_delete = []
                for i, row in enumerate(all_rows[1:], start=2):
                    if len(row) > idx_emp_id and str(row[idx_emp_id]) == str(selected_id):
                        rows_to_delete.append(i)

                # Borrar de abajo hacia arriba
                for i in reversed(rows_to_delete):
                    ws.delete_rows(i)

                # Insertar nuevos horarios
                new_rows = []
                for day in range(7):
                    s = new_schedule[day]
                    if s["is_libre"]:
                        new_rows.append([
                            selected_id, selected_name, day, DAYS_ES[day],
                            "", "", "", "", "TRUE",
                        ])
                    else:
                        new_rows.append([
                            selected_id, selected_name, day, DAYS_ES[day],
                            s["ent"].strftime("%H:%M") if s["ent"] else "",
                            s["sal"].strftime("%H:%M") if s["sal"] else "",
                            s["ai"].strftime("%H:%M") if s["ai"] else "",
                            s["af"].strftime("%H:%M") if s["af"] else "",
                            "FALSE",
                        ])

                ws.append_rows(new_rows, value_input_option="USER_ENTERED")
                invalidate_cache()

                notify_success(
                    f"Horario de {selected_name} actualizado (7 días reescritos).",
                    title="Horario guardado"
                )
                st.rerun()
            except Exception as e:
                notify_error(str(e))


def _find_employee_row_idx(emp_id):
    """Encuentra el row index del empleado por ID."""
    ws = get_worksheet(WS_EMPLOYEES)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return None
    headers = all_rows[0]
    try:
        idx_id = headers.index("id")
    except ValueError:
        return None
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > idx_id and str(row[idx_id]) == str(emp_id):
            return i
    return None
