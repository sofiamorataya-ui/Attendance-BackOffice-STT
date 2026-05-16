"""
modules/attendance_log.py
Registro de excepciones de asistencia con UX mejorada.

CAMBIOS vs versión anterior:
- "Llegada tarde": selector de hora exacta → calcula minutos tarde automáticamente
- "Salida temprano": selector de hora exacta → calcula minutos antes
- Notificaciones snackbar profesionales (sin globos)
- Banderas vía Twemoji (renderizan en todos los SO)
- Sin HTML escapándose
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, time, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import (
    WS_ATTENDANCE, WS_EMPLOYEES, WS_SCHEDULES, COLORS,
    EXCEPTION_TYPES, REFRESH_OTHER_TABS,
)
from core.time_utils import (
    today_gt, now_gt, format_date_long, parse_date, parse_time,
    time_to_minutes,
)
from core.auth import current_user_display_name
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error, notify_warning


# Labels en español para los tipos de excepción
EXCEPTION_LABELS = {
    "NORMAL": "Ajuste de horario",
    "LLEGADA_TARDE": "Llegada tarde",
    "SALIDA_TEMPRANO": "Salida temprano",
    "AUSENTE": "Ausente",
    "PERMISO": "Permiso",
    "INCAPACIDAD": "Incapacidad médica",
    "DIA_LIBRE_INESPERADO": "Día libre inesperado",
}

EXCEPTION_COLORS = {
    "NORMAL": "#64748B",
    "LLEGADA_TARDE": "#DC2626",
    "SALIDA_TEMPRANO": "#EA580C",
    "AUSENTE": "#991B1B",
    "PERMISO": "#2563EB",
    "INCAPACIDAD": "#7C2D12",
    "DIA_LIBRE_INESPERADO": "#94A3B8",
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

    tab_new, tab_history = st.tabs(["➕  Nuevo registro", "📜  Histórico"])

    with tab_new:
        _render_new_exception_form(employees_active)

    with tab_history:
        _render_history(employees_active)


def _get_scheduled_hours_for(employee_id: int, target_date: date):
    """Obtiene hora_entrada y hora_salida programadas del empleado para ese día."""
    try:
        df = read_worksheet(WS_SCHEDULES)
        if df.empty:
            return None, None
        weekday = target_date.weekday()
        match = df[
            (df["empleado_id"].astype(str) == str(employee_id))
            & (df["dia_semana"].astype(int) == weekday)
        ]
        if match.empty:
            return None, None
        row = match.iloc[0]
        is_day_off = str(row.get("es_dia_libre", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
        if is_day_off:
            return None, None
        return parse_time(str(row.get("hora_entrada", ""))), parse_time(str(row.get("hora_salida", "")))
    except Exception:
        return None, None


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

    # Mapeo empleado → datos
    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {
            "id": int(emp["id"]),
            "nombre": emp["nombre"],
            "pais": emp.get("pais", ""),
        }

    # Selector empleado y fecha FUERA del form para reactive logic
    col_emp, col_fecha, col_tipo = st.columns([2, 1.2, 1.3])

    with col_emp:
        emp_display = st.selectbox(
            "Empleado",
            options=list(emp_options.keys()),
            key="exc_emp_outer",
        )

    with col_fecha:
        fecha_excepcion = st.date_input(
            "Fecha",
            value=today_gt(),
            max_value=today_gt() + timedelta(days=30),
            key="exc_fecha_outer",
            format="DD/MM/YYYY",
        )

    with col_tipo:
        tipo = st.selectbox(
            "Tipo de excepción",
            options=EXCEPTION_TYPES,
            format_func=lambda x: EXCEPTION_LABELS.get(x, x),
            key="exc_tipo_outer",
        )

    selected = emp_options[emp_display]
    sched_entrada, sched_salida = _get_scheduled_hours_for(selected["id"], fecha_excepcion)

    # ============================================================
    # CAMPOS CONDICIONALES SEGÚN TIPO
    # ============================================================
    hora_entrada_real = None
    hora_salida_real = None
    minutos_diff = None

    if tipo == "LLEGADA_TARDE":
        st.markdown(
            f'<div style="background:#FEE2E2;border-left:3px solid #DC2626;'
            f'padding:10px 14px;border-radius:0 4px 4px 0;margin:8px 0 12px 0;'
            f'font-size:12px;color:#7F1D1D;">'
            f'<strong>Horario programado:</strong> Entrada {sched_entrada.strftime("%I:%M %p").lstrip("0") if sched_entrada else "—"}'
            f'</div>',
            unsafe_allow_html=True,
        )
        col_real, col_diff = st.columns([1.2, 1])
        with col_real:
            default_late = sched_entrada or time(8, 0)
            hora_entrada_real = st.time_input(
                "Hora real de entrada",
                value=time(default_late.hour, min(default_late.minute + 15, 59)),
                key="exc_late_time",
                help="Hora real en que el empleado llegó",
                step=300,  # 5 min
            )
        with col_diff:
            if hora_entrada_real and sched_entrada:
                diff_min = time_to_minutes(hora_entrada_real) - time_to_minutes(sched_entrada)
                if diff_min < 0:
                    diff_min = 0
                minutos_diff = diff_min
                st.markdown(
                    f'<div style="background:#FFFFFF;border:1px solid #FCA5A5;'
                    f'border-radius:6px;padding:12px 16px;margin-top:24px;text-align:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
                    f'text-transform:uppercase;color:#94A3B8;margin-bottom:4px;">MINUTOS TARDE</div>'
                    f'<div style="font-size:28px;font-weight:700;color:#DC2626;'
                    f'font-family:\'Inter Tight\';line-height:1;">{diff_min}'
                    f'<span style="font-size:13px;color:#94A3B8;margin-left:4px;">min</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    elif tipo == "SALIDA_TEMPRANO":
        st.markdown(
            f'<div style="background:#FFEDD5;border-left:3px solid #EA580C;'
            f'padding:10px 14px;border-radius:0 4px 4px 0;margin:8px 0 12px 0;'
            f'font-size:12px;color:#7C2D12;">'
            f'<strong>Horario programado:</strong> Salida {sched_salida.strftime("%I:%M %p").lstrip("0") if sched_salida else "—"}'
            f'</div>',
            unsafe_allow_html=True,
        )
        col_real, col_diff = st.columns([1.2, 1])
        with col_real:
            default_early = sched_salida or time(17, 0)
            hora_salida_real = st.time_input(
                "Hora real de salida",
                value=time(default_early.hour, max(default_early.minute - 15, 0)) if default_early.minute >= 15 else time(max(default_early.hour - 1, 0), 45),
                key="exc_early_time",
                step=300,
            )
        with col_diff:
            if hora_salida_real and sched_salida:
                diff_min = time_to_minutes(sched_salida) - time_to_minutes(hora_salida_real)
                if diff_min < 0:
                    diff_min = 0
                minutos_diff = diff_min
                st.markdown(
                    f'<div style="background:#FFFFFF;border:1px solid #FDBA74;'
                    f'border-radius:6px;padding:12px 16px;margin-top:24px;text-align:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
                    f'text-transform:uppercase;color:#94A3B8;margin-bottom:4px;">MINUTOS ANTES</div>'
                    f'<div style="font-size:28px;font-weight:700;color:#EA580C;'
                    f'font-family:\'Inter Tight\';line-height:1;">{diff_min}'
                    f'<span style="font-size:13px;color:#94A3B8;margin-left:4px;">min</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    elif tipo == "NORMAL":
        col1, col2 = st.columns(2)
        with col1:
            hora_entrada_real = st.time_input(
                "Hora real de entrada (opcional)",
                value=sched_entrada,
                key="exc_normal_in",
                step=300,
            )
        with col2:
            hora_salida_real = st.time_input(
                "Hora real de salida (opcional)",
                value=sched_salida,
                key="exc_normal_out",
                step=300,
            )

    # Observaciones siempre
    observaciones = st.text_area(
        "Observaciones / motivo",
        placeholder="Ej: Cita médica, tráfico extremo, emergencia familiar...",
        key="exc_obs",
        max_chars=300,
    )

    # Botón submit
    if st.button(
        "Registrar excepción",
        use_container_width=True,
        type="primary",
        key="exc_submit",
    ):
        try:
            # Construir nota con minutos diff si aplica
            obs_final = observaciones.strip()
            if minutos_diff is not None and minutos_diff > 0:
                prefix = f"[{minutos_diff} min] "
                obs_final = prefix + obs_final if obs_final else f"{minutos_diff} min de diferencia"

            timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                fecha_excepcion.strftime("%Y-%m-%d"),
                selected["id"],
                selected["nombre"],
                hora_entrada_real.strftime("%H:%M") if hora_entrada_real else "",
                hora_salida_real.strftime("%H:%M") if hora_salida_real else "",
                tipo,
                obs_final,
                current_user_display_name(),
                timestamp,
            ]
            append_row(WS_ATTENDANCE, row)

            label_tipo = EXCEPTION_LABELS.get(tipo, tipo)
            extra = f" · {minutos_diff} min" if minutos_diff else ""
            notify_success(
                f"{selected['nombre']} · {fecha_excepcion.strftime('%d/%m/%Y')} · {label_tipo}{extra}",
                title="Excepción registrada"
            )
        except Exception as e:
            notify_error(str(e), title="Error al registrar")


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

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"].notna()].copy()

    # Filtros
    col1, col2, col3, col4 = st.columns([1.3, 1.3, 1.3, 1])

    with col1:
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
        st.write("")
        st.write("")
        st.caption(f"Total registros: **{len(df)}**")

    # Aplicar filtros
    filtered = df[
        (df["fecha_parsed"] >= date_from) & (df["fecha_parsed"] <= date_to)
    ].copy()
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo_excepcion"] == type_filter]

    if filtered.empty:
        st.info("🔎 Sin resultados para los filtros seleccionados.")
        return

    filtered = filtered.sort_values("fecha_parsed", ascending=False).reset_index(drop=True)

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        f'— {len(filtered)} registros'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # TABLA EN BLOQUE ÚNICO HTML (sin fragmentación)
    # ============================================================
    rows_html_parts = []
    for _, row in filtered.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag = flag_emoji_unicode(pais)

        tipo = row.get("tipo_excepcion", "")
        tipo_label = EXCEPTION_LABELS.get(tipo, tipo)
        tipo_color = EXCEPTION_COLORS.get(tipo, COLORS["slate_500"])

        ent = row.get("hora_entrada_real", "") or ""
        sal = row.get("hora_salida_real", "") or ""
        parts = []
        if ent:
            parts.append(f"Ent: {ent}")
        if sal:
            parts.append(f"Sal: {sal}")
        hora_info = " · ".join(parts) if parts else "—"

        obs = (row.get("observaciones", "") or "")[:80] + ("..." if len(row.get("observaciones", "") or "") > 80 else "")
        registrado_por = row.get("registrado_por", "") or ""
        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""

        rows_html_parts.append(
            f'<tr>'
            f'<td class="stt-h-cell stt-h-mono">{fecha_str}</td>'
            f'<td class="stt-h-cell">'
            f'<span style="margin-right:6px;">{flag}</span>'
            f'<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong>'
            f'</td>'
            f'<td class="stt-h-cell">'
            f'<span style="display:inline-block;padding:4px 10px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span>'
            f'</td>'
            f'<td class="stt-h-cell stt-h-mono">{hora_info}</td>'
            f'<td class="stt-h-cell" style="font-size:12px;color:#475569;">{obs or "—"}</td>'
            f'<td class="stt-h-cell stt-h-mono" style="color:#94A3B8;">{registrado_por}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.stt-h-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.stt-h-table th{padding:12px 16px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.stt-h-cell{padding:14px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.stt-h-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,0.02);overflow-x:auto;">'
        '<table class="stt-h-table">'
        '<thead><tr>'
        '<th>Fecha</th><th>Empleado</th><th>Tipo</th>'
        '<th>Horario real</th><th>Observaciones</th><th>Registró</th>'
        '</tr></thead><tbody>'
        + "".join(rows_html_parts) +
        '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # Eliminación
    st.divider()
    with st.expander("🗑️  Eliminar registro"):
        st.caption("Selecciona un registro para eliminarlo. **Acción irreversible.**")
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
            if st.button("Eliminar", type="primary", key="del_btn"):
                try:
                    selected = delete_options[selected_key]
                    sheet_row_idx = _find_sheet_row_index(selected)
                    if sheet_row_idx:
                        delete_row(WS_ATTENDANCE, sheet_row_idx)
                        notify_success(f"Registro de {selected.get('empleado_nombre')} eliminado.", title="Eliminado")
                        st.rerun()
                    else:
                        notify_error("No se pudo localizar el registro.")
                except Exception as e:
                    notify_error(str(e))


def _find_sheet_row_index(target_row: pd.Series):
    """Encuentra el índice (1-based) en la worksheet."""
    ws = get_worksheet(WS_ATTENDANCE)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return None
    headers = all_rows[0]
    try:
        idx_fecha = headers.index("fecha")
        idx_emp_id = headers.index("empleado_id")
        idx_ts = headers.index("timestamp")
    except ValueError:
        return None
    target_fecha = target_row.get("fecha")
    target_emp_id = str(target_row.get("empleado_id"))
    target_ts = target_row.get("timestamp")
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > max(idx_fecha, idx_emp_id, idx_ts):
            if (row[idx_fecha] == target_fecha
                and str(row[idx_emp_id]) == target_emp_id
                and row[idx_ts] == target_ts):
                return i
    return None
