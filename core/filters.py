"""
core/filters.py
Filtros globales de período: Día / Semana / Mes / Año.

Usados por:
- modules/dashboard_live.py (modo histórico)
- modules/incidents_history.py
"""
import streamlit as st
from datetime import date, timedelta
import calendar
from typing import Tuple

from core.time_utils import today_gt
from core.business_logic import MONTHS_ES


PERIOD_LABELS = {
    "day": "Día",
    "week": "Semana",
    "month": "Mes",
    "year": "Año",
}


def render_period_selector(key_prefix: str = "filter") -> Tuple[str, date, date, str]:
    """
    Renderiza un selector de período con date_input contextual.
    Devuelve (period_kind, date_from, date_to, label).

    Layout: [tipo período] [selector específico] [info del rango]
    """
    col1, col2, col3 = st.columns([1.2, 2.5, 1.8])

    with col1:
        period_kind = st.radio(
            "Período",
            options=["day", "week", "month", "year"],
            format_func=lambda x: PERIOD_LABELS[x],
            horizontal=True,
            key=f"{key_prefix}_period_kind",
            label_visibility="visible",
        )

    today = today_gt()
    current_year = today.year

    with col2:
        if period_kind == "day":
            selected_date = st.date_input(
                "Fecha",
                value=today,
                max_value=today + timedelta(days=365),
                format="DD/MM/YYYY",
                key=f"{key_prefix}_day_date",
            )
            date_from = selected_date
            date_to = selected_date
            label = selected_date.strftime("%A %d de %B, %Y").capitalize()
            # Traducir nombres ingleses básicos al español
            label = _translate_date_label(label, selected_date)

        elif period_kind == "week":
            anchor = st.date_input(
                "Día dentro de la semana",
                value=today,
                format="DD/MM/YYYY",
                key=f"{key_prefix}_week_date",
            )
            # Lunes a domingo
            date_from = anchor - timedelta(days=anchor.weekday())
            date_to = date_from + timedelta(days=6)
            label = f"Semana del {date_from.strftime('%d/%m')} al {date_to.strftime('%d/%m/%Y')}"

        elif period_kind == "month":
            sub1, sub2 = st.columns(2)
            with sub1:
                month_num = st.selectbox(
                    "Mes",
                    options=list(range(1, 13)),
                    index=today.month - 1,
                    format_func=lambda m: MONTHS_ES[m],
                    key=f"{key_prefix}_month_num",
                )
            with sub2:
                year_num = st.selectbox(
                    "Año",
                    options=list(range(current_year - 2, current_year + 2)),
                    index=2,
                    key=f"{key_prefix}_month_year",
                )
            last_day = calendar.monthrange(year_num, month_num)[1]
            date_from = date(year_num, month_num, 1)
            date_to = date(year_num, month_num, last_day)
            label = f"{MONTHS_ES[month_num]} {year_num}"

        else:  # year
            year_num = st.selectbox(
                "Año",
                options=list(range(current_year - 3, current_year + 2)),
                index=3,
                key=f"{key_prefix}_year_num",
            )
            date_from = date(year_num, 1, 1)
            date_to = date(year_num, 12, 31)
            label = f"Año {year_num}"

    with col3:
        days_in_range = (date_to - date_from).days + 1
        st.markdown(
            f'<div style="padding-top:30px;font-size:11px;color:#94A3B8;'
            f'font-family:\'JetBrains Mono\',monospace;letter-spacing:0.3px;line-height:1.5;">'
            f'<strong style="color:#0A0A0A;font-size:13px;">{label}</strong><br>'
            f'{days_in_range} día{"s" if days_in_range != 1 else ""} en el rango'
            f'</div>',
            unsafe_allow_html=True,
        )

    return period_kind, date_from, date_to, label


def _translate_date_label(label: str, d: date) -> str:
    """Convierte 'Monday 18 de May, 2026' → 'Lunes 18 de Mayo, 2026'."""
    weekdays_es = {
        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
        4: "Viernes", 5: "Sábado", 6: "Domingo",
    }
    weekday = weekdays_es[d.weekday()]
    month = MONTHS_ES[d.month]
    return f"{weekday} {d.day} de {month}, {d.year}"


def filter_by_period(df, date_column: str, date_from: date, date_to: date):
    """Filtra DataFrame por rango de fechas en columna `date_column` (de tipo date)."""
    if df is None or df.empty or date_column not in df.columns:
        return df
    return df[(df[date_column] >= date_from) & (df[date_column] <= date_to)].copy()
