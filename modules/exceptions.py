"""
modules/exceptions.py
Permisos y Ausencias (no vacaciones).
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import WS_PERMITS, WS_EMPLOYEES, PERMIT_TYPES, REFRESH_OTHER_TABS
from core.time_utils import today_gt, now_gt, format_date_long, parse_date
from core.auth import current_user_display_name
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error


PERMIT_LABELS = {
    "PERMISO_PERSONAL": "Permiso personal",
    "INCAPACIDAD_MEDICA": "Incapacidad médica",
    "DUELO": "Duelo",
    "OTRO": "Otro",
}

PERMIT_COLORS = {
    "PERMISO_PERSONAL": "#2563EB",
    "INCAPACIDAD_MEDICA": "#7C2D12",
    "DUELO": "#475569",
    "OTRO": "#64748B",
}


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="permits_refresh")

    render_page_title(
        eyebrow="REGISTRO",
        title="Permisos y ausencias",
        subtitle=format_date_long(today_gt()),
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if employees_df.empty:
        st.warning("No hay empleados cargados.")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    # KPIs: permisos activos HOY
    permits_df = _load_permits()
    today = today_gt()
    active_today = _count_active_on(permits_df, today)

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">ACTIVOS HOY</div>
            <div style="font-size:36px;font-weight:700;color:#2563EB;line-height:1;letter-spacing:-1.5px;">{active_today}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2563EB;margin-right:6px;"></span>
                permisos/incapacidades vigentes
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">ESTE MES</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{_count_in_month(permits_df, today.year, today.month)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">registros creados</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">ESTE AÑO</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{_count_in_year(permits_df, today.year)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">registros totales</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    tab_new, tab_history = st.tabs(["➕  Nuevo registro", "📜  Histórico"])

    with tab_new:
        _render_new_form(employees_active)

    with tab_history:
        _render_history(employees_active, permits_df)


def _load_permits():
    df = read_worksheet(WS_PERMITS)
    if df.empty:
        return df
    df["fi_parsed"] = df["fecha_inicio"].apply(parse_date)
    df["ff_parsed"] = df["fecha_fin"].apply(parse_date)
    df = df[df["fi_parsed"].notna() & df["ff_parsed"].notna()]
    return df.reset_index(drop=True)


def _count_active_on(df: pd.DataFrame, target_date: date) -> int:
    if df.empty:
        return 0
    mask = df.apply(lambda r: r["fi_parsed"] <= target_date <= r["ff_parsed"], axis=1)
    return int(mask.sum())


def _count_in_month(df: pd.DataFrame, year: int, month: int) -> int:
    if df.empty:
        return 0
    mask = df["fi_parsed"].apply(lambda d: d.year == year and d.month == month)
    return int(mask.sum())


def _count_in_year(df: pd.DataFrame, year: int) -> int:
    if df.empty:
        return 0
    mask = df["fi_parsed"].apply(lambda d: d.year == year)
    return int(mask.sum())


def _render_new_form(employees_active: pd.DataFrame):
    import uuid as _uuid
    from core.time_utils import parse_time as _parse_time

    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {"id": int(emp["id"]), "nombre": emp["nombre"]}

    # Selector de modalidad (FUERA del form para que el form reaccione al cambio)
    modalidad = st.radio(
        "Modalidad del permiso",
        options=["DIA_COMPLETO", "PARCIAL_CON_FIN", "PARCIAL_ABIERTO"],
        format_func=lambda x: {
            "DIA_COMPLETO": "📅  Día completo (uno o más días)",
            "PARCIAL_CON_FIN": "⏱️  Parcial con hora fin (sale temprano / llega tarde)",
            "PARCIAL_ABIERTO": "🚪  Parcial abierto (sin hora fin conocida — se cierra después)",
        }[x],
        key="per_modalidad",
        horizontal=False,
    )

    with st.form("new_permit_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            emp_display = st.selectbox(
                "Empleado", options=list(emp_options.keys()), key="per_emp",
            )
        with col2:
            tipo = st.selectbox(
                "Tipo",
                options=PERMIT_TYPES,
                format_func=lambda x: PERMIT_LABELS.get(x, x),
                key="per_tipo",
            )

        if modalidad == "DIA_COMPLETO":
            col3, col4 = st.columns(2)
            with col3:
                fecha_inicio = st.date_input(
                    "Fecha inicio", value=today_gt(),
                    format="DD/MM/YYYY", key="per_from",
                )
            with col4:
                fecha_fin = st.date_input(
                    "Fecha fin", value=today_gt(),
                    format="DD/MM/YYYY", key="per_to",
                )
            hora_inicio_str = ""
            hora_fin_str = ""

        elif modalidad == "PARCIAL_CON_FIN":
            fecha_inicio = st.date_input(
                "Fecha", value=today_gt(),
                format="DD/MM/YYYY", key="per_fecha_pc",
            )
            fecha_fin = fecha_inicio
            col_hi, col_hf = st.columns(2)
            with col_hi:
                hora_inicio_str = st.text_input(
                    "Hora inicio (HH:MM)",
                    value=now_gt().strftime("%H:%M"),
                    placeholder="06:00",
                    key="per_hi", max_chars=8,
                )
            with col_hf:
                hora_fin_str = st.text_input(
                    "Hora fin (HH:MM)",
                    value="",
                    placeholder="15:00",
                    key="per_hf", max_chars=8,
                )

        else:  # PARCIAL_ABIERTO
            fecha_inicio = st.date_input(
                "Fecha", value=today_gt(),
                format="DD/MM/YYYY", key="per_fecha_pa",
            )
            fecha_fin = fecha_inicio
            hora_inicio_str = st.text_input(
                "Hora inicio (HH:MM)",
                value=now_gt().strftime("%H:%M"),
                placeholder="06:00",
                key="per_hi_open", max_chars=8,
            )
            hora_fin_str = ""
            st.caption("⚠️  Sin hora fin: el permiso queda ACTIVO hasta que lo cierres manualmente.")

        motivo = st.text_area(
            "Motivo / descripción",
            placeholder="Ej: Cita IGSS, Trámite migratorio, Sale temprano por asunto familiar...",
            key="per_motivo",
            max_chars=400,
        )

        submitted = st.form_submit_button(
            "Registrar permiso", use_container_width=True, type="primary",
        )

        if submitted:
            # Validaciones
            if modalidad == "DIA_COMPLETO" and fecha_fin < fecha_inicio:
                notify_error("La fecha 'fin' no puede ser anterior a 'inicio'.")
                return
            if not motivo.strip():
                notify_error("El motivo es obligatorio.")
                return

            hi_parsed = _parse_time(hora_inicio_str) if hora_inicio_str else None
            hf_parsed = _parse_time(hora_fin_str) if hora_fin_str else None

            if modalidad == "PARCIAL_CON_FIN":
                if not hi_parsed:
                    notify_error(f"Hora inicio inválida: '{hora_inicio_str}'")
                    return
                if not hf_parsed:
                    notify_error(f"Hora fin inválida: '{hora_fin_str}'")
                    return
                from core.time_utils import time_to_minutes
                if time_to_minutes(hf_parsed) <= time_to_minutes(hi_parsed):
                    notify_error("La hora fin debe ser posterior a la hora inicio.")
                    return

            if modalidad == "PARCIAL_ABIERTO" and not hi_parsed:
                notify_error(f"Hora inicio inválida: '{hora_inicio_str}'")
                return

            try:
                selected = emp_options[emp_display]
                timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
                id_permiso = f"PER-{now_gt().strftime('%Y%m%d%H%M%S')}-{_uuid.uuid4().hex[:6].upper()}"

                # Estado: ACTIVO si parcial abierto, CERRADO en otros casos
                if modalidad == "PARCIAL_ABIERTO":
                    estado = "ACTIVO"
                else:
                    estado = "CERRADO"

                row = [
                    selected["id"], selected["nombre"],
                    fecha_inicio.strftime("%Y-%m-%d"),
                    fecha_fin.strftime("%Y-%m-%d"),
                    tipo, motivo,
                    current_user_display_name(), timestamp,
                    modalidad,
                    hi_parsed.strftime("%H:%M") if hi_parsed else "",
                    hf_parsed.strftime("%H:%M") if hf_parsed else "",
                    estado,
                    id_permiso,
                ]
                append_row(WS_PERMITS, row)
                from core.sheets import invalidate_cache
                invalidate_cache()

                if modalidad == "DIA_COMPLETO":
                    days = (fecha_fin - fecha_inicio).days + 1
                    msg = (
                        f"{selected['nombre']} · {PERMIT_LABELS.get(tipo)} · "
                        f"{fecha_inicio.strftime('%d/%m')} – {fecha_fin.strftime('%d/%m/%Y')} "
                        f"({days} día{'s' if days != 1 else ''})"
                    )
                elif modalidad == "PARCIAL_CON_FIN":
                    msg = (
                        f"{selected['nombre']} · {PERMIT_LABELS.get(tipo)} · "
                        f"{fecha_inicio.strftime('%d/%m')} de "
                        f"{hi_parsed.strftime('%H:%M')} a {hf_parsed.strftime('%H:%M')}"
                    )
                else:
                    msg = (
                        f"{selected['nombre']} · {PERMIT_LABELS.get(tipo)} · "
                        f"ACTIVO desde {hi_parsed.strftime('%H:%M')}"
                    )

                notify_success(msg, title="Permiso registrado")
                st.rerun()
            except Exception as e:
                notify_error(str(e))


def _render_history(employees_active: pd.DataFrame, df: pd.DataFrame):
    if df.empty:
        st.info("📭 No hay permisos registrados todavía.")
        return

    # ============================================================
    # WARNING: Permisos sin modalidad (legacy → considerados DÍA COMPLETO)
    # ============================================================
    if "modalidad" in df.columns:
        legacy_mask = df["modalidad"].fillna("").astype(str).str.strip() == ""
        n_legacy = int(legacy_mask.sum())
        if n_legacy > 0:
            st.warning(
                f"⚠️ Hay **{n_legacy} permiso(s) sin modalidad** (registros viejos). "
                f"Estos se interpretan como DÍA COMPLETO y oscurecen toda la barra del empleado en el dashboard. "
                f"Si alguno corresponde a un permiso por horas, **elimínalo** abajo y vuelve a crearlo con modalidad correcta."
            )

    # ============================================================
    # FILTROS
    # ============================================================
    col1, col2, col3 = st.columns([1.3, 1.3, 1.3])
    with col1:
        emp_filter = st.selectbox(
            "Empleado",
            options=["Todos"] + sorted(employees_active["nombre"].tolist()),
            key="per_hist_emp",
        )
    with col2:
        type_filter = st.selectbox(
            "Tipo",
            options=["Todos"] + PERMIT_TYPES,
            format_func=lambda x: "Todos" if x == "Todos" else PERMIT_LABELS.get(x, x),
            key="per_hist_type",
        )
    with col3:
        modality_filter = st.selectbox(
            "Modalidad",
            options=["Todas", "DIA_COMPLETO", "PARCIAL_CON_FIN", "PARCIAL_ABIERTO", "(sin modalidad)"],
            key="per_hist_mod",
        )

    filtered = df.copy()
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo"] == type_filter]
    if modality_filter != "Todas":
        if modality_filter == "(sin modalidad)":
            filtered = filtered[filtered.get("modalidad", "").fillna("").astype(str).str.strip() == ""]
        else:
            filtered = filtered[filtered.get("modalidad", "").astype(str) == modality_filter]

    if filtered.empty:
        st.info("🔎 Sin resultados.")
        return

    filtered = filtered.sort_values("fi_parsed", ascending=False).reset_index(drop=True)

    # ============================================================
    # TABLA con columna modalidad y horario
    # ============================================================
    rows_html = []
    for _, row in filtered.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag = flag_emoji_unicode(pais)

        tipo = row.get("tipo", "")
        tipo_label = PERMIT_LABELS.get(tipo, tipo)
        tipo_color = PERMIT_COLORS.get(tipo, "#64748B")

        fi = row["fi_parsed"].strftime("%d/%m/%Y") if row["fi_parsed"] else ""
        ff = row["ff_parsed"].strftime("%d/%m/%Y") if row["ff_parsed"] else ""
        days = (row["ff_parsed"] - row["fi_parsed"]).days + 1 if row["fi_parsed"] and row["ff_parsed"] else 0
        rango = f"{fi}" if fi == ff else f"{fi} → {ff}"

        # Modalidad
        modalidad = str(row.get("modalidad", "") or "").strip()
        hi = str(row.get("hora_inicio", "") or "")
        hf = str(row.get("hora_fin", "") or "")

        if not modalidad:
            mod_html = (
                '<span style="display:inline-block;padding:3px 8px;border-radius:3px;'
                'background:#FEE2E2;color:#991B1B;font-size:9px;font-weight:700;'
                'letter-spacing:0.5px;text-transform:uppercase;">⚠ SIN MODALIDAD</span>'
                '<div style="font-size:10px;color:#94A3B8;margin-top:2px;">→ se toma como día completo</div>'
            )
        elif modalidad == "DIA_COMPLETO":
            mod_html = (
                '<span style="display:inline-block;padding:3px 8px;border-radius:3px;'
                'background:#E0E7FF;color:#3730A3;font-size:9px;font-weight:700;'
                'letter-spacing:0.5px;text-transform:uppercase;">📅 DÍA COMPLETO</span>'
            )
        elif modalidad == "PARCIAL_CON_FIN":
            mod_html = (
                '<span style="display:inline-block;padding:3px 8px;border-radius:3px;'
                'background:#DBEAFE;color:#1E40AF;font-size:9px;font-weight:700;'
                'letter-spacing:0.5px;text-transform:uppercase;">⏱ PARCIAL</span>'
                f'<div style="font-size:11px;color:#475569;margin-top:2px;font-family:\'JetBrains Mono\',monospace;">'
                f'{hi} → {hf}</div>'
            )
        elif modalidad == "PARCIAL_ABIERTO":
            estado = str(row.get("estado", "") or "").upper()
            estado_badge = "ACTIVO" if estado == "ACTIVO" else "CERRADO"
            estado_color = "#16A34A" if estado == "ACTIVO" else "#94A3B8"
            mod_html = (
                '<span style="display:inline-block;padding:3px 8px;border-radius:3px;'
                'background:#FEF3C7;color:#92400E;font-size:9px;font-weight:700;'
                'letter-spacing:0.5px;text-transform:uppercase;">▶ ABIERTO</span>'
                f'<div style="font-size:11px;color:#475569;margin-top:2px;font-family:\'JetBrains Mono\',monospace;">'
                f'{hi} → {hf or "?"} <span style="color:{estado_color};">· {estado_badge}</span></div>'
            )
        else:
            mod_html = f'<span style="color:#94A3B8;font-size:10px;">{modalidad}</span>'

        is_active = row["fi_parsed"] <= today_gt() <= row["ff_parsed"]
        active_badge = (
            '<span style="background:#16A34A22;color:#15803D;padding:2px 6px;'
            'border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
            'text-transform:uppercase;margin-left:6px;">ACTIVO</span>'
            if is_active else ""
        )

        motivo = (row.get("motivo", "") or "")[:80]
        if len(row.get("motivo", "") or "") > 80:
            motivo += "..."

        rows_html.append(
            f'<tr>'
            f'<td class="per-cell per-mono">{rango}</td>'
            f'<td class="per-cell" style="text-align:center;font-weight:700;color:#0A0A0A;">{days}</td>'
            f'<td class="per-cell"><span style="margin-right:6px;">{flag}</span>'
            f'<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong>{active_badge}</td>'
            f'<td class="per-cell">'
            f'<span style="display:inline-block;padding:4px 10px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span></td>'
            f'<td class="per-cell">{mod_html}</td>'
            f'<td class="per-cell" style="font-size:12px;color:#475569;">{motivo}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.per-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.per-table th{padding:12px 16px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.per-cell{padding:14px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;vertical-align:top;}'
        '.per-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:12px;">'
        '<table class="per-table"><thead><tr>'
        '<th>Rango</th><th style="text-align:center;">Días</th>'
        '<th>Empleado</th><th>Tipo</th><th>Modalidad / Horario</th><th>Motivo</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ============================================================
    # ELIMINACIÓN (siempre visible, no oculta en expander)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '🗑️ — ELIMINAR REGISTRO'
        '</div>',
        unsafe_allow_html=True,
    )

    delete_options = {"— Selecciona un registro —": None}
    for _, row in filtered.iterrows():
        fi = row["fi_parsed"].strftime("%d/%m/%Y") if row["fi_parsed"] else ""
        emp = row.get("empleado_nombre", "")
        tipo = PERMIT_LABELS.get(row.get("tipo", ""), "")
        modalidad = str(row.get("modalidad", "") or "").strip() or "SIN MODALIDAD"
        hi = str(row.get("hora_inicio", "") or "")
        hf = str(row.get("hora_fin", "") or "")
        horario_str = f"({hi}–{hf})" if hi or hf else ""
        key = f"{fi} · {emp} · {tipo} · {modalidad} {horario_str}".strip()
        delete_options[key] = row

    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        selected_key = st.selectbox(
            "Registro a eliminar",
            options=list(delete_options.keys()),
            key="per_del",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button(
            "🗑️ Eliminar",
            type="primary",
            key="per_del_btn",
            use_container_width=True,
            disabled=(delete_options[selected_key] is None),
        ):
            try:
                selected = delete_options[selected_key]
                sheet_row_idx = _find_permit_row_idx(selected)
                if sheet_row_idx:
                    delete_row(WS_PERMITS, sheet_row_idx)
                    from core.sheets import invalidate_cache
                    invalidate_cache()
                    notify_success("Permiso eliminado.")
                    st.rerun()
                else:
                    notify_error("No se encontró el registro en el sheet.")
            except Exception as e:
                notify_error(str(e))


def _find_permit_row_idx(target_row):
    ws = get_worksheet(WS_PERMITS)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return None
    headers = all_rows[0]
    try:
        idx_fi = headers.index("fecha_inicio")
        idx_emp_id = headers.index("empleado_id")
        idx_ts = headers.index("timestamp")
    except ValueError:
        return None
    target_fi = target_row.get("fecha_inicio")
    target_emp_id = str(target_row.get("empleado_id"))
    target_ts = target_row.get("timestamp")
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > max(idx_fi, idx_emp_id, idx_ts):
            if (row[idx_fi] == target_fi
                and str(row[idx_emp_id]) == target_emp_id
                and row[idx_ts] == target_ts):
                return i
    return None


# ============================================================
# API PÚBLICA: permisos parciales (consumida desde dashboard)
# ============================================================
def load_partial_permits_for_date(target_date):
    """
    Devuelve un DataFrame con TODOS los permisos parciales (PARCIAL_CON_FIN y
    PARCIAL_ABIERTO) que aplican a la fecha indicada.
    Para PARCIAL_CON_FIN: aplica si target_date == fecha_inicio
    Para PARCIAL_ABIERTO: aplica si estado == ACTIVO y fecha_inicio <= target_date
    """
    df = _load_permits()
    if df.empty:
        return df

    # Solo modalidades parciales
    if "modalidad" not in df.columns:
        return df.iloc[0:0]

    parciales = df[df["modalidad"].isin(["PARCIAL_CON_FIN", "PARCIAL_ABIERTO"])].copy()
    if parciales.empty:
        return parciales

    # Filtrar por fecha
    def _aplica(row):
        modalidad = str(row.get("modalidad", "")).upper()
        if modalidad == "PARCIAL_CON_FIN":
            return row["fi_parsed"] == target_date
        if modalidad == "PARCIAL_ABIERTO":
            estado = str(row.get("estado", "")).upper()
            return estado == "ACTIVO" and row["fi_parsed"] <= target_date
        return False

    mask = parciales.apply(_aplica, axis=1)
    return parciales[mask].reset_index(drop=True)


def get_active_partial_permit_for_employee(employee_id, target_date=None):
    """Devuelve el permiso PARCIAL_ABIERTO activo del empleado (o None)."""
    target_date = target_date or today_gt()
    df = _load_permits()
    if df.empty or "modalidad" not in df.columns:
        return None
    match = df[
        (df["empleado_id"].astype(str) == str(employee_id))
        & (df["modalidad"] == "PARCIAL_ABIERTO")
        & (df["estado"].astype(str).str.upper() == "ACTIVO")
        & (df["fi_parsed"] <= target_date)
    ]
    if match.empty:
        return None
    match = match.sort_values("timestamp", ascending=False)
    return match.iloc[0]


def close_partial_permit(id_permiso: str, hora_fin, closed_by: str):
    """Cierra un permiso PARCIAL_ABIERTO indicando la hora fin."""
    from datetime import time as _t
    ws = get_worksheet(WS_PERMITS)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return {"success": False, "message": "No hay permisos en el sheet."}

    headers = all_rows[0]
    try:
        idx_id = headers.index("id_permiso")
        idx_hf = headers.index("hora_fin")
        idx_estado = headers.index("estado")
    except ValueError as e:
        return {"success": False, "message": f"Headers inválidos: {e}"}

    target_row_idx = None
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > idx_id and row[idx_id] == id_permiso:
            target_row_idx = i
            break

    if target_row_idx is None:
        return {"success": False, "message": "Permiso no encontrado."}

    if not isinstance(hora_fin, _t):
        return {"success": False, "message": "Hora fin inválida."}

    ws.update_cell(target_row_idx, idx_hf + 1, hora_fin.strftime("%H:%M"))
    ws.update_cell(target_row_idx, idx_estado + 1, "CERRADO")
    from core.sheets import invalidate_cache
    invalidate_cache()

    return {"success": True, "message": f"Permiso cerrado a las {hora_fin.strftime('%H:%M')}."}


def register_partial_permit_now(employee_id, employee_name, tipo, motivo, registered_by):
    """Registra un permiso PARCIAL_ABIERTO con hora_inicio = ahora."""
    import uuid as _uuid
    from core.sheets import invalidate_cache

    now = now_gt()
    hi_str = now.strftime("%H:%M")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    fecha_str = now.strftime("%Y-%m-%d")
    id_permiso = f"PER-{now.strftime('%Y%m%d%H%M%S')}-{_uuid.uuid4().hex[:6].upper()}"

    row = [
        employee_id, employee_name, fecha_str, fecha_str,
        tipo, motivo, registered_by, timestamp,
        "PARCIAL_ABIERTO", hi_str, "", "ACTIVO", id_permiso,
    ]
    append_row(WS_PERMITS, row)
    invalidate_cache()

    return {
        "success": True,
        "message": f"Permiso ACTIVO iniciado para {employee_name} a las {hi_str}.",
        "id_permiso": id_permiso,
    }
