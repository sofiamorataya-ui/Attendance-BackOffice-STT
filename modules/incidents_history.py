"""
modules/incidents_history.py
Histórico y reportes de incidencias (sin luz, sin internet, médico, etc.)
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, get_worksheet
from core.config import (
    WS_INCIDENTS, WS_EMPLOYEES, REFRESH_OTHER_TABS,
    INCIDENT_TYPES, INCIDENT_LABELS, INCIDENT_ICONS, INCIDENT_COLORS,
)
from core.time_utils import today_gt, parse_date, parse_time
from core.flags import flag_emoji_unicode, flag_img_inline
from core.notifications import notify_success, notify_error
from core.incidents import (
    load_incidents_df, get_current_duration_minutes, format_duration,
    close_incident,
)
from core.auth import current_user_display_name
from core.business_logic import MONTHS_ES


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="incidents_hist_refresh")

    render_page_title(
        eyebrow="REPORTES",
        title="Incidencias",
        subtitle="Histórico y análisis de reportes durante turno",
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy() if not employees_df.empty else pd.DataFrame()

    df = load_incidents_df()
    if df.empty:
        st.info("📭 No hay incidencias registradas todavía.")
        st.caption("Las incidencias se registran desde el dashboard '🟢 Asistencia en Vivo'.")
        return

    tab_active, tab_history, tab_summary = st.tabs([
        "🚨  Activas ahora",
        "📜  Histórico",
        "📊  Resumen por empleado",
    ])

    with tab_active:
        _render_active_tab(df, employees_active)

    with tab_history:
        _render_history_tab(df, employees_active)

    with tab_summary:
        _render_summary_tab(df, employees_active)


def _render_active_tab(df: pd.DataFrame, employees_active: pd.DataFrame):
    """Incidencias actualmente ACTIVAS con botón Volvió."""
    active = df[df["estado"].astype(str).str.upper() == "ACTIVA"].copy()

    if active.empty:
        st.success("✓ Ninguna incidencia activa en este momento.")
        return

    active = active.sort_values("hi_parsed", ascending=False).reset_index(drop=True)

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:8px 0 16px 0;">'
        f'— {len(active)} INCIDENCIA{"S" if len(active) != 1 else ""} ACTIVA{"S" if len(active) != 1 else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for _, inc in active.iterrows():
        tipo = str(inc.get("tipo", "OTRO"))
        tipo_label = INCIDENT_LABELS.get(tipo, tipo)
        tipo_icon = INCIDENT_ICONS.get(tipo, "❓")
        tipo_color = INCIDENT_COLORS.get(tipo, "#64748B")

        emp_name = inc.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name] if not employees_active.empty else pd.DataFrame()
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag_html = flag_img_inline(pais, size=14)

        hora_inicio = str(inc.get("hora_inicio", ""))
        duration_min = get_current_duration_minutes(hora_inicio)
        duration_str = format_duration(duration_min) if duration_min > 0 else "recién"

        fecha = inc["fecha_parsed"].strftime("%d/%m/%Y") if inc["fecha_parsed"] else ""
        nota = (str(inc.get("nota", "")) or "")
        registrado = str(inc.get("registrado_por", "") or "")

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid {tipo_color};border-radius:8px;
                    padding:18px 22px;margin-bottom:10px;
                    box-shadow:0 2px 8px {tipo_color}22;">
            <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
                <div style="font-size:32px;line-height:1;">{tipo_icon}</div>
                <div style="flex:1;min-width:200px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
                        {flag_html}
                        <strong style="font-size:16px;color:#0A0A0A;">{emp_name}</strong>
                        <span style="display:inline-block;padding:3px 10px;border-radius:4px;
                                     font-size:10px;font-weight:700;letter-spacing:0.5px;
                                     text-transform:uppercase;background:{tipo_color};color:#FFFFFF;">
                            {tipo_label}
                        </span>
                    </div>
                    <div style="font-size:11px;color:#64748B;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.3px;">
                        {fecha} · Desde {hora_inicio} · Reg: {registrado.upper()}
                    </div>
                    {f'<div style="font-size:12px;color:#475569;margin-top:6px;">{nota}</div>' if nota else ''}
                </div>
                <div style="text-align:right;min-width:120px;">
                    <div style="font-size:28px;font-weight:700;color:{tipo_color};
                                line-height:1;letter-spacing:-1px;font-family:'JetBrains Mono',monospace;">
                        {duration_str}
                    </div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:4px;">EN CURSO</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(cards_html), unsafe_allow_html=True)

    # Botones de cerrar
    st.divider()
    st.caption("Cerrar incidencias activas:")

    cols_per_row = 3
    active_rows = active.to_dict("records")
    for i in range(0, len(active_rows), cols_per_row):
        chunk = active_rows[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for j, inc in enumerate(chunk):
            with cols[j]:
                inc_id = inc.get("id", "")
                emp_name = inc.get("empleado_nombre", "")
                if st.button(
                    f"✓ Volvió · {emp_name}",
                    key=f"close_hist_{inc_id}",
                    use_container_width=True,
                ):
                    try:
                        result = close_incident(inc_id, current_user_display_name())
                        if result["success"]:
                            notify_success(
                                f"{emp_name} volvió. Duración: {format_duration(result['duration_minutes'])}",
                                title="Incidencia cerrada"
                            )
                            st.rerun()
                        else:
                            notify_error(result["message"])
                    except Exception as e:
                        notify_error(str(e))


def _render_history_tab(df: pd.DataFrame, employees_active: pd.DataFrame):
    """Tabla histórica con filtros."""
    col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.2, 1])

    with col1:
        date_range = st.date_input(
            "Rango de fechas",
            value=(today_gt() - timedelta(days=30), today_gt()),
            format="DD/MM/YYYY",
            key="inc_hist_dates",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_from, date_to = date_range
        else:
            date_from = date_to = today_gt()

    with col2:
        emp_options = ["Todos"] + sorted(
            employees_active["nombre"].tolist() if not employees_active.empty else []
        )
        emp_filter = st.selectbox("Empleado", options=emp_options, key="inc_hist_emp")

    with col3:
        type_filter = st.selectbox(
            "Tipo",
            options=["Todos"] + INCIDENT_TYPES,
            format_func=lambda x: "Todos" if x == "Todos" else f"{INCIDENT_ICONS.get(x, '?')} {INCIDENT_LABELS.get(x, x)}",
            key="inc_hist_type",
        )

    with col4:
        status_filter = st.selectbox(
            "Estado",
            options=["Todas", "Cerradas", "Activas"],
            key="inc_hist_status",
        )

    # Aplicar filtros
    filtered = df.copy()
    filtered = filtered[
        (filtered["fecha_parsed"] >= date_from) & (filtered["fecha_parsed"] <= date_to)
    ]
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo"] == type_filter]
    if status_filter == "Cerradas":
        filtered = filtered[filtered["estado"].astype(str).str.upper() == "CERRADA"]
    elif status_filter == "Activas":
        filtered = filtered[filtered["estado"].astype(str).str.upper() == "ACTIVA"]

    if filtered.empty:
        st.info("🔎 Sin resultados para los filtros seleccionados.")
        return

    filtered = filtered.sort_values(["fecha_parsed", "hi_parsed"], ascending=False).reset_index(drop=True)

    # KPIs filtrados
    total_min = 0
    for _, row in filtered.iterrows():
        if str(row.get("estado", "")).upper() == "ACTIVA":
            total_min += get_current_duration_minutes(str(row.get("hora_inicio", "")))
        else:
            try:
                total_min += int(row.get("duracion_minutos", 0) or 0)
            except (ValueError, TypeError):
                pass

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0 20px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:16px 18px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:8px;">INCIDENCIAS</div>
            <div style="font-size:30px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1px;">{len(filtered)}</div>
            <div style="margin-top:8px;font-size:10px;color:#64748B;">en el filtro</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:16px 18px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:8px;">TIEMPO TOTAL</div>
            <div style="font-size:30px;font-weight:700;color:#F97316;line-height:1;letter-spacing:-1px;">{format_duration(total_min)}</div>
            <div style="margin-top:8px;font-size:10px;color:#64748B;">{total_min} min acumulados</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:16px 18px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:8px;">EMPLEADOS</div>
            <div style="font-size:30px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1px;">{filtered["empleado_id"].nunique()}</div>
            <div style="margin-top:8px;font-size:10px;color:#64748B;">con al menos 1 reporte</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Tabla
    rows_html = []
    for _, row in filtered.iterrows():
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
        if is_active:
            duration_min = get_current_duration_minutes(hi)
            estado_badge = (
                '<span style="background:#FEE2E2;color:#991B1B;padding:2px 7px;'
                'border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
                'text-transform:uppercase;">ACTIVA</span>'
            )
            tiempo_str = f"{hi} → en curso"
        else:
            try:
                duration_min = int(row.get("duracion_minutos", 0) or 0)
            except (ValueError, TypeError):
                duration_min = 0
            estado_badge = ""
            tiempo_str = f"{hi} → {hf}" if hf else hi

        nota = (str(row.get("nota", "") or ""))[:60]
        if len(str(row.get("nota", "") or "")) > 60:
            nota += "..."

        rows_html.append(
            f'<tr>'
            f'<td class="ih-cell ih-mono">{fecha_str}</td>'
            f'<td class="ih-cell">{flag_html}<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong>{" " + estado_badge if estado_badge else ""}</td>'
            f'<td class="ih-cell"><span style="margin-right:4px;font-size:14px;">{tipo_icon}</span>'
            f'<span style="display:inline-block;padding:3px 8px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span></td>'
            f'<td class="ih-cell ih-mono">{tiempo_str}</td>'
            f'<td class="ih-cell" style="text-align:center;">'
            f'<strong style="font-size:14px;color:{tipo_color};font-family:\'JetBrains Mono\',monospace;">{format_duration(duration_min)}</strong></td>'
            f'<td class="ih-cell" style="font-size:11px;color:#475569;">{nota or "—"}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.ih-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.ih-table th{padding:12px 14px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.ih-cell{padding:12px 14px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.ih-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:8px;">'
        '<table class="ih-table"><thead><tr>'
        '<th>Fecha</th><th>Empleado</th><th>Tipo</th>'
        '<th>Horario</th><th style="text-align:center;">Duración</th><th>Nota</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _render_summary_tab(df: pd.DataFrame, employees_active: pd.DataFrame):
    """Resumen agregado por empleado."""
    col1, col2 = st.columns([1, 3])
    with col1:
        period = st.selectbox(
            "Período",
            options=["Hoy", "Esta semana", "Este mes", "Últimos 90 días", "Todo el año"],
            index=2,
            key="inc_sum_period",
        )

    today = today_gt()
    if period == "Hoy":
        date_from = today
    elif period == "Esta semana":
        date_from = today - timedelta(days=today.weekday())
    elif period == "Este mes":
        date_from = today.replace(day=1)
    elif period == "Últimos 90 días":
        date_from = today - timedelta(days=90)
    else:
        date_from = today.replace(month=1, day=1)

    filtered = df[df["fecha_parsed"] >= date_from].copy()

    if filtered.empty:
        st.info(f"📭 Sin incidencias en el período '{period.lower()}'.")
        return

    # Calcular duración por fila
    def _row_duration(row):
        if str(row.get("estado", "")).upper() == "ACTIVA":
            return get_current_duration_minutes(str(row.get("hora_inicio", "")))
        try:
            return int(row.get("duracion_minutos", 0) or 0)
        except (ValueError, TypeError):
            return 0

    filtered["duracion_calc"] = filtered.apply(_row_duration, axis=1)

    summary = filtered.groupby(
        ["empleado_id", "empleado_nombre"], as_index=False,
    ).agg(
        incidencias=("id", "count"),
        minutos_totales=("duracion_calc", "sum"),
    ).sort_values("minutos_totales", ascending=False).reset_index(drop=True)

    # Tipo predominante por empleado
    tipo_counts = filtered.groupby(["empleado_id", "tipo"]).size().reset_index(name="count")
    top_tipo_por_emp = tipo_counts.sort_values(["empleado_id", "count"], ascending=[True, False]).groupby("empleado_id").first().reset_index()
    top_tipo_map = dict(zip(top_tipo_por_emp["empleado_id"].astype(str), top_tipo_por_emp["tipo"]))

    max_min = summary["minutos_totales"].max() if not summary.empty else 1

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        f'— RESUMEN · {period.upper()}'
        f'</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for _, row in summary.iterrows():
        emp_name = row["empleado_nombre"]
        emp_match = employees_active[employees_active["nombre"] == emp_name] if not employees_active.empty else pd.DataFrame()
        if not emp_match.empty:
            pais = emp_match.iloc[0]["pais"]
            iniciales = emp_match.iloc[0]["iniciales"]
            color = emp_match.iloc[0]["color_avatar"]
        else:
            pais = ""
            iniciales = "??"
            color = "#F1F5F9"

        flag_html = flag_img_inline(pais, size=14)
        incidencias = int(row["incidencias"])
        minutos = int(row["minutos_totales"])
        pct = (minutos / max_min) * 100 if max_min > 0 else 0

        top_tipo = top_tipo_map.get(str(row["empleado_id"]), "OTRO")
        top_tipo_label = INCIDENT_LABELS.get(top_tipo, top_tipo)
        top_tipo_icon = INCIDENT_ICONS.get(top_tipo, "❓")
        top_tipo_color = INCIDENT_COLORS.get(top_tipo, "#64748B")

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;
                    padding:16px 20px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
                {flag_html}
                <span style="width:36px;height:36px;border-radius:50%;background:{color};
                             display:inline-flex;align-items:center;justify-content:center;
                             font-weight:700;font-size:12px;color:#475569;">{iniciales}</span>
                <div style="flex:1;min-width:160px;">
                    <div style="font-size:14px;font-weight:700;color:#0A0A0A;margin-bottom:4px;">
                        {emp_name}
                    </div>
                    <div style="font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.3px;">
                        {incidencias} incidencia{"s" if incidencias != 1 else ""} · Mayor: {top_tipo_icon} {top_tipo_label}
                    </div>
                </div>
                <div style="flex:2;min-width:180px;">
                    <div style="background:#F1F5F9;height:8px;border-radius:4px;overflow:hidden;">
                        <div style="background:{top_tipo_color};height:100%;width:{pct}%;border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:80px;">
                    <div style="font-size:20px;font-weight:700;color:{top_tipo_color};
                                line-height:1;letter-spacing:-0.5px;
                                font-family:'JetBrains Mono',monospace;">{format_duration(minutos)}</div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:2px;">acumulado</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(cards_html), unsafe_allow_html=True)
