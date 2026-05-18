"""
modules/incidents_history.py
Histórico y análisis de Incidencias con filtros globales día/semana/mes/año.

Incluye dos rankings paralelos:
- TOP POR CANTIDAD (frecuencia de reportes)
- TOP POR TIEMPO (minutos acumulados)
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta, time as _t

from core.ui import render_page_title
from core.sheets import read_worksheet
from core.config import (
    WS_INCIDENTS, WS_EMPLOYEES,
    INCIDENT_TYPES, INCIDENT_LABELS, INCIDENT_ICONS, INCIDENT_COLORS,
)
from core.time_utils import today_gt, now_gt, parse_date, parse_time
from core.flags import flag_emoji_unicode, flag_img_inline
from core.notifications import notify_success, notify_error
from core.incidents import (
    load_incidents_df, get_current_duration_minutes, format_duration,
    close_incident, compute_row_duration,
)
from core.auth import current_user_display_name
from core.filters import render_period_selector


def render():
    render_page_title(
        eyebrow="REPORTES",
        title="Incidencias",
        subtitle="Histórico, rankings y análisis de reportes durante turno",
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy() if not employees_df.empty else pd.DataFrame()

    df_full = load_incidents_df()
    if df_full.empty:
        st.info("📭 No hay incidencias registradas todavía.")
        st.caption("Las incidencias se registran desde el dashboard '🟢 Asistencia en Vivo'.")
        return

    # ============================================================
    # FILTRO GLOBAL DE PERÍODO
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:8px 0 8px 0;">'
        '— FILTRO DE PERÍODO'
        '</div>',
        unsafe_allow_html=True,
    )
    period_kind, date_from, date_to, period_label = render_period_selector("inc_hist")
    st.divider()

    # Aplicar filtro
    df = df_full[
        (df_full["fecha_parsed"] >= date_from) & (df_full["fecha_parsed"] <= date_to)
    ].copy()

    if df.empty:
        st.info(f"📭 Sin incidencias en {period_label.lower()}.")
        return

    df["duracion_calc"] = df.apply(compute_row_duration, axis=1)

    tab_active, tab_rankings, tab_table = st.tabs([
        "🚨  Activas ahora",
        "🏆  Rankings",
        "📜  Detalle del período",
    ])

    with tab_active:
        _render_active_tab(df_full, employees_active)

    with tab_rankings:
        _render_rankings_tab(df, employees_active, period_label)

    with tab_table:
        _render_table_tab(df, employees_active, period_label)


# ============================================================
# TAB: ACTIVAS AHORA (independiente del filtro de período)
# ============================================================
def _render_active_tab(df_full: pd.DataFrame, employees_active: pd.DataFrame):
    """Incidencias actualmente activas con botón Volvió y hora fin manual."""
    today = today_gt()
    active = df_full[
        (df_full["fecha_parsed"] == today)
        & (df_full["estado"].astype(str).str.upper() == "ACTIVA")
    ].copy()

    if active.empty:
        st.success("✓ Ninguna incidencia activa en este momento.")
        return

    active = active.sort_values("hi_parsed", ascending=False).reset_index(drop=True)

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:8px 0 16px 0;">'
        f'— {len(active)} ACTIVA{"S" if len(active) != 1 else ""} (HOY)'
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

    # Cerrar incidencias con hora fin manual
    st.divider()
    st.caption("Cerrar incidencias activas (indica hora fin):")
    for _, inc in active.iterrows():
        inc_id = inc.get("id", "")
        emp_name = inc.get("empleado_nombre", "")
        tipo = INCIDENT_LABELS.get(str(inc.get("tipo", "")), "")
        hora_inicio_str = str(inc.get("hora_inicio", ""))

        col_info, col_time, col_btn = st.columns([2, 1.2, 1])
        with col_info:
            st.markdown(
                f'<div style="padding-top:8px;font-size:13px;">'
                f'<strong>{emp_name}</strong> · {tipo} · '
                f'<span style="font-family:\'JetBrains Mono\',monospace;color:#64748B;">'
                f'desde {hora_inicio_str}</span></div>',
                unsafe_allow_html=True,
            )
        with col_time:
            hora_fin_close = st.time_input(
                "Hora fin",
                value=now_gt().time().replace(second=0, microsecond=0),
                step=300,
                key=f"htabclose_time_{inc_id}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("✓ Volvió", key=f"htabbtn_close_{inc_id}", use_container_width=True):
                try:
                    result = close_incident(
                        inc_id, current_user_display_name(),
                        hora_fin=hora_fin_close,
                    )
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


# ============================================================
# TAB: RANKINGS
# ============================================================
def _render_rankings_tab(df: pd.DataFrame, employees_active: pd.DataFrame, period_label: str):
    """Dos rankings: por cantidad y por tiempo total."""

    # KPIs generales del período
    total_inc = len(df)
    total_min = int(df["duracion_calc"].sum())
    empleados_afectados = df["empleado_id"].nunique()
    promedio_min = total_min // total_inc if total_inc else 0

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:8px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">INCIDENCIAS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total_inc}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">{period_label}</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">TIEMPO TOTAL</div>
            <div style="font-size:36px;font-weight:700;color:#F97316;line-height:1;letter-spacing:-1.5px;">{format_duration(total_min)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">{total_min} min</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{empleados_afectados}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">con al menos 1 reporte</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PROMEDIO</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{format_duration(promedio_min)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">por reporte</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Agregar por empleado
    summary = df.groupby(
        ["empleado_id", "empleado_nombre"], as_index=False,
    ).agg(
        incidencias=("id", "count"),
        minutos_totales=("duracion_calc", "sum"),
    )

    # Ranking POR CANTIDAD
    by_count = summary.sort_values(["incidencias", "minutos_totales"], ascending=[False, False]).reset_index(drop=True)
    # Ranking POR TIEMPO
    by_time = summary.sort_values(["minutos_totales", "incidencias"], ascending=[False, False]).reset_index(drop=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
            'text-transform:uppercase;color:#DC2626;margin:8px 0 12px 0;">'
            '🏆 — RANKING POR CANTIDAD (FRECUENCIA)</div>',
            unsafe_allow_html=True,
        )
        _render_ranking_list(by_count, employees_active, mode="count")

    with col_right:
        st.markdown(
            '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
            'text-transform:uppercase;color:#DC2626;margin:8px 0 12px 0;">'
            '⏱️ — RANKING POR TIEMPO (MINUTOS)</div>',
            unsafe_allow_html=True,
        )
        _render_ranking_list(by_time, employees_active, mode="time")

    # ============================================================
    # DISTRIBUCIÓN POR TIPO DE INCIDENCIA
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:32px 0 12px 0;">'
        '📊 — DISTRIBUCIÓN POR TIPO</div>',
        unsafe_allow_html=True,
    )

    tipo_summary = df.groupby("tipo", as_index=False).agg(
        cantidad=("id", "count"),
        minutos=("duracion_calc", "sum"),
    ).sort_values("minutos", ascending=False)

    max_min_tipo = int(tipo_summary["minutos"].max()) if not tipo_summary.empty else 1

    tipo_cards = []
    for _, row in tipo_summary.iterrows():
        tipo = str(row["tipo"])
        tipo_label = INCIDENT_LABELS.get(tipo, tipo)
        tipo_icon = INCIDENT_ICONS.get(tipo, "❓")
        tipo_color = INCIDENT_COLORS.get(tipo, "#64748B")
        cantidad = int(row["cantidad"])
        minutos = int(row["minutos"])
        pct = (minutos / max_min_tipo) * 100 if max_min_tipo > 0 else 0

        tipo_cards.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;
                    padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
                <span style="font-size:24px;line-height:1;">{tipo_icon}</span>
                <div style="flex:1;min-width:140px;">
                    <div style="font-size:13px;font-weight:700;color:#0A0A0A;">{tipo_label}</div>
                    <div style="font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.3px;margin-top:2px;">
                        {cantidad} reporte{"s" if cantidad != 1 else ""}
                    </div>
                </div>
                <div style="flex:2;min-width:180px;">
                    <div style="background:#F1F5F9;height:8px;border-radius:4px;overflow:hidden;">
                        <div style="background:{tipo_color};height:100%;width:{pct}%;border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:80px;">
                    <div style="font-size:18px;font-weight:700;color:{tipo_color};
                                line-height:1;letter-spacing:-0.5px;
                                font-family:'JetBrains Mono',monospace;">{format_duration(minutos)}</div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:2px;">acumulado</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(tipo_cards), unsafe_allow_html=True)


def _render_ranking_list(df_sorted: pd.DataFrame, employees_active: pd.DataFrame, mode: str):
    """Lista ordenada de empleados con medallas y barra de progreso."""
    if df_sorted.empty:
        st.info("Sin datos.")
        return

    medals = {0: "🥇", 1: "🥈", 2: "🥉"}

    if mode == "count":
        max_val = int(df_sorted["incidencias"].max())
        primary_key = "incidencias"
        primary_color = "#3B82F6"
    else:
        max_val = int(df_sorted["minutos_totales"].max())
        primary_key = "minutos_totales"
        primary_color = "#F97316"

    cards = []
    for i, row in df_sorted.iterrows():
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
        cantidad = int(row["incidencias"])
        minutos = int(row["minutos_totales"])

        primary_val = cantidad if mode == "count" else minutos
        pct = (primary_val / max_val) * 100 if max_val > 0 else 0

        if mode == "count":
            primary_display = f"{cantidad}"
            secondary_display = f"{format_duration(minutos)} acum."
            primary_unit = "reporte" + ("s" if cantidad != 1 else "")
        else:
            primary_display = format_duration(minutos)
            secondary_display = f"{cantidad} reporte" + ("s" if cantidad != 1 else "")
            primary_unit = "acumulado"

        medal = medals.get(i, f"#{i+1}")

        cards.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;
                    padding:14px 16px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <div style="font-size:20px;font-weight:800;color:#94A3B8;min-width:32px;
                            text-align:center;">{medal}</div>
                {flag_html}
                <span style="width:32px;height:32px;border-radius:50%;background:{color};
                             display:inline-flex;align-items:center;justify-content:center;
                             font-weight:700;font-size:11px;color:#475569;">{iniciales}</span>
                <div style="flex:1;min-width:120px;">
                    <div style="font-size:13px;font-weight:700;color:#0A0A0A;">{emp_name}</div>
                    <div style="font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.3px;margin-top:2px;">{secondary_display}</div>
                </div>
                <div style="text-align:right;min-width:70px;">
                    <div style="font-size:18px;font-weight:700;color:{primary_color};
                                line-height:1;letter-spacing:-0.5px;
                                font-family:'JetBrains Mono',monospace;">{primary_display}</div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:2px;">{primary_unit}</div>
                </div>
            </div>
            <div style="margin-top:8px;background:#F1F5F9;height:6px;border-radius:3px;overflow:hidden;">
                <div style="background:{primary_color};height:100%;width:{pct}%;border-radius:3px;"></div>
            </div>
        </div>
        ''')

    st.markdown("".join(cards), unsafe_allow_html=True)


# ============================================================
# TAB: TABLA DETALLE
# ============================================================
def _render_table_tab(df: pd.DataFrame, employees_active: pd.DataFrame, period_label: str):
    """Tabla completa de incidencias del período."""
    # Filtros internos: empleado y tipo
    col1, col2, _ = st.columns([1.3, 1.3, 1])
    with col1:
        emp_options = ["Todos"] + sorted(
            employees_active["nombre"].tolist() if not employees_active.empty else []
        )
        emp_filter = st.selectbox("Empleado", options=emp_options, key="ihtable_emp")
    with col2:
        type_filter = st.selectbox(
            "Tipo",
            options=["Todos"] + INCIDENT_TYPES,
            format_func=lambda x: "Todos" if x == "Todos" else f"{INCIDENT_ICONS.get(x, '?')} {INCIDENT_LABELS.get(x, x)}",
            key="ihtable_type",
        )

    filtered = df.copy()
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]
    if type_filter != "Todos":
        filtered = filtered[filtered["tipo"] == type_filter]

    if filtered.empty:
        st.info("🔎 Sin resultados con los filtros aplicados.")
        return

    filtered = filtered.sort_values(["fecha_parsed", "hi_parsed"], ascending=False).reset_index(drop=True)

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        f'— {len(filtered)} REGISTROS · {period_label}'
        f'</div>',
        unsafe_allow_html=True,
    )

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
            estado_badge = (
                '<span style="background:#FEE2E2;color:#991B1B;padding:2px 7px;'
                'border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
                'text-transform:uppercase;margin-left:6px;">ACTIVA</span>'
            )
            tiempo_str = f"{hi} → en curso"
        else:
            estado_badge = ""
            tiempo_str = f"{hi} → {hf}" if hf else hi

        duration_min = int(row.get("duracion_calc", 0) or 0)
        nota = (str(row.get("nota", "") or ""))[:60]
        if len(str(row.get("nota", "") or "")) > 60:
            nota += "..."

        rows_html.append(
            f'<tr>'
            f'<td class="iht-cell iht-mono">{fecha_str}</td>'
            f'<td class="iht-cell">{flag_html}<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong>{" " + estado_badge if estado_badge else ""}</td>'
            f'<td class="iht-cell"><span style="margin-right:4px;font-size:14px;">{tipo_icon}</span>'
            f'<span style="display:inline-block;padding:3px 8px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span></td>'
            f'<td class="iht-cell iht-mono">{tiempo_str}</td>'
            f'<td class="iht-cell" style="text-align:center;">'
            f'<strong style="font-size:14px;color:{tipo_color};font-family:\'JetBrains Mono\',monospace;">{format_duration(duration_min)}</strong></td>'
            f'<td class="iht-cell" style="font-size:11px;color:#475569;">{nota or "—"}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.iht-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.iht-table th{padding:12px 14px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.iht-cell{padding:12px 14px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.iht-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:8px;">'
        '<table class="iht-table"><thead><tr>'
        '<th>Fecha</th><th>Empleado</th><th>Tipo</th>'
        '<th>Horario</th><th style="text-align:center;">Duración</th><th>Nota</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)
