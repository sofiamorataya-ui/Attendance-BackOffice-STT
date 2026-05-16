"""
modules/overtime.py
Sistema completo de Horas Extras con 3 sub-pestañas:
- Matriz Mensual (réplica de tu Excel imagen 4)
- Registrar (formulario nuevo)
- Detalle Día/Semana/Mes

Henry tiene inyección automática de sábados (7h) al cargar el módulo.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import (
    WS_OVERTIME, WS_EMPLOYEES, COLORS, FLAGS, REFRESH_OTHER_TABS,
)
from core.time_utils import today_gt, now_gt, format_date_long, parse_date
from core.auth import current_user_display_name
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

    # ============================================================
    # INYECCIÓN AUTOMÁTICA DE SÁBADOS DE HENRY
    # ============================================================
    # Se ejecuta UNA vez por sesión (cacheado en session_state)
    cache_key = f"henry_saturdays_{today_gt().year}_{today_gt().isocalendar()[1]}"
    if cache_key not in st.session_state:
        try:
            result = ensure_henry_saturdays(today_gt().year)
            st.session_state[cache_key] = result
            if result.get("insertados", 0) > 0:
                st.toast(
                    f"🎯 Inyectados {result['insertados']} sábados recurrentes de Henry",
                    icon="✅",
                )
        except Exception as e:
            st.warning(f"No se pudo verificar sábados de Henry: {e}")

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

    # ============================================================
    # SUB-TABS
    # ============================================================
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


# ============================================================
# SUB-TAB 1: MATRIZ MENSUAL (réplica de tu Excel)
# ============================================================
def _render_monthly_matrix():
    """Renderiza la matriz mensual estilo Excel (imagen 4)."""

    # Selector de año
    current_year = today_gt().year
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        selected_year = st.selectbox(
            "Año",
            options=list(range(current_year - 2, current_year + 2)),
            index=2,
            key="matrix_year",
        )

    # Cargar matriz
    try:
        df_matrix = get_overtime_matrix(selected_year)
    except Exception as e:
        st.error(f"Error al construir matriz: {e}")
        return

    if df_matrix.empty:
        st.info("📭 No hay horas extras registradas.")
        return

    # ============================================================
    # CONSTRUIR HTML DE LA TABLA (estilo Excel imagen 4)
    # ============================================================
    # Header rojo: "HORAS EXTRAS"
    # Sub-header azul: "HORAS EXTRAS BO - 2,026"
    # Header de meses (texto blanco sobre azul)
    # Filas de empleados (alternadas)
    # Fila TOTAL al final (fondo verde)

    months_cols = list(MONTHS_ES.values())  # Enero...Diciembre
    all_cols = ["Empleado"] + months_cols + ["TOTAL"]

    # ------ HEADER ------
    header_html = (
        '<tr style="background:#1F4E79;color:#FFFFFF;">'
        f'<th colspan="{len(all_cols)}" style="padding:14px;text-align:center;'
        f'font-size:13px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;border:1px solid #1F4E79;">'
        f'HORAS EXTRAS · BO · {selected_year:,}'
        f'</th></tr>'
    )

    # Header de columnas (meses)
    cols_header_cells = '<th style="padding:10px 12px;text-align:center;background:#DDEBF7;color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #BDD7EE;letter-spacing:0.5px;">Empleado</th>'
    for m in months_cols:
        cols_header_cells += (
            f'<th style="padding:10px 8px;text-align:center;background:#DDEBF7;'
            f'color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #BDD7EE;">'
            f'{m}</th>'
        )
    cols_header_cells += (
        '<th style="padding:10px 8px;text-align:center;background:#BDD7EE;'
        'color:#1F4E79;font-size:11px;font-weight:700;border:1px solid #1F4E79;">TOTAL</th>'
    )

    # ------ ROWS ------
    rows_html = []
    for idx, row in df_matrix.iterrows():
        emp = row["Empleado"]
        is_total = emp == "TOTAL"

        if is_total:
            # Fila total: fondo verde claro tipo Excel
            cells = (
                f'<td style="padding:10px 12px;background:#C6EFCE;color:#0A0A0A;'
                f'font-weight:700;border:1px solid #92D050;font-size:12px;'
                f'letter-spacing:0.5px;">{emp}</td>'
            )
            for m in months_cols:
                val = row[m]
                cells += (
                    f'<td style="padding:10px 8px;background:#C6EFCE;color:#0A0A0A;'
                    f'font-weight:700;text-align:center;border:1px solid #92D050;'
                    f'font-size:12px;font-family:\'Inter Tight\',sans-serif;">'
                    f'{format_hours_cell(val)}</td>'
                )
            total_val = row["TOTAL"]
            cells += (
                f'<td style="padding:10px 8px;background:#92D050;color:#0A0A0A;'
                f'font-weight:800;text-align:center;border:1px solid #1F4E79;'
                f'font-size:13px;">'
                f'{format_hours_cell(total_val)}</td>'
            )
        else:
            # Fila normal: fondo blanco alternado
            bg = "#FFFFFF" if idx % 2 == 0 else "#F8FAFC"
            cells = (
                f'<td style="padding:10px 12px;background:{bg};color:#0A0A0A;'
                f'font-weight:600;border:1px solid #E2E8F0;font-size:12px;">'
                f'{emp}</td>'
            )
            for m in months_cols:
                val = row[m]
                cells += (
                    f'<td style="padding:10px 8px;background:{bg};color:#334155;'
                    f'text-align:center;border:1px solid #E2E8F0;'
                    f'font-size:12px;font-family:\'Inter Tight\',sans-serif;">'
                    f'{format_hours_cell(val)}</td>'
                )
            total_val = row["TOTAL"]
            cells += (
                f'<td style="padding:10px 8px;background:#F1F5F9;color:#0A0A0A;'
                f'font-weight:700;text-align:center;border:1px solid #CBD5E1;'
                f'font-size:12px;">'
                f'{format_hours_cell(total_val)}</td>'
            )

        rows_html.append(f'<tr>{cells}</tr>')

    table_html = f"""
    <div style="overflow-x:auto;margin-top:8px;">
    <table style="width:100%;border-collapse:collapse;font-family:'Inter Tight',sans-serif;">
        <thead>
            {header_html}
            <tr>{cols_header_cells}</tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)

    # ============================================================
    # RESUMEN
    # ============================================================
    st.markdown(
        '<div style="margin-top:24px;font-size:11px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#DC2626;">'
        '— TOP CONTRIBUYENTES DEL AÑO'
        '</div>',
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
                    f'font-family:\'Inter Tight\';margin-top:4px;">'
                    f'{format_hours_cell(row["total_horas"])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ============================================================
# SUB-TAB 2: FORMULARIO DE REGISTRO
# ============================================================
def _render_register_form(employees_active: pd.DataFrame):
    """Formulario para registrar horas extras."""

    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #D97706;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">Solo registra horas extras aprobadas</strong><br>'
        'Las horas extras deben ser autorizadas por supervisión antes de registrarse. '
        'Henry tiene sábados recurrentes automáticos (7h cada sábado).'
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
        }

    with st.form("new_overtime_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1.5, 1])

        with col1:
            emp_display = st.selectbox(
                "Empleado",
                options=list(emp_options.keys()),
                key="ot_emp",
            )
        with col2:
            fecha_ot = st.date_input(
                "Fecha",
                value=today_gt(),
                max_value=today_gt() + timedelta(days=7),
                format="DD/MM/YYYY",
                key="ot_fecha",
            )
        with col3:
            horas = st.number_input(
                "Horas",
                min_value=0.5,
                max_value=12.0,
                value=1.0,
                step=0.5,
                key="ot_horas",
            )

        motivo = st.text_area(
            "Motivo / descripción",
            placeholder="Ej: Cierre de mes contable, cobertura de feriado US, etc.",
            key="ot_motivo",
            max_chars=300,
        )

        submitted = st.form_submit_button(
            "Registrar horas extras",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not motivo.strip():
                st.error("⚠️ El motivo es obligatorio.")
            else:
                try:
                    selected = emp_options[emp_display]
                    timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
                    aprobado_por = current_user_display_name()

                    row = [
                        fecha_ot.strftime("%Y-%m-%d"),
                        selected["id"],
                        selected["nombre"],
                        horas,
                        motivo,
                        aprobado_por,
                        timestamp,
                        "FALSE",  # No recurrente (las recurrentes solo Henry sábados)
                    ]
                    append_row(WS_OVERTIME, row)
                    st.success(
                        f"✅ **{horas}h** registradas para **{selected['nombre']}** "
                        f"el {fecha_ot.strftime('%d/%m/%Y')}"
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al registrar: {e}")

    # ============================================================
    # ÚLTIMAS HORAS EXTRAS REGISTRADAS
    # ============================================================
    st.divider()
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin-bottom:12px;">'
        '— ÚLTIMOS 10 REGISTROS'
        '</div>',
        unsafe_allow_html=True,
    )

    df = load_overtime_df()
    if df.empty:
        st.info("📭 No hay horas extras registradas todavía.")
        return

    df = df.sort_values(["fecha_parsed", "timestamp"], ascending=False).head(10)

    rows_html = []
    for _, row in df.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag = FLAGS.get(pais, "")

        is_recurrent = str(row.get("recurrente", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
        recurrent_badge = (
            '<span style="background:#FEF3C7;color:#92400E;padding:2px 6px;'
            'border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
            'text-transform:uppercase;margin-left:6px;">RECURRENTE</span>'
            if is_recurrent else ""
        )

        horas = row.get("horas", 0)
        motivo = row.get("motivo", "") or ""
        if len(motivo) > 60:
            motivo = motivo[:57] + "..."

        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""
        aprobado = row.get("aprobado_por", "")

        rows_html.append(f"""
        <tr>
            <td style="padding:12px 14px;border-bottom:1px solid #F1F5F9;font-family:'JetBrains Mono',monospace;font-size:11px;color:#334155;">
                {fecha_str}
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid #F1F5F9;">
                <span style="font-size:14px;margin-right:4px;">{flag}</span>
                <strong style="font-size:12px;color:#0A0A0A;">{emp_name}</strong>
                {recurrent_badge}
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid #F1F5F9;text-align:center;">
                <span style="font-size:16px;font-weight:700;color:#D97706;">{horas}</span>
                <span style="font-size:10px;color:#94A3B8;margin-left:2px;">hrs</span>
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid #F1F5F9;font-size:11px;color:#475569;">
                {motivo}
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid #F1F5F9;font-family:'JetBrains Mono',monospace;font-size:10px;color:#94A3B8;text-transform:uppercase;">
                {aprobado}
            </td>
        </tr>
        """)

    table_html = f"""
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:'Inter Tight',sans-serif;">
        <thead style="background:#FAFBFC;">
            <tr>
                <th style="padding:10px 14px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Fecha</th>
                <th style="padding:10px 14px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Empleado</th>
                <th style="padding:10px 14px;text-align:center;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Horas</th>
                <th style="padding:10px 14px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Motivo</th>
                <th style="padding:10px 14px;text-align:left;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;border-bottom:1px solid #E2E8F0;">Aprobó</th>
            </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# ============================================================
# SUB-TAB 3: DETALLE DÍA / SEMANA / MES
# ============================================================
def _render_detail_view(employees_active: pd.DataFrame):
    """Vista de detalle con KPIs y desglose por período."""

    # Sub-tabs internos
    period = st.radio(
        "Período",
        options=["Hoy", "Esta semana", "Este mes"],
        horizontal=True,
        label_visibility="collapsed",
        key="detail_period",
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
        # Días desde el 1 del mes hasta hoy
        days_in_period = today_gt().day

    # ============================================================
    # KPIs DEL PERÍODO
    # ============================================================
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
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#16A34A;margin-right:6px;"></span>
                aprobados
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{empleados_unicos}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">/ {len(employees_active)}</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#2563EB;margin-right:6px;"></span>
                con horas extras
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PROMEDIO / DÍA</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{promedio_dia:.1f}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">hrs</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#0891B2;margin-right:6px;"></span>
                en el período
            </div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    if df.empty:
        st.info(f"📭 No hay horas extras registradas en este período.")
        return

    # ============================================================
    # BREAKDOWN POR EMPLEADO
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— DESGLOSE POR EMPLEADO'
        '</div>',
        unsafe_allow_html=True,
    )

    breakdown = df.groupby(["empleado_id", "empleado_nombre"], as_index=False).agg(
        horas_total=("horas", "sum"),
        registros=("horas", "count"),
    ).sort_values("horas_total", ascending=False).reset_index(drop=True)

    # Encontrar el max para el % de barra
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

        flag = FLAGS.get(pais, "")
        horas = row["horas_total"]
        regs = row["registros"]
        pct = (horas / max_hours) * 100 if max_hours > 0 else 0

        rows_html.append(f"""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;
                    padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <span style="font-size:18px;">{flag}</span>
                <span style="width:36px;height:36px;border-radius:50%;background:{color};
                       display:inline-flex;align-items:center;justify-content:center;
                       font-weight:700;font-size:12px;color:#475569;">{iniciales}</span>
                <div style="flex:1;">
                    <div style="font-size:14px;font-weight:600;color:#0A0A0A;margin-bottom:6px;">
                        {emp_name}
                        <span style="font-size:11px;color:#94A3B8;font-weight:400;margin-left:8px;">
                            · {regs} {"registros" if regs != 1 else "registro"}
                        </span>
                    </div>
                    <div style="background:#F1F5F9;height:8px;border-radius:4px;overflow:hidden;">
                        <div style="background:linear-gradient(90deg,#D97706,#F59E0B);
                                    height:100%;width:{pct}%;border-radius:4px;
                                    transition:width 0.5s ease;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:80px;">
                    <div style="font-size:24px;font-weight:700;color:#D97706;
                                font-family:'Inter Tight',sans-serif;line-height:1;letter-spacing:-0.5px;">
                        {horas:g}
                    </div>
                    <div style="font-size:10px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:2px;">hrs</div>
                </div>
            </div>
        </div>
        """)

    st.markdown("".join(rows_html), unsafe_allow_html=True)
