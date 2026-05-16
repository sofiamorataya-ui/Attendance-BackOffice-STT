
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
    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {"id": int(emp["id"]), "nombre": emp["nombre"]}

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

        col3, col4 = st.columns(2)
        with col3:
            fecha_inicio = st.date_input(
                "Fecha inicio",
                value=today_gt(),
                format="DD/MM/YYYY",
                key="per_from",
            )
        with col4:
            fecha_fin = st.date_input(
                "Fecha fin",
                value=today_gt(),
                format="DD/MM/YYYY",
                key="per_to",
            )

        motivo = st.text_area(
            "Motivo / descripción",
            placeholder="Ej: Trámite migratorio, cirugía menor, fallecimiento familiar...",
            key="per_motivo",
            max_chars=400,
        )

        submitted = st.form_submit_button(
            "Registrar permiso", use_container_width=True, type="primary",
        )

        if submitted:
            if fecha_fin < fecha_inicio:
                notify_error("La fecha 'fin' no puede ser anterior a 'inicio'.")
            elif not motivo.strip():
                notify_error("El motivo es obligatorio.")
            else:
                try:
                    selected = emp_options[emp_display]
                    timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
                    row = [
                        selected["id"], selected["nombre"],
                        fecha_inicio.strftime("%Y-%m-%d"),
                        fecha_fin.strftime("%Y-%m-%d"),
                        tipo, motivo,
                        current_user_display_name(), timestamp,
                    ]
                    append_row(WS_PERMITS, row)
                    days = (fecha_fin - fecha_inicio).days + 1
                    notify_success(
                        f"{selected['nombre']} · {PERMIT_LABELS.get(tipo)} · "
                        f"{fecha_inicio.strftime('%d/%m')} – {fecha_fin.strftime('%d/%m/%Y')} "
                        f"({days} día{'s' if days != 1 else ''})",
                        title="Permiso registrado"
                    )
                except Exception as e:
                    notify_error(str(e))


def _render_history(employees_active: pd.DataFrame, df: pd.DataFrame):
    if df.empty:
        st.info("📭 No hay permisos registrados todavía.")
        return

    col1, col2, _ = st.columns([1.3, 1.3, 1])
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

    filtered = df.copy()
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo"] == type_filter]

    if filtered.empty:
        st.info("🔎 Sin resultados.")
        return

    filtered = filtered.sort_values("fi_parsed", ascending=False).reset_index(drop=True)

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

        # Activo si hoy está en el rango
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
        aprobado = row.get("aprobado_por", "")

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
            f'<td class="per-cell" style="font-size:12px;color:#475569;">{motivo}</td>'
            f'<td class="per-cell per-mono" style="color:#94A3B8;text-transform:uppercase;">{aprobado}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.per-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.per-table th{padding:12px 16px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.per-cell{padding:14px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.per-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:12px;">'
        '<table class="per-table"><thead><tr>'
        '<th>Rango</th><th style="text-align:center;">Días</th>'
        '<th>Empleado</th><th>Tipo</th><th>Motivo</th><th>Aprobó</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # Eliminación
    with st.expander("🗑️  Eliminar registro"):
        delete_options = {}
        for _, row in filtered.iterrows():
            fi = row["fi_parsed"].strftime("%d/%m/%Y") if row["fi_parsed"] else ""
            emp = row.get("empleado_nombre", "")
            tipo = PERMIT_LABELS.get(row.get("tipo", ""), "")
            key = f"{fi} · {emp} · {tipo}"
            delete_options[key] = row

        if delete_options:
            selected_key = st.selectbox(
                "Registro a eliminar", options=list(delete_options.keys()), key="per_del",
            )
            if st.button("Eliminar", type="primary", key="per_del_btn"):
                try:
                    selected = delete_options[selected_key]
                    sheet_row_idx = _find_permit_row_idx(selected)
                    if sheet_row_idx:
                        delete_row(WS_PERMITS, sheet_row_idx)
                        notify_success("Permiso eliminado.")
                        st.rerun()
                    else:
                        notify_error("No se encontró el registro.")
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
