"""
modules/attendance_log.py
Registro de excepciones de asistencia: llegadas tarde, ausencias,
salidas tempranas, etc.

Los empleados con horario normal NO se registran aquí (el dashboard los muestra
como "trabajando" automáticamente). Solo se registran las EXCEPCIONES.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, time, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import (
    WS_ATTENDANCE, WS_EMPLOYEES, COLORS, FLAGS,
    EXCEPTION_TYPES, REFRESH_OTHER_TABS,
)
from core.time_utils import (
    today_gt, now_gt, format_date_long, parse_date, parse_time,
    format_time, format_date_short,
)
from core.auth import current_user_display_name


# Labels en español para los tipos de excepción
EXCEPTION_LABELS = {
    "NORMAL": "Normal (ajuste de horario)",
    "LLEGADA_TARDE": "Llegada tarde",
    "SALIDA_TEMPRANO": "Salida temprano",
    "AUSENTE": "Ausente",
    "PERMISO": "Permiso",
    "INCAPACIDAD": "Incapacidad médica",
    "DIA_LIBRE_INESPERADO": "Día libre inesperado",
}

EXCEPTION_COLORS = {
    "NORMAL": COLORS["slate_500"],
    "LLEGADA_TARDE": COLORS["late"],
    "SALIDA_TEMPRANO": COLORS["late"],
    "AUSENTE": COLORS["late_bg"],
    "PERMISO": COLORS["permit"],
    "INCAPACIDAD": COLORS["sick"],
    "DIA_LIBRE_INESPERADO": COLORS["day_off"],
}


def render():
    """Renderiza el módulo de Registro de Asistencia."""
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="attendance_log_refresh")

    render_page_title(
        eyebrow="REGISTRO",
        title="Asistencia diaria",
        subtitle=f"Excepciones · {format_date_long(today_gt())}",
    )

    # Cargar empleados activos
    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error al cargar empleados: {e}")
        return

    if employees_df.empty:
        st.warning("No hay empleados cargados. Ve a 🛠️ Setup Inicial.")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    # Tabs: Nuevo Registro · Histórico
    tab_new, tab_history = st.tabs(["➕  Nuevo registro", "📜  Histórico"])

    # ============================================================
    # TAB 1 — NUEVO REGISTRO
    # ============================================================
    with tab_new:
        _render_new_exception_form(employees_active)

    # ============================================================
    # TAB 2 — HISTÓRICO
    # ============================================================
    with tab_history:
        _render_history(employees_active)


# ============================================================
# FORMULARIO DE NUEVA EXCEPCIÓN
# ============================================================
def _render_new_exception_form(employees_active: pd.DataFrame):
    """Formulario para registrar una nueva excepción."""

    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #DC2626;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">¿Cuándo usar este registro?</strong><br>'
        'Solo cuando un empleado <strong>se desvía de su horario base</strong>: '
        'llegó tarde, salió temprano, no vino, tomó permiso, incapacidad médica, etc. '
        'Los días normales NO se registran aquí.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Construir mapeo empleado → datos para el dropdown
    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = FLAGS.get(emp.get("pais", ""), "")
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {
            "id": int(emp["id"]),
            "nombre": emp["nombre"],
            "pais": emp.get("pais", ""),
        }

    with st.form("new_exception_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            emp_display = st.selectbox(
                "Empleado",
                options=list(emp_options.keys()),
                key="exc_emp",
            )
            fecha_excepcion = st.date_input(
                "Fecha",
                value=today_gt(),
                max_value=today_gt() + timedelta(days=30),
                key="exc_fecha",
                format="DD/MM/YYYY",
            )

        with col2:
            tipo = st.selectbox(
                "Tipo de excepción",
                options=EXCEPTION_TYPES,
                format_func=lambda x: EXCEPTION_LABELS.get(x, x),
                key="exc_tipo",
            )

        # Horas solo si aplica al tipo
        show_hours = tipo in ("LLEGADA_TARDE", "SALIDA_TEMPRANO", "NORMAL")
        col3, col4 = st.columns(2)
        hora_entrada_real = None
        hora_salida_real = None
        with col3:
            if show_hours:
                hora_entrada_real = st.time_input(
                    "Hora de entrada real",
                    value=None,
                    key="exc_hora_entrada",
                    help="Solo si entró/salió en hora distinta a su horario base",
                )
        with col4:
            if show_hours:
                hora_salida_real = st.time_input(
                    "Hora de salida real",
                    value=None,
                    key="exc_hora_salida",
                )

        observaciones = st.text_area(
            "Observaciones / motivo",
            placeholder="Ej: Cita médica, tráfico extremo, emergencia familiar...",
            key="exc_obs",
            max_chars=300,
        )

        submitted = st.form_submit_button(
            "Registrar excepción",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            try:
                selected = emp_options[emp_display]
                timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")

                row = [
                    fecha_excepcion.strftime("%Y-%m-%d"),  # fecha
                    selected["id"],                         # empleado_id
                    selected["nombre"],                     # empleado_nombre
                    hora_entrada_real.strftime("%H:%M") if hora_entrada_real else "",
                    hora_salida_real.strftime("%H:%M") if hora_salida_real else "",
                    tipo,                                   # tipo_excepcion
                    observaciones,                          # observaciones
                    current_user_display_name(),            # registrado_por
                    timestamp,                              # timestamp
                ]

                append_row(WS_ATTENDANCE, row)
                st.success(
                    f"✅ Excepción registrada para **{selected['nombre']}** "
                    f"el {fecha_excepcion.strftime('%d/%m/%Y')}: "
                    f"{EXCEPTION_LABELS.get(tipo, tipo)}"
                )
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error al registrar: {e}")


# ============================================================
# HISTÓRICO
# ============================================================
def _render_history(employees_active: pd.DataFrame):
    """Tabla del histórico de excepciones con filtros."""

    try:
        df = read_worksheet(WS_ATTENDANCE)
    except Exception as e:
        st.error(f"Error al cargar histórico: {e}")
        return

    if df.empty:
        st.info("📭 No hay excepciones registradas todavía.")
        return

    # Parsear fechas
    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"].notna()].copy()

    # ============================================================
    # FILTROS
    # ============================================================
    col1, col2, col3, col4 = st.columns([1.3, 1.3, 1.3, 1])

    with col1:
        # Rango de fechas — default últimos 30 días
        date_range = st.date_input(
            "Rango de fechas",
            value=(today_gt() - timedelta(days=30), today_gt()),
            format="DD/MM/YYYY",
            key="hist_dates",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_from, date_to = date_range
        else:
            date_from = date_to = today_gt()

    with col2:
        emp_filter = st.selectbox(
            "Empleado",
            options=["Todos"] + sorted(employees_active["nombre"].tolist()),
            key="hist_emp",
        )

    with col3:
        type_filter = st.selectbox(
            "Tipo",
            options=["Todos"] + EXCEPTION_TYPES,
            format_func=lambda x: "Todos" if x == "Todos" else EXCEPTION_LABELS.get(x, x),
            key="hist_type",
        )

    with col4:
        st.write("")  # espaciador
        st.write("")
        st.caption(f"Total registros: **{len(df)}**")

    # Aplicar filtros
    filtered = df[
        (df["fecha_parsed"] >= date_from)
        & (df["fecha_parsed"] <= date_to)
    ].copy()

    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]

    if type_filter != "Todos":
        filtered = filtered[filtered["tipo_excepcion"] == type_filter]

    if filtered.empty:
        st.info("🔎 Sin resultados para los filtros seleccionados.")
        return

    # Ordenar por fecha desc
    filtered = filtered.sort_values("fecha_parsed", ascending=False).reset_index(drop=True)

    # ============================================================
    # RENDER DE TABLA
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        f'— {len(filtered)} registros'
        '</div>',
        unsafe_allow_html=True,
    )

    # Construir tabla custom HTML para el look STT
    rows_html = []
    for idx, row in filtered.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag = FLAGS.get(pais, "")

        tipo = row.get("tipo_excepcion", "")
        tipo_label = EXCEPTION_LABELS.get(tipo, tipo)
        tipo_color = EXCEPTION_COLORS.get(tipo, COLORS["slate_500"])

        ent = row.get("hora_entrada_real", "") or ""
        sal = row.get("hora_salida_real", "") or ""
        hora_info = ""
        if ent or sal:
            parts = []
            if ent:
                parts.append(f"Ent: {ent}")
            if sal:
                parts.append(f"Sal: {sal}")
            hora_info = " · ".join(parts)

        obs = row.get("observaciones", "") or ""
        if len(obs) > 80:
            obs = obs[:77] + "..."

        registrado_por = row.get("registrado_por", "") or ""
        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""

        rows_html.append(f"""
        <tr>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;font-family:'JetBrains Mono',monospace;font-size:12px;color:#334155;white-space:nowrap;">
                {fecha_str}
            </td>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;">
                <span style="font-size:16px;margin-right:6px;">{flag}</span>
                <strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong>
            </td>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;">
                <span style="display:inline-block;padding:4px 10px;border-radius:3px;font-size:10px;
                font-weight:700;letter-spacing:0.5px;text-transform:uppercase;
                background:{tipo_color}20;color:{tipo_color};">
                    {tipo_label}
                </span>
            </td>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;font-family:'JetBrains Mono',monospace;font-size:11px;color:#64748B;">
                {hora_info or '—'}
            </td>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;color:#475569;">
                {obs or '—'}
            </td>
            <td style="padding:14px 16px;border-bottom:1px solid #F1F5F9;font-family:'JetBrains Mono',monospace;font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.5px;">
                {registrado_por}
            </td>
        </tr>
        """)

    table_html = f"""
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,0.02);overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:'Inter Tight',sans-serif;">
        <thead style="background:#FAFBFC;">
            <tr>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Fecha</th>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Empleado</th>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Tipo</th>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Horario real</th>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Observaciones</th>
                <th style="padding:12px 16px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Registró</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)

    # ============================================================
    # ZONA DE ELIMINACIÓN
    # ============================================================
    st.divider()
    with st.expander("🗑️  Eliminar registro"):
        st.caption(
            "Selecciona un registro para eliminarlo. **Acción irreversible.**"
        )

        # Construir opciones legibles
        delete_options = {}
        for _, row in filtered.iterrows():
            fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y")
            emp = row.get("empleado_nombre", "")
            tipo = EXCEPTION_LABELS.get(row.get("tipo_excepcion", ""), "")
            key = f"{fecha_str} · {emp} · {tipo}"
            delete_options[key] = row

        if delete_options:
            selected_key = st.selectbox(
                "Registro a eliminar",
                options=list(delete_options.keys()),
                key="del_select",
            )

            col_del1, col_del2 = st.columns([1, 4])
            with col_del1:
                if st.button("Eliminar", type="primary", key="del_btn"):
                    try:
                        selected = delete_options[selected_key]
                        # Encontrar el row_idx en el Sheet (filtered viene del df ya parseado)
                        # Necesitamos el índice ORIGINAL en el sheet
                        sheet_row_idx = _find_sheet_row_index(selected)
                        if sheet_row_idx:
                            delete_row(WS_ATTENDANCE, sheet_row_idx)
                            st.success(f"✅ Registro eliminado.")
                            st.rerun()
                        else:
                            st.error("No se pudo localizar el registro en el Sheet.")
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")


def _find_sheet_row_index(target_row: pd.Series) -> int:
    """
    Encuentra el índice de la fila en la worksheet (1-based, incluyendo header).
    Busca por combinación fecha + empleado_id + timestamp (debería ser único).
    """
    ws = get_worksheet(WS_ATTENDANCE)
    all_rows = ws.get_all_values()

    if len(all_rows) < 2:
        return None

    headers = all_rows[0]
    try:
        idx_fecha = headers.index("fecha")
        idx_emp_id = headers.index("empleado_id")
        idx_timestamp = headers.index("timestamp")
    except ValueError:
        return None

    target_fecha = target_row.get("fecha")
    target_emp_id = str(target_row.get("empleado_id"))
    target_ts = target_row.get("timestamp")

    for i, row in enumerate(all_rows[1:], start=2):  # start=2 porque header es fila 1
        if len(row) > max(idx_fecha, idx_emp_id, idx_timestamp):
            if (row[idx_fecha] == target_fecha
                and str(row[idx_emp_id]) == target_emp_id
                and row[idx_timestamp] == target_ts):
                return i
    return None
