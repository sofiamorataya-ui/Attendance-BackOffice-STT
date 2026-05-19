"""
modules/tenure.py
Antigüedad en la empresa de cada empleado.
"""
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet
from core.config import WS_EMPLOYEES, REFRESH_OTHER_TABS
from core.time_utils import today_gt, parse_date, format_tenure, years_months_days
from core.flags import flag_emoji_unicode
from core.business_logic import MONTHS_ES


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="tenure_refresh")

    render_page_title(
        eyebrow="EQUIPO",
        title="Antigüedad",
        subtitle="Tiempo en la empresa actualizado en tiempo real",
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

    employees_active["ingreso_parsed"] = employees_active["fecha_ingreso"].apply(parse_date)
    valid = employees_active[employees_active["ingreso_parsed"].notna()].copy()

    if valid.empty:
        st.warning("No hay fechas de ingreso cargadas.")
        return

    valid["days_total"] = valid["ingreso_parsed"].apply(lambda d: (today_gt() - d).days)
    valid = valid.sort_values("days_total", ascending=False).reset_index(drop=True)

    # KPIs
    total_employees = len(valid)
    veterans = sum(1 for d in valid["days_total"] if d >= 365 * 3)  # 3+ años
    avg_days = int(valid["days_total"].mean())
    avg_years = avg_days / 365.25

    most_senior = valid.iloc[0] if not valid.empty else None
    most_senior_years = most_senior["days_total"] / 365.25 if most_senior is not None else 0

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 24px 0;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">EMPLEADOS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{total_employees}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">activos en BackOffice</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">VETERANOS (3+ AÑOS)</div>
            <div style="font-size:36px;font-weight:700;color:#D97706;line-height:1;letter-spacing:-1.5px;">{veterans}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#D97706;margin-right:6px;"></span>
                con experiencia
            </div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">ANTIGÜEDAD PROMEDIO</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{avg_years:.1f}<span style="font-size:16px;color:#94A3B8;margin-left:4px;">años</span></div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">por empleado</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">MÁS SENIOR</div>
            <div style="font-size:24px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-0.8px;">{most_senior["nombre"] if most_senior is not None else "—"}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">{most_senior_years:.1f} años en la empresa</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Lista
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        '— EQUIPO ORDENADO POR ANTIGÜEDAD</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for i, row in valid.iterrows():
        flag = flag_emoji_unicode(row.get("pais", ""))
        color = row.get("color_avatar", "#F1F5F9")
        iniciales = row.get("iniciales", "??")
        ingreso = row["ingreso_parsed"]
        years, months, days = years_months_days(ingreso)
        tenure_str = format_tenure(ingreso)
        total_days = row["days_total"]

        # Badge "VETERANO" si 3+ años
        veteran_badge = ""
        if years >= 3:
            veteran_badge = (
                '<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;'
                'border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.5px;'
                'text-transform:uppercase;margin-left:8px;">🌟 VETERANO</span>'
            )

        # Ranking badge
        rank_badges = {0: "🥇", 1: "🥈", 2: "🥉"}
        rank_badge = rank_badges.get(i, f"#{i+1}")

        # Highlight color por antigüedad
        if years >= 5:
            border_color = "#D97706"
            bg_accent = "#FEF3C7"
        elif years >= 3:
            border_color = "#0891B2"
            bg_accent = "#CFFAFE"
        else:
            border_color = "#E2E8F0"
            bg_accent = "transparent"

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid {border_color};border-radius:8px;
                    padding:18px 22px;margin-bottom:10px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
                <div style="font-size:24px;font-weight:800;color:#94A3B8;
                            min-width:36px;text-align:center;font-family:'Inter Tight';">
                    {rank_badge}
                </div>
                <span style="font-size:20px;">{flag}</span>
                <span style="width:42px;height:42px;border-radius:50%;background:{color};
                             display:inline-flex;align-items:center;justify-content:center;
                             font-weight:700;font-size:13px;color:#475569;">{iniciales}</span>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:15px;font-weight:700;color:#0A0A0A;">
                        {row["nombre"]}{veteran_badge}
                    </div>
                    <div style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                margin-top:2px;letter-spacing:0.3px;">
                        Ingresó: {ingreso.strftime("%d")} de {MONTHS_ES[ingreso.month]}, {ingreso.year} · {row.get("rol", "")}
                    </div>
                </div>
                <div style="text-align:right;min-width:140px;background:{bg_accent};
                            padding:8px 14px;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#0A0A0A;
                                line-height:1.1;letter-spacing:-0.5px;">{tenure_str}</div>
                    <div style="font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                                margin-top:2px;letter-spacing:0.5px;">{total_days} días totales</div>
                </div>
            </div>
        </div>
        ''')

    st.markdown("".join(cards_html), unsafe_allow_html=True)
