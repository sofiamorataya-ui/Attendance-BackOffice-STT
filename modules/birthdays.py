"""
modules/birthdays.py
Cumpleaños del equipo con countdown.
"""
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_autorefresh import st_autorefresh

from core.ui import render_page_title
from core.sheets import read_worksheet
from core.config import WS_EMPLOYEES, REFRESH_OTHER_TABS
from core.time_utils import today_gt, parse_date, next_birthday, days_until
from core.flags import flag_emoji_unicode
from core.business_logic import MONTHS_ES


def render():
    st_autorefresh(interval=REFRESH_OTHER_TABS * 1000, key="bday_refresh")

    render_page_title(
        eyebrow="EQUIPO",
        title="Cumpleaños",
        subtitle="Calendario y countdown del equipo BackOffice",
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

    # Parsear cumpleaños
    employees_active["bday_parsed"] = employees_active["cumpleanos"].apply(parse_date)
    valid = employees_active[employees_active["bday_parsed"].notna()].copy()

    if valid.empty:
        st.warning("No hay fechas de cumpleaños cargadas en los empleados.")
        return

    # Calcular próximo cumpleaños y días restantes
    valid["next_bday"] = valid["bday_parsed"].apply(next_birthday)
    valid["days_to"] = valid["next_bday"].apply(days_until)
    valid = valid.sort_values("days_to").reset_index(drop=True)

    # Próximo cumple destacado
    next_emp = valid.iloc[0]
    next_flag = flag_emoji_unicode(next_emp.get("pais", ""))
    next_color = next_emp.get("color_avatar", "#F1F5F9")
    next_iniciales = next_emp.get("iniciales", "??")
    days_to_next = int(next_emp["days_to"])
    bday_date = next_emp["next_bday"]

    if days_to_next == 0:
        countdown_label = "¡HOY ES SU CUMPLEAÑOS!"
        countdown_color = "#DC2626"
        countdown_emoji = "🎂"
    elif days_to_next == 1:
        countdown_label = "MAÑANA"
        countdown_color = "#D97706"
        countdown_emoji = "🎉"
    elif days_to_next <= 7:
        countdown_label = f"EN {days_to_next} DÍAS"
        countdown_color = "#D97706"
        countdown_emoji = "🎁"
    elif days_to_next <= 30:
        countdown_label = f"EN {days_to_next} DÍAS"
        countdown_color = "#2563EB"
        countdown_emoji = "🎈"
    else:
        countdown_label = f"EN {days_to_next} DÍAS"
        countdown_color = "#64748B"
        countdown_emoji = "📅"

    hero_html = f"""
    <div style="background:linear-gradient(135deg,#FFFFFF 0%,#FEF3C7 50%,#FEE2E2 100%);
                border:1px solid #E2E8F0;border-radius:12px;
                padding:32px;margin:16px 0 24px 0;
                box-shadow:0 4px 12px rgba(220,38,38,0.08);">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
                    color:#DC2626;margin-bottom:16px;">— PRÓXIMO CUMPLEAÑOS</div>
        <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
            <div style="font-size:84px;line-height:1;">{countdown_emoji}</div>
            <div style="flex:1;min-width:220px;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <span style="font-size:24px;">{next_flag}</span>
                    <span style="width:44px;height:44px;border-radius:50%;background:{next_color};
                                 display:inline-flex;align-items:center;justify-content:center;
                                 font-weight:700;font-size:14px;color:#475569;">{next_iniciales}</span>
                    <div>
                        <div style="font-size:32px;font-weight:700;color:#0A0A0A;line-height:1.1;letter-spacing:-1px;">
                            {next_emp["nombre"]}
                        </div>
                        <div style="font-size:13px;color:#64748B;font-family:'JetBrains Mono',monospace;
                                    letter-spacing:0.3px;margin-top:4px;">
                            {next_emp.get("rol", "")} · {bday_date.strftime("%d de ") + MONTHS_ES[bday_date.month]}
                        </div>
                    </div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:64px;font-weight:800;color:{countdown_color};
                            line-height:1;letter-spacing:-3px;">{days_to_next if days_to_next != 0 else "🎂"}</div>
                <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;color:{countdown_color};
                            margin-top:4px;">{countdown_label}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

    # KPIs
    today = today_gt()
    this_month = sum(1 for d in valid["bday_parsed"] if d.month == today.month)
    next_30 = sum(1 for d in valid["days_to"] if d <= 30)
    next_90 = sum(1 for d in valid["days_to"] if d <= 90)

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;">
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">ESTE MES</div>
            <div style="font-size:36px;font-weight:700;color:#DC2626;line-height:1;letter-spacing:-1.5px;">{this_month}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">cumpleaños en {MONTHS_ES[today.month]}</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PRÓXIMOS 30 DÍAS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{next_30}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">cumpleaños cercanos</div>
        </div>
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:18px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#64748B;margin-bottom:10px;">PRÓXIMOS 90 DÍAS</div>
            <div style="font-size:36px;font-weight:700;color:#0A0A0A;line-height:1;letter-spacing:-1.5px;">{next_90}</div>
            <div style="margin-top:10px;font-size:11px;color:#64748B;">en trimestre actual</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Lista completa
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        '— EQUIPO ORDENADO POR PROXIMIDAD</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for i, row in valid.iterrows():
        flag = flag_emoji_unicode(row.get("pais", ""))
        color = row.get("color_avatar", "#F1F5F9")
        iniciales = row.get("iniciales", "??")
        bday = row["bday_parsed"]
        days = int(row["days_to"])

        if days == 0:
            badge_bg = "#DC2626"
            badge_color = "#FFFFFF"
            badge_text = "HOY 🎂"
        elif days <= 7:
            badge_bg = "#FEF3C7"
            badge_color = "#92400E"
            badge_text = f"EN {days}d"
        elif days <= 30:
            badge_bg = "#DBEAFE"
            badge_color = "#1E40AF"
            badge_text = f"EN {days}d"
        else:
            badge_bg = "#F1F5F9"
            badge_color = "#64748B"
            badge_text = f"EN {days}d"

        cards_html.append(f'''
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;
                    padding:16px 20px;display:flex;align-items:center;gap:16px;
                    margin-bottom:8px;">
            <span style="font-size:18px;">{flag}</span>
            <span style="width:38px;height:38px;border-radius:50%;background:{color};
                         display:inline-flex;align-items:center;justify-content:center;
                         font-weight:700;font-size:12px;color:#475569;">{iniciales}</span>
            <div style="flex:1;">
                <div style="font-size:14px;font-weight:700;color:#0A0A0A;">{row["nombre"]}</div>
                <div style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;
                            margin-top:2px;letter-spacing:0.3px;">
                    {bday.strftime("%d")} de {MONTHS_ES[bday.month]} · {row.get("rol", "")}
                </div>
            </div>
            <span style="padding:6px 14px;border-radius:4px;font-size:11px;font-weight:700;
                         letter-spacing:0.8px;text-transform:uppercase;
                         background:{badge_bg};color:{badge_color};">{badge_text}</span>
        </div>
        ''')

    st.markdown("".join(cards_html), unsafe_allow_html=True)
