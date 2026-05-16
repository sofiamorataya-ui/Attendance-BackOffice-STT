
"""
modules/vacations.py
Sistema de Vacaciones:
- 15 días por empleado por año, acumulación proporcional (1.25 días/mes)
- Cálculo automático de tomados vs disponibles
- Calendario visual del año
- Formulario para registrar
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, delete_row, get_worksheet
from core.config import WS_VACATIONS, WS_EMPLOYEES, VACATION_DAYS_PER_YEAR, REFRESH_OTHER_TABS
from core.time_utils import today_gt, now_gt, format_date_long, parse_date
from core.auth import current_user_display_name
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error
from core.business_logic import MONTHS_ES


VACATION_ACCRUAL_MONTHLY = VACATION_DAYS_PER_YEAR / 12  # 1.25


def days_accrued_so_far(year: int, ref_date=None) -> float:
    """Días acumulados hasta ref_date (1.25 por mes completo, proporcional el mes en curso)."""
    ref = ref_date or today_gt()
    if year < ref.year:
        return float(VACATION_DAYS_PER_YEAR)
    if year > ref.year:
        return 0.0
    full_months = ref.month - 1
    import calendar
    days_in_current_month = calendar.monthrange(ref.year, ref.month)[1]
    partial = (ref.day / days_in_current_month) * VACATION_ACCRUAL_MONTHLY
    return round(full_months * VACATION_ACCRUAL_MONTHLY + partial, 2)


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="vacations_refresh")

    render_page_title(
        eyebrow="GESTIÓN",
        title="Vacaciones",
        subtitle=f"15 días anuales por empleado · {today_gt().year}",
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

    # Selector de año global
    col_year, _ = st.columns([1, 4])
    with col_year:
        current_year = today_gt().year
        selected_year = st.selectbox(
            "Año",
            options=list(range(current_year - 1, current_year + 2)),
            index=1,
            key="vac_year",
        )

    tab_overview, tab_register, tab_history = st.tabs([
        "📊  Resumen por empleado",
        "➕  Registrar vacaciones",
        "📜  Histórico",
    ])

    with tab_overview:
        _render_overview(employees_active, selected_year)

    with tab_register:
        _render_register_form(employees_active)

    with tab_history:
        _render_history(employees_active, selected_year)


def _render_overview(employees_active: pd.DataFrame, year: int):
    """Resumen por empleado: tomados, disponibles, calendario visual."""
    try:
        df = read_worksheet(WS_VACATIONS)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if not df.empty:
        df["fecha_parsed"] = df["fecha"].apply(parse_date)
        df = df[df["fecha_parsed"].notna() & df["fecha_parsed"].apply(lambda d: d.year == year)]

    # KPIs globales
    accrued = days_accrued_so_far(year)
    total_taken = len(df) if not df.empty else 0
    total_available = len(employees_active) * VACATION_DAYS_PER_YEAR - total_taken

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{len(employees_active)}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">activos en {year}</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">DÍAS ACUMULADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0891B2;line-height:1;letter-spacing:-1.5px;">{accrued:g}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">/ 15</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">por empleado hasta hoy</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">TOTAL TOMADOS</div>
            <div style="font-size:36px;font-weight:700;color:#DC2626;line-height:1;letter-spacing:-1.5px;">{total_taken}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">días en el año</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">DISPONIBLES</div>
            <div style="font-size:36px;font-weight:700;color:#16A34A;line-height:1;letter-spacing:-1.5px;">{total_available}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">en pool total</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Cards por empleado
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        '— BALANCE POR EMPLEADO</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for _, emp in employees_active.iterrows():
        emp_id = int(emp["id"])
        emp_name = emp["nombre"]
        flag = flag_emoji_unicode(emp.get("pais", ""))
        iniciales = emp.get("iniciales", "??")
        color = emp.get("color_avatar", "#F1F5F9")

        if df.empty:
            taken = 0
        else:
            taken = len(df[df["empleado_id"].astype(str) == str(emp_id)])

        available = VACATION_DAYS_PER_YEAR - taken
        pct_used = (taken / VACATION_DAYS_PER_YEAR) * 100 if VACATION_DAYS_PER_YEAR else 0

        # Barra de color: verde si disponibles, ámbar si <5, rojo si 0
        bar_color = "#16A34A"
        if available <= 5:
            bar_color = "#D97706"
        if available == 0:
            bar_color = "#DC2626"

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;
                    padding:18px 22px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
                <span style="font-size:20px;">{flag}</span>
                <span style="width:40px;height:40px;border-radius:50%;background:{color};
                       display:inline-flex;align-items:center;justify-content:center;
                       font-weight:700;font-size:13px;color:#475569;">{iniciales}</span>
                <div style="flex:1;min-width:160px;">
                    <div style="font-size:15px;font-weight:700;color:#0A0A0A;">{emp_name}</div>
                    <div style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                margin-top:2px;letter-spacing:0.3px;">
                        {emp.get("rol", "")} · {emp.get("pais", "")}
                    </div>
                </div>
                <div style="flex:2;min-width:200px;">
                    <div style="background:#F1F5F9;height:10px;border-radius:5px;overflow:hidden;">
                        <div style="background:{bar_color};height:100%;width:{pct_used}%;
                                    border-radius:5px;transition:width 0.5s ease;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:6px;
                                font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                letter-spacing:0.5px;">
                        <span>{taken} TOMADOS</span><span>{available} DISPONIBLES</span>
                    </div>
                </div>
                <div style="text-align:right;min-width:80px;">
                    <div style="font-size:28px;font-weight:700;color:{bar_color};
                                line-height:1;letter-spacing:-1px;">{available}</div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1px;
                                text-transform:uppercase;margin-top:2px;">DÍAS LIBRES</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(cards_html), unsafe_allow_html=True)


def _render_register_form(employees_active: pd.DataFrame):
    """Formulario para registrar días de vacaciones."""
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #0891B2;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">Tipos de registro</strong><br>'
        '• <strong>Rango continuo:</strong> ej. 5 al 10 de junio (se generan 6 registros)<br>'
        '• <strong>Día único:</strong> un solo día de vacación'
        '</div>',
        unsafe_allow_html=True,
    )

    emp_options = {}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        display = f"{flag}  {emp['nombre']} ({emp.get('rol', '')})"
        emp_options[display] = {"id": int(emp["id"]), "nombre": emp["nombre"]}

    with st.form("new_vacation_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            emp_display = st.selectbox(
                "Empleado", options=list(emp_options.keys()), key="vac_emp",
            )
        with col2:
            tipo = st.selectbox(
                "Tipo",
                options=["VACACION", "MEDIO_DIA"],
                format_func=lambda x: "Día completo" if x == "VACACION" else "Medio día",
                key="vac_tipo",
            )

        col3, col4 = st.columns(2)
        with col3:
            fecha_inicio = st.date_input(
                "Fecha desde",
                value=today_gt() + timedelta(days=1),
                format="DD/MM/YYYY",
                key="vac_from",
            )
        with col4:
            fecha_fin = st.date_input(
                "Fecha hasta (igual a 'desde' si es un solo día)",
                value=today_gt() + timedelta(days=1),
                format="DD/MM/YYYY",
                key="vac_to",
            )

        submitted = st.form_submit_button(
            "Registrar vacaciones", use_container_width=True, type="primary",
        )

        if submitted:
            if fecha_fin < fecha_inicio:
                notify_error("La fecha 'hasta' no puede ser anterior a 'desde'.")
            else:
                try:
                    selected = emp_options[emp_display]
                    timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
                    approver = current_user_display_name()

                    # Generar un registro por cada día del rango
                    days_inserted = 0
                    d = fecha_inicio
                    while d <= fecha_fin:
                        row = [
                            selected["id"], selected["nombre"],
                            d.strftime("%Y-%m-%d"), tipo, approver, timestamp,
                        ]
                        append_row(WS_VACATIONS, row)
                        days_inserted += 1
                        d += timedelta(days=1)

                    if days_inserted == 1:
                        msg = f"{selected['nombre']} · {fecha_inicio.strftime('%d/%m/%Y')}"
                    else:
                        msg = (
                            f"{selected['nombre']} · "
                            f"{fecha_inicio.strftime('%d/%m')} – {fecha_fin.strftime('%d/%m/%Y')} "
                            f"({days_inserted} días)"
                        )
                    notify_success(msg, title="Vacaciones registradas")
                except Exception as e:
                    notify_error(str(e))


def _render_history(employees_active: pd.DataFrame, year: int):
    """Histórico de vacaciones tomadas."""
    try:
        df = read_worksheet(WS_VACATIONS)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if df.empty:
        st.info("📭 No hay vacaciones registradas todavía.")
        return

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"].notna() & df["fecha_parsed"].apply(lambda d: d.year == year)]

    if df.empty:
        st.info(f"📭 Sin vacaciones registradas en {year}.")
        return

    col1, col2, _ = st.columns([1.3, 1.3, 1])
    with col1:
        emp_filter = st.selectbox(
            "Empleado",
            options=["Todos"] + sorted(employees_active["nombre"].tolist()),
            key="vac_hist_emp",
        )

    filtered = df.copy()
    if emp_filter != "Todos":
        filtered = filtered[filtered["empleado_nombre"] == emp_filter]

    filtered = filtered.sort_values("fecha_parsed", ascending=False).reset_index(drop=True)

    with col2:
        st.write("")
        st.write("")
        st.caption(f"**{len(filtered)}** días en {year}")

    rows_html = []
    for _, row in filtered.iterrows():
        emp_name = row.get("empleado_nombre", "")
        emp_match = employees_active[employees_active["nombre"] == emp_name]
        pais = emp_match.iloc[0]["pais"] if not emp_match.empty else ""
        flag = flag_emoji_unicode(pais)

        tipo = row.get("tipo", "VACACION")
        tipo_label = "Día completo" if tipo == "VACACION" else "Medio día"
        tipo_color = "#0891B2" if tipo == "VACACION" else "#0E7490"

        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""
        weekday_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][row["fecha_parsed"].weekday()]
        aprobado = row.get("aprobado_por", "")

        rows_html.append(
            f'<tr>'
            f'<td class="vac-cell vac-mono">{weekday_es} {fecha_str}</td>'
            f'<td class="vac-cell"><span style="margin-right:6px;">{flag}</span>'
            f'<strong style="font-size:13px;color:#0A0A0A;">{emp_name}</strong></td>'
            f'<td class="vac-cell">'
            f'<span style="display:inline-block;padding:4px 10px;border-radius:3px;font-size:10px;'
            f'font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
            f'background:{tipo_color}22;color:{tipo_color};">{tipo_label}</span></td>'
            f'<td class="vac-cell vac-mono" style="color:#94A3B8;text-transform:uppercase;">{aprobado}</td>'
            f'</tr>'
        )

    table_html = (
        '<style>'
        '.vac-table{width:100%;border-collapse:collapse;font-family:\'Inter Tight\',sans-serif;}'
        '.vac-table th{padding:12px 16px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:1.5px;text-transform:uppercase;color:#94A3B8;'
        'border-bottom:1px solid #E2E8F0;background:#FAFBFC;}'
        '.vac-cell{padding:14px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;}'
        '.vac-mono{font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#334155;}'
        '</style>'
        '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:12px;">'
        '<table class="vac-table"><thead><tr>'
        '<th>Fecha</th><th>Empleado</th><th>Tipo</th><th>Aprobó</th>'
        '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # Eliminación
    with st.expander("🗑️  Eliminar registro"):
        st.caption("Acción irreversible.")
        delete_options = {}
        for _, row in filtered.iterrows():
            fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y")
            emp = row.get("empleado_nombre", "")
            key = f"{fecha_str} · {emp}"
            delete_options[key] = row

        if delete_options:
            selected_key = st.selectbox(
                "Día a eliminar", options=list(delete_options.keys()), key="vac_del_select",
            )
            if st.button("Eliminar", type="primary", key="vac_del_btn"):
                try:
                    selected = delete_options[selected_key]
                    sheet_row_idx = _find_vacation_row_idx(selected)
                    if sheet_row_idx:
                        delete_row(WS_VACATIONS, sheet_row_idx)
                        notify_success("Día de vacación eliminado.")
                        st.rerun()
                    else:
                        notify_error("No se pudo localizar el registro.")
                except Exception as e:
                    notify_error(str(e))


def _find_vacation_row_idx(target_row):
    """Encuentra fila por fecha + empleado_id + timestamp."""
    ws = get_worksheet(WS_VACATIONS)
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
