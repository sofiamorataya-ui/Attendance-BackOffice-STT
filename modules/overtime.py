"""
modules/overtime.py
Sistema completo de Horas Extras con 3 sub-pestañas.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import (
    WS_OVERTIME, WS_EMPLOYEES, COLORS, REFRESH_OTHER_TABS,
)
from core.time_utils import today_gt, now_gt, format_date_long, parse_date
from core.auth import current_user_display_name
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error, notify_warning
from core.business_logic import (
    ensure_henry_saturdays, get_overtime_matrix, load_overtime_df,
    get_overtime_today, get_overtime_this_week, get_overtime_this_month,
    total_overtime_by_employee, format_hours_cell, MONTHS_ES,
)


def render():
    """Renderiza el módulo de Horas Extras."""
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="overtime_refresh")

    render_page_title(
        eyebrow="REPORTES",
        title="Horas Extras",
        subtitle=f"Año en curso · {today_gt().year}",
    )

    # Inyección automática de sábados de Henry (una vez por semana ISO)
    cache_key = f"henry_saturdays_{today_gt().year}_{today_gt().isocalendar()[1]}"
    if cache_key not in st.session_state:
        try:
            result = ensure_henry_saturdays(today_gt().year)
            st.session_state[cache_key] = result
        except Exception as e:
            st.warning(f"No se pudo verificar sábados de Henry: {e}")

    # Cargar empleados
    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error al cargar empleados: {e}")
        return

    if employees_df.empty:
        st.warning("No hay empleados cargados.")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    tab_matrix, tab_register, tab_detail = st.tabs([
        "📊  Matriz Mensual",
        "➕  Registrar",
        "🔍  Detalle día / semana / mes",
    ])

    with tab_matrix:
        _render_monthly_matrix()

    with tab_register:
        _render_register_form(employees_active)

    with tab_detail:
        _render_detail_view(employees_active)


def _render_monthly_matrix():
    """Matriz mensual estilo Excel."""
    current_year = today_gt().year
    col1, _, _ = st.columns([1, 3, 1])
    with col1:
        selected_year = st.selectbox(
            "Año",
            options=list(range(current_year - 2, current_year + 2)),
            index=2,
            key="matrix_year",
        )

    try:
        df_matrix = get_overtime_matrix(selected_year)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if df_matrix.empty:
        st.info("📭 No hay horas extras registradas.")
        return

    months_cols = list(MONTHS_ES.values())

    # Header
    header_html = (
        f'<tr style="background:#1F4E79;color:#FFFFFF;">'
        f'<th colspan="{len(months_cols) + 2}" '
        f'style="padding:14px;text-align:center;font-size:13px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;border:1px solid #1F4E79;">'
        f'HORAS EXTRAS · BO · {selected_year:,}</th></tr>'
    )

    cols_cells = (
        '<th style="padding:10px 12px;text-align:center;background:#DDEBF7;'
        'color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #BDD7EE;'
        'letter-spacing:0.5px;">Empleado</th>'
    )
    for m in months_cols:
        cols_cells += (
            f'<th style="padding:10px 8px;text-align:center;background:#DDEBF7;'
            f'color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #BDD7EE;">'
            f'{m}</th>'
        )
    cols_cells += (
        '<th style="padding:10px 8px;text-align:center;background:#BDD7EE;'
        'color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #1F4E79;">TOTAL</th>'
    )

    rows_html = []
    for idx, row in df_matrix.iterrows():
        emp = row["Empleado"]
        is_total = emp == "TOTAL"

        if is_total:
            cells = (
                f'<td style="padding:10px 12px;background:#C6EFCE;color:#0A0A0A;'
                f'font-weight:700;border:1px solid #92D050;font-size:12px;">{emp}</td>'
            )
            for m in months_cols:
                cells += (
                    f'<td style="padding:10px 8px;background:#C6EFCE;color:#0A0A0A;'
                    f'font-weight:700;text-align:center;border:1px solid #92D050;'
                    f'font-size:12px;">{format_hours_cell(row[m])}</td>'
                )
            cells += (
                f'<td style="padding:10px 8px;background:#92D050;color:#0A0A0A;'
                f'font-weight:800;text-align:center;border:1px solid #1F4E79;'
                f'font-size:13px;">{format_hours_cell(row["TOTAL"])}</td>'
            )
        else:
            bg = "#FFFFFF" if idx % 2 == 0 else "#F8FAFC"
            cells = (
                f'<td style="padding:10px 12px;background:{bg};color:#0A0A0A;'
                f'font-weight:600;border:1px solid #E2E8F0;font-size:12px;">{emp}</td>'
            )
            for m in months_cols:
                cells += (
                    f'<td style="padding:10px 8px;background:{bg};color:#334155;'
                    f'text-align:center;border:1px solid #E2E8F0;font-size:12px;">'
                    f'{format_hours_cell(row[m])}</td>'
                )
            cells += (
                f'<td style="padding:10px 8px;background:#F1F5F9;color:#0A0A0A;'
                f'font-weight:700;text-align:center;border:1px solid #CBD5E1;'
                f'font-size:12px;">{format_hours_cell(row["TOTAL"])}</td>'
            )
        rows_html.append(f'<tr>{cells}</tr>')

    table_html = (
        '<div style="overflow-x:auto;margin-top:8px;">'
        '<table style="width:100%;border-collapse:collapse;'
        'font-family:\'Inter Tight\',sans-serif;">'
        '<thead>' + header_html + '<tr>' + cols_cells + '</tr></thead>'
        '<tbody>' + "".join(rows_html) + '</tbody>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # Top 3
    st.markdown(
        '<div style="margin-top:24px;font-size:11px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#DC2626;">'
        '— TOP CONTRIBUYENTES DEL AÑO</div>',
        unsafe_allow_html=True,
    )

    top_df = total_overtime_by_employee(selected_year)
    if not top_df.empty:
        top_3 = top_df.head(3)
        cols = st.columns(3)
        for i, (_, row) in enumerate(top_3.iterrows()):
            with cols[i]:
                medal = ["🥇", "🥈", "🥉"][i]
                st.markdown(
                    f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;'
                    f'border-radius:6px;padding:16px;text-align:center;">'
                    f'<div style="font-size:32px;line-height:1;">{medal}</div>'
                    f'<div style="font-size:14px;font-weight:700;color:#0A0A0A;'
                    f'margin-top:8px;">{row["empleado_nombre"]}</div>'
                    f'<div style="font-size:24px;font-weight:700;color:#DC2626;'
                    f'margin-top:4px;">{format_hours_cell(row["total_horas"])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _render_register_form(employees_active: pd.DataFrame):
    """Formulario para registrar horas extras con Hora Inicio + Hora Fin."""
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #D97706;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">Solo registra horas extras aprobadas</strong><br>'
        'Las horas extras deben ser autorizadas por supervisión. '
        'Henry tiene sábados recurrentes automáticos (7h cada sábado). '
        'Las horas se calculan automáticamente desde Hora Inicio y Hora Fin.'
        '</div>',
        unsafe_allow_html=True,
    )

    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {
            "id": int(emp["id"]),
            "nombre": emp["nombre"],
        }

    from core.time_utils import parse_time as _parse_time, time_to_minutes

    # NO usar st.form porque queremos preview en vivo de la duración
    col1, col2 = st.columns([2, 1.5])
    with col1:
        emp_display = st.selectbox(
            "Empleado", options=list(emp_options.keys()), key="ot_emp",
        )
    with col2:
        fecha_ot = st.date_input(
            "Fecha", value=today_gt(),
            max_value=today_gt() + timedelta(days=7),
            format="DD/MM/YYYY", key="ot_fecha",
        )

    col_hi, col_hf = st.columns(2)
    with col_hi:
        hi_str = st.text_input(
            "Hora inicio (HH:MM)",
            value="18:00",
            max_chars=8,
            placeholder="18:00",
            key="ot_hi",
            help="Acepta 18:00, 6:00 PM, 1800, etc.",
        )
    with col_hf:
        hf_str = st.text_input(
            "Hora fin (HH:MM)",
            value="22:00",
            max_chars=8,
            placeholder="22:00",
            key="ot_hf",
            help="Acepta 22:00, 10:00 PM, 2200, etc.",
        )

    # Validar y mostrar preview en vivo
    hi_parsed = _parse_time(hi_str)
    hf_parsed = _parse_time(hf_str)

    if hi_str and not hi_parsed:
        st.error(f"❌ Hora inicio inválida: '{hi_str}'. Usa formato HH:MM")
    if hf_str and not hf_parsed:
        st.error(f"❌ Hora fin inválida: '{hf_str}'. Usa formato HH:MM")

    horas_calc = 0.0
    duracion_pretty = ""
    if hi_parsed and hf_parsed:
        mins_hi = time_to_minutes(hi_parsed)
        mins_hf = time_to_minutes(hf_parsed)
        if mins_hf <= mins_hi:
            # Caso turno nocturno cruza medianoche (ej: 22:00 → 02:00)
            mins_hf += 24 * 60
        diff_min = mins_hf - mins_hi
        horas_calc = round(diff_min / 60.0, 2)
        h_int = diff_min // 60
        m_int = diff_min % 60
        if m_int == 0:
            duracion_pretty = f"{h_int}h"
        else:
            duracion_pretty = f"{h_int}h {m_int}min"

        if horas_calc > 12:
            st.warning(
                f"⚠️ La duración es {duracion_pretty} ({horas_calc}h). "
                f"Si cruza medianoche está bien; si no, revisa las horas."
            )
        elif horas_calc <= 0:
            st.error("❌ La hora fin debe ser posterior a la hora inicio.")
        else:
            st.success(
                f"✅ Duración calculada: **{duracion_pretty}** "
                f"(se registrarán **{horas_calc}h**)"
            )

    motivo = st.text_area(
        "Motivo / descripción",
        placeholder="Ej: Cierre de mes contable, cobertura de feriado US, etc.",
        key="ot_motivo", max_chars=300,
    )

    disabled = not (hi_parsed and hf_parsed and horas_calc > 0 and motivo.strip())

    if st.button(
        "Registrar horas extras", use_container_width=True, type="primary",
        key="ot_submit", disabled=disabled,
    ):
        try:
            selected = emp_options[emp_display]
            timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                fecha_ot.strftime("%Y-%m-%d"),
                selected["id"], selected["nombre"], horas_calc,
                motivo.strip(), current_user_display_name(), timestamp, "FALSE",
                hi_parsed.strftime("%H:%M"),
                hf_parsed.strftime("%H:%M"),
            ]
            append_row(WS_OVERTIME, row)
            from core.sheets import invalidate_cache
            invalidate_cache()
            notify_success(
                f"{horas_calc}h ({duracion_pretty}) registradas para {selected['nombre']} · "
                f"{fecha_ot.strftime('%d/%m/%Y')} · {hi_parsed.strftime('%H:%M')}–{hf_parsed.strftime('%H:%M')}",
                title="Horas extras registradas"
            )
            st.rerun()
        except Exception as e:
            notify_error(str(e))

    # Últimos 10 registros - Editor inline
    st.divider()
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin-bottom:12px;">'
        '— ÚLTIMOS 10 REGISTROS · EDITABLE</div>'
        '<div style="font-size:11px;color:#64748B;margin-bottom:8px;">'
        'Modifica los valores directamente en la tabla. Marca la casilla ✓ y presiona "Eliminar seleccionados" para borrar registros.'
        '</div>',
        unsafe_allow_html=True,
    )

    df = load_overtime_df()
    if df.empty:
        st.info("📭 No hay horas extras registradas.")
        return

    df_recent = df.sort_values(["fecha_parsed", "timestamp"], ascending=False).head(10).copy()
    df_recent = df_recent.reset_index(drop=True)

    # Helper para extraer hora_inicio/hora_fin con compatibilidad legacy
    hi_col = df_recent["hora_inicio"].astype(str) if "hora_inicio" in df_recent.columns else pd.Series([""] * len(df_recent))
    hf_col = df_recent["hora_fin"].astype(str) if "hora_fin" in df_recent.columns else pd.Series([""] * len(df_recent))

    # Construir DataFrame editable
    editor_df = pd.DataFrame({
        "_id": df_recent.index.astype(int),  # índice interno (no editable, oculto)
        "Eliminar": [False] * len(df_recent),
        "Fecha": pd.to_datetime(df_recent["fecha_parsed"]).dt.date if "fecha_parsed" in df_recent else df_recent["fecha"],
        "Empleado": df_recent["empleado_nombre"].astype(str),
        "Hora Inicio": hi_col.reset_index(drop=True),
        "Hora Fin": hf_col.reset_index(drop=True),
        "Horas": pd.to_numeric(df_recent["horas"], errors="coerce").fillna(0).astype(float),
        "Motivo": df_recent["motivo"].astype(str),
        "Aprobado por": df_recent["aprobado_por"].astype(str),
        "Recurrente": df_recent["recurrente"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"]),
    })

    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "_id": None,  # ocultar
            "Eliminar": st.column_config.CheckboxColumn(
                "✓",
                help="Marca para eliminar",
                default=False,
                width="small",
            ),
            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", width="small"),
            "Empleado": st.column_config.SelectboxColumn(
                "Empleado",
                options=sorted(employees_active["nombre"].tolist()) if not employees_active.empty else [],
                required=True,
            ),
            "Hora Inicio": st.column_config.TextColumn(
                "Inicio", help="Formato HH:MM (ej. 18:00). Vacío = registro legacy.",
                width="small",
            ),
            "Hora Fin": st.column_config.TextColumn(
                "Fin", help="Formato HH:MM (ej. 22:00). Si se modifica, las horas se recalculan al guardar.",
                width="small",
            ),
            "Horas": st.column_config.NumberColumn(
                "Horas",
                min_value=0.0, max_value=24.0, step=0.25, format="%.2f",
                width="small",
                help="Se recalcula automáticamente si modificas Hora Inicio/Fin.",
            ),
            "Motivo": st.column_config.TextColumn("Motivo"),
            "Aprobado por": st.column_config.TextColumn("Aprobó", width="small"),
            "Recurrente": st.column_config.CheckboxColumn("Recurr.", width="small"),
        },
        key="overtime_editor",
    )

    col_save, col_del = st.columns(2)

    with col_del:
        n_to_delete = int(edited_df["Eliminar"].sum())
        if st.button(
            f"🗑️ Eliminar seleccionados ({n_to_delete})",
            disabled=(n_to_delete == 0),
            use_container_width=True,
            key="ot_del_btn",
            type="secondary",
        ):
            try:
                rows_to_delete = edited_df[edited_df["Eliminar"]].copy()
                deleted_count = 0
                ws = get_worksheet(WS_OVERTIME)
                all_rows = ws.get_all_values()

                for _, dr in rows_to_delete.iterrows():
                    orig_idx = int(dr["_id"])
                    target = df_recent.iloc[orig_idx]
                    target_fecha = target.get("fecha", "")
                    target_emp = target.get("empleado_nombre", "")
                    target_horas = str(target.get("horas", ""))
                    target_ts = str(target.get("timestamp", ""))

                    # Buscar la fila exacta en el sheet por timestamp+empleado+fecha
                    headers_row = all_rows[0]
                    try:
                        idx_fecha = headers_row.index("fecha")
                        idx_emp = headers_row.index("empleado_nombre")
                        idx_ts = headers_row.index("timestamp")
                    except ValueError:
                        notify_error("Headers del sheet incompletos.")
                        return

                    target_row_idx = None
                    for i, srow in enumerate(all_rows[1:], start=2):
                        if (len(srow) > max(idx_fecha, idx_emp, idx_ts)
                                and srow[idx_fecha] == str(target_fecha)
                                and srow[idx_emp] == str(target_emp)
                                and srow[idx_ts] == target_ts):
                            target_row_idx = i
                            break

                    if target_row_idx:
                        delete_row(WS_OVERTIME, target_row_idx)
                        deleted_count += 1
                        # Reload all_rows para mantener los índices correctos
                        all_rows = get_worksheet(WS_OVERTIME).get_all_values()

                from core.sheets import invalidate_cache
                invalidate_cache()
                notify_success(f"{deleted_count} registro(s) eliminado(s).", title="Eliminados")
                st.rerun()
            except Exception as e:
                notify_error(f"Error al eliminar: {e}")

    with col_save:
        if st.button(
            "💾 Guardar cambios editados",
            use_container_width=True,
            type="primary",
            key="ot_save_btn",
        ):
            try:
                from core.time_utils import parse_time as _parse_time, time_to_minutes

                ws = get_worksheet(WS_OVERTIME)
                all_rows = ws.get_all_values()
                headers_row = all_rows[0]
                try:
                    idx_fecha = headers_row.index("fecha")
                    idx_emp_id = headers_row.index("empleado_id")
                    idx_emp = headers_row.index("empleado_nombre")
                    idx_horas = headers_row.index("horas")
                    idx_motivo = headers_row.index("motivo")
                    idx_aprob = headers_row.index("aprobado_por")
                    idx_rec = headers_row.index("recurrente")
                    idx_ts = headers_row.index("timestamp")
                except ValueError:
                    notify_error("Headers del sheet incompletos. Ve a Setup → Crear/verificar headers.")
                    return

                # Las columnas hora_inicio/hora_fin pueden no existir si el sheet es legacy
                idx_hi = headers_row.index("hora_inicio") if "hora_inicio" in headers_row else None
                idx_hf = headers_row.index("hora_fin") if "hora_fin" in headers_row else None

                if idx_hi is None or idx_hf is None:
                    notify_warning(
                        "Tu sheet no tiene columnas hora_inicio/hora_fin. "
                        "Ve a Setup → 'Crear/verificar headers' para agregarlas automáticamente."
                    )

                changes = 0
                for i, edited in edited_df.iterrows():
                    if edited["Eliminar"]:
                        continue  # los de Eliminar van por otro botón
                    orig_idx = int(edited["_id"])
                    orig = df_recent.iloc[orig_idx]

                    new_fecha = str(edited["Fecha"])
                    new_emp_name = str(edited["Empleado"])
                    new_horas_manual = float(edited["Horas"])
                    new_motivo = str(edited["Motivo"])
                    new_aprob = str(edited["Aprobado por"])
                    new_rec = "TRUE" if edited["Recurrente"] else "FALSE"
                    new_hi_str = str(edited.get("Hora Inicio", "") or "").strip()
                    new_hf_str = str(edited.get("Hora Fin", "") or "").strip()

                    # Si hay HI y HF válidos, recalcular horas automáticamente
                    hi_p = _parse_time(new_hi_str) if new_hi_str else None
                    hf_p = _parse_time(new_hf_str) if new_hf_str else None
                    new_horas_final = new_horas_manual
                    if hi_p and hf_p:
                        mins_hi = time_to_minutes(hi_p)
                        mins_hf = time_to_minutes(hf_p)
                        if mins_hf <= mins_hi:
                            mins_hf += 24 * 60  # turno nocturno
                        diff_min = mins_hf - mins_hi
                        if diff_min > 0:
                            new_horas_final = round(diff_min / 60.0, 2)

                    # Mapear empleado_id por nombre
                    emp_row_match = employees_active[employees_active["nombre"] == new_emp_name]
                    new_emp_id = int(emp_row_match.iloc[0]["id"]) if not emp_row_match.empty else orig.get("empleado_id", "")

                    # Encontrar fila original en el sheet
                    orig_ts = str(orig.get("timestamp", ""))
                    target_row_idx = None
                    for j, srow in enumerate(all_rows[1:], start=2):
                        if (len(srow) > idx_ts and srow[idx_ts] == orig_ts):
                            target_row_idx = j
                            break
                    if target_row_idx is None:
                        continue

                    # Actualizar cada celda
                    ws.update_cell(target_row_idx, idx_fecha + 1, new_fecha)
                    ws.update_cell(target_row_idx, idx_emp_id + 1, new_emp_id)
                    ws.update_cell(target_row_idx, idx_emp + 1, new_emp_name)
                    ws.update_cell(target_row_idx, idx_horas + 1, new_horas_final)
                    ws.update_cell(target_row_idx, idx_motivo + 1, new_motivo)
                    ws.update_cell(target_row_idx, idx_aprob + 1, new_aprob)
                    ws.update_cell(target_row_idx, idx_rec + 1, new_rec)
                    if idx_hi is not None:
                        ws.update_cell(target_row_idx, idx_hi + 1, hi_p.strftime("%H:%M") if hi_p else "")
                    if idx_hf is not None:
                        ws.update_cell(target_row_idx, idx_hf + 1, hf_p.strftime("%H:%M") if hf_p else "")
                    changes += 1

                from core.sheets import invalidate_cache
                invalidate_cache()
                if changes > 0:
                    notify_success(f"{changes} registro(s) actualizados.", title="Cambios guardados")
                    st.rerun()
                else:
                    notify_warning("No hay cambios para guardar.")
            except Exception as e:
                notify_error(f"Error al guardar: {e}")


def _render_detail_view(employees_active: pd.DataFrame):
    """Vista de detalle día/semana/mes."""
    period = st.radio(
        "Período", options=["Hoy", "Esta semana", "Este mes"],
        horizontal=True, label_visibility="collapsed", key="detail_period",
    )

    if period == "Hoy":
        df = get_overtime_today()
        period_label = format_date_long(today_gt())
        days_in_period = 1
    elif period == "Esta semana":
        df = get_overtime_this_week()
        today = today_gt()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        period_label = f"{monday.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')}"
        days_in_period = 7
    else:
        df = get_overtime_this_month()
        period_label = MONTHS_ES[today_gt().month] + f" {today_gt().year}"
        days_in_period = today_gt().day

    total_horas = df["horas"].sum() if not df.empty else 0
    total_registros = len(df)
    empleados_unicos = df["empleado_id"].nunique() if not df.empty else 0
    promedio_dia = total_horas / days_in_period if days_in_period else 0

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">TOTAL HORAS EXTRAS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total_horas:g}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">hrs</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#D97706;margin-right:6px;"></span>
                {period_label}
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">REGISTROS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total_registros}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#16A34A;margin-right:6px;"></span>aprobados</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{empleados_unicos}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">/ {len(employees_active)}</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2563EB;margin-right:6px;"></span>con horas extras</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PROMEDIO / DÍA</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{promedio_dia:.1f}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">hrs</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#0891B2;margin-right:6px;"></span>en el período</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    if df.empty:
        st.info("📭 No hay horas extras registradas en este período.")
        return

    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— DESGLOSE POR EMPLEADO</div>',
        unsafe_allow_html=True,
    )

    breakdown = df.groupby(["empleado_id", "empleado_nombre"], as_index=False).agg(
        horas_total=("horas", "sum"),
        registros=("horas", "count"),
    ).sort_values("horas_total", ascending=False).reset_index(drop=True)

    max_hours = breakdown["horas_total"].max() if not breakdown.empty else 1

    rows_html = []
    for _, row in breakdown.iterrows():
        emp_name = row["empleado_nombre"]
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        if not emp_match.empty:
            pais = emp_match.iloc[0]["pais"]
            iniciales = emp_match.iloc[0]["iniciales"]
            color = emp_match.iloc[0]["color_avatar"]
        else:
            pais = ""
            iniciales = "??"
            color = "#F1F5F9"

        flag = flag_emoji_unicode(pais)
        horas = row["horas_total"]
        regs = row["registros"]
        pct = (horas / max_hours) * 100 if max_hours > 0 else 0

        rows_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <span style="font-size:18px;">{flag}</span>
                <span style="width:36px;height:36px;border-radius:50%;background:{color};display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#475569;">{iniciales}</span>
                <div style="flex:1;">
                    <div style="font-size:14px;font-weight:600;color:#0A0A0A;margin-bottom:6px;">
                        {emp_name}
                        <span style="font-size:11px;color:#94A3B8;font-weight:400;margin-left:8px;">· {regs} {"registros" if regs != 1 else "registro"}</span>
                    </div>
                    <div style="background:#F1F5F9;height:8px;border-radius:4px;overflow:hidden;">
                        <div style="background:linear-gradient(90deg,#D97706,#F59E0B);height:100%;width:{pct}%;border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:80px;">
                    <div style="font-size:24px;font-weight:700;color:#D97706;line-height:1;letter-spacing:-0.5px;">{horas:g}</div>
                    <div style="font-size:10px;color:#94A3B8;letter-spacing:1px;text-transform:uppercase;margin-top:2px;">hrs</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(rows_html), unsafe_allow_html=True)
