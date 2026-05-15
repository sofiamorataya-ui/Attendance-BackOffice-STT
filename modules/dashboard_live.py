"""
modules/dashboard_live.py
Vista 'Asistencia en Vivo' del día actual.
La versión completa con el timeline visual viene en la Entrega 2.
"""
import streamlit as st
from core.ui import render_page_title
from core.time_utils import today_gt, format_date_long


def render():
    render_page_title(
        eyebrow="VISTA DIARIA",
        title="Asistencia",
        subtitle=format_date_long(today_gt()),
    )
    st.info(
        "🚧 Dashboard en vivo llega en la **Entrega 2**. "
        "Primero asegúrate de completar el setup inicial en la pestaña 🛠️ Setup."
    )
