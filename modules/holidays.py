
"""
modules/holidays.py
Feriados de Estados Unidos con asignación de coverage por empleado.
Réplica de tu Excel de la imagen 5.
"""
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet, get_worksheet, append_row
from core.config import WS_HOLIDAYS, WS_EMPLOYEES, REFRESH_OTHER_TABS
from core.time_utils import today_gt, parse_date
from core.flags import flag_emoji_unicode
from core.notifications import notify_success, notify_error


WEEKDAYS_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="holidays_refresh")

    render_page_title(
        eyebrow="CALENDARIO",
        title="Feriados US",
        subtitle="Gestión de coverage por empleado · United States holidays",
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
        holidays_df = read_worksheet(WS_HOLIDAYS)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if employees_df.empty:
        st.warning("No hay empleados cargados.")
        return

    if holidays_df.empty:
        st.warning("No hay feriados cargados. Ve a 🛠️ Setup Inicial.")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy()

    # Parsear fechas
    holidays_df["fecha_parsed"] = holidays_df["fecha"].apply(parse_date)
    holidays_df = holidays_df[holidays_df["fecha_parsed"].notna()]

    # Filtrar por año seleccionable
    available_years = sorted(set(holidays_df["fecha_parsed"].apply(lambda d: d.year)))
    if not available_years:
        st.warning("Las fechas de feriados no son válidas.")
        return

    current_year = today_gt().year
    default_idx = available_years.index(current_year) if current_year in available_years else 0

    col1, _ = st.columns([1, 4])
    with col1:
        selected_year = st.selectbox(
            "Año", options=available_years, index=default_idx, key="hol_year",
        )

    year_df = holidays_df[holidays_df["fecha_parsed"].apply(lambda d: d.year == selected_year)].copy()
    year_df = year_df.sort_values("fecha_parsed").reset_index(drop=True)

    # KPIs
    total = len(year_df)
    asignados = int((year_df["empleado_id_cubre"].astype(str).str.strip() != "").sum())
    pendientes = total - asignados
    pasados = int(year_df["fecha_parsed"].apply(lambda d: d < today_gt()).sum())

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">FERIADOS EN {selected_year}</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3B82F6;margin-right:6px;"></span>
                official US holidays
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">COVERAGE ASIGNADO</div>
            <div style="font-size:36px;font-weight:700;color:#16A34A;line-height:1;letter-spacing:-1.5px;">{asignados}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">/ {total}</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#16A34A;margin-right:6px;"></span>
                con responsable
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PENDIENTES</div>
            <div style="font-size:36px;font-weight:700;color:#DC2626;line-height:1;letter-spacing:-1.5px;">{pendientes}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#DC2626;margin-right:6px;"></span>
                sin asignar
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">YA PASARON</div>
            <div style="font-size:36px;font-weight:700;color:#94A3B8;line-height:1;letter-spacing:-1.5px;">{pasados}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">de {total}</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ============================================================
    # GRID DE FERIADOS (cards estilo imagen 5)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        '— CALENDARIO DE FERIADOS</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for _, hol in year_df.iterrows():
        nombre = hol.get("nombre_feriado", "")
        fecha = hol["fecha_parsed"]
        fecha_str = fecha.strftime("%b %d").upper()
        weekday = WEEKDAYS_EN[fecha.weekday()]
        es_pasado = fecha < today_gt()
        es_hoy = fecha == today_gt()

        emp_id_cubre = str(hol.get("empleado_id_cubre", "")).strip()
        emp_match = employees_active[employees_active["id"].astype(str) == emp_id_cubre]
        if emp_id_cubre and not emp_match.empty:
            emp_data = emp_match.iloc[0]
            flag = flag_emoji_unicode(emp_data.get("pais", ""))
            iniciales = emp_data.get("iniciales", "??")
            color_avatar = emp_data.get("color_avatar", "#F1F5F9")
            assigned_html = (
                f'<div style="display:flex;align-items:center;gap:8px;padding:10px 14px;'
                f'background:#DCFCE7;border-radius:6px;border:1px solid #86EFAC;">'
                f'<span style="font-size:16px;">{flag}</span>'
                f'<span style="width:26px;height:26px;border-radius:50%;background:{color_avatar};'
                f'display:inline-flex;align-items:center;justify-content:center;font-weight:700;'
                f'font-size:10px;color:#475569;">{iniciales}</span>'
                f'<strong style="font-size:12px;color:#15803D;">{emp_data["nombre"]}</strong>'
                f'</div>'
            )
        else:
            assigned_html = (
                '<div style="padding:10px 14px;background:#FEE2E2;border-radius:6px;'
                'border:1px dashed #FCA5A5;text-align:center;color:#991B1B;font-size:11px;'
                'font-weight:700;letter-spacing:1px;text-transform:uppercase;">SIN ASIGNAR</div>'
            )

        if es_hoy:
            badge_style = "background:#DC2626;color:#FFFFFF;"
            badge_text = "HOY"
        elif es_pasado:
            badge_style = "background:#F1F5F9;color:#94A3B8;"
            badge_text = "PASADO"
        else:
            days_to = (fecha - today_gt()).days
            badge_style = "background:#DBEAFE;color:#1E40AF;"
            badge_text = f"EN {days_to}d"

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;
                    padding:18px 20px;display:flex;flex-direction:column;gap:12px;
                    {'opacity:0.6;' if es_pasado else ''}">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:18px;">🇺🇸</span>
                    <span style="font-size:11px;font-weight:700;letter-spacing:1px;color:#94A3B8;
                                 font-family:'JetBrains Mono',monospace;">{weekday}</span>
                </div>
                <span style="padding:3px 8px;border-radius:3px;font-size:9px;font-weight:700;
                             letter-spacing:0.5px;text-transform:uppercase;{badge_style}">
                    {badge_text}
                </span>
            </div>
            <div>
                <div style="font-size:13px;font-weight:700;color:#0A0A0A;line-height:1.3;">{nombre}</div>
                <div style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                            margin-top:2px;letter-spacing:0.5px;">{fecha_str}</div>
            </div>
            {assigned_html}
        </div>
        ''')

    grid_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));'
        f'gap:12px;margin-bottom:24px;">{"".join(cards_html)}</div>'
    )
    st.markdown(grid_html, unsafe_allow_html=True)

    # ============================================================
    # FORMULARIO DE ASIGNACIÓN
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— ASIGNAR COVERAGE</div>',
        unsafe_allow_html=True,
    )

    holiday_options = {}
    for _, hol in year_df.iterrows():
        d = hol["fecha_parsed"]
        emp_id = str(hol.get("empleado_id_cubre", "")).strip()
        emp_match = employees_active[employees_active["id"].astype(str) == emp_id]
        current_emp = emp_match.iloc[0]["nombre"] if emp_id and not emp_match.empty else "Sin asignar"
        label = f"{d.strftime('%d/%m/%Y')} · {hol.get('nombre_feriado', '')} → {current_emp}"
        holiday_options[label] = hol

    emp_options = {"— Sin asignar —": None}
    for _, emp in employees_active.iterrows():
        flag = flag_emoji_unicode(emp.get("pais", ""))
        emp_options[f"{flag}  {emp['nombre']}"] = int(emp["id"])

    with st.form("assign_holiday_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 2])
        with col1:
            selected_holiday_key = st.selectbox(
                "Feriado",
                options=list(holiday_options.keys()),
                key="hol_select",
            )
        with col2:
            selected_emp_key = st.selectbox(
                "Asignar a",
                options=list(emp_options.keys()),
                key="hol_assign_emp",
            )

        observaciones = st.text_input(
            "Observaciones (opcional)",
            placeholder="Ej: Confirmado por email, cubre cliente XYZ...",
            key="hol_obs",
            max_chars=200,
        )

        submitted = st.form_submit_button(
            "Guardar asignación", use_container_width=True, type="primary",
        )

        if submitted:
            try:
                selected_holiday = holiday_options[selected_holiday_key]
                selected_emp_id = emp_options[selected_emp_key]

                if selected_emp_id is None:
                    new_emp_id = ""
                    new_emp_name = ""
                    confirmado = "FALSE"
                else:
                    new_emp_id = selected_emp_id
                    emp_row = employees_active[employees_active["id"].astype(str) == str(selected_emp_id)].iloc[0]
                    new_emp_name = emp_row["nombre"]
                    confirmado = "TRUE"

                # Encontrar fila en sheet y actualizar
                sheet_idx = _find_holiday_row_idx(selected_holiday["fecha"])
                if sheet_idx:
                    ws = get_worksheet(WS_HOLIDAYS)
                    ws.update(f"A{sheet_idx}:F{sheet_idx}", [[
                        selected_holiday["fecha"],
                        selected_holiday.get("nombre_feriado", ""),
                        new_emp_id,
                        new_emp_name,
                        confirmado,
                        observaciones,
                    ]], value_input_option="USER_ENTERED")
                    from core.sheets import invalidate_cache
                    invalidate_cache()
                    notify_success(
                        f"{selected_holiday.get('nombre_feriado')} → {new_emp_name or 'Sin asignar'}",
                        title="Coverage actualizado"
                    )
                    st.rerun()
                else:
                    notify_error("No se encontró el feriado en el sheet.")
            except Exception as e:
                notify_error(str(e))


def _find_holiday_row_idx(fecha_str: str):
    ws = get_worksheet(WS_HOLIDAYS)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return None
    headers = all_rows[0]
    try:
        idx_fecha = headers.index("fecha")
    except ValueError:
        return None
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > idx_fecha and row[idx_fecha] == fecha_str:
            return i
    return None
