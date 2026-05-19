"""
modules/feedback_reports.py
Reportes de Resolución de Dudas (replica del reporte WhatsApp).

Estructura:
- Dudas/Resoluciones: tabla con [empleado, duda/situación, resolución]
- Observaciones: texto libre
- Feedbacks individuales: tabla con [empleado, feedback]
- Reminders generales: lista de bullets

Permite descargar como PDF con formato STT.
"""
import streamlit as st
import pandas as pd
import json
import uuid
from datetime import date, datetime
from io import BytesIO

from core.ui import render_page_title
from core.sheets import read_worksheet, append_row, get_worksheet, invalidate_cache
from core.config import WS_FEEDBACK_REPORTS, WS_EMPLOYEES
from core.time_utils import today_gt, now_gt, parse_date
from core.flags import flag_emoji_unicode
from core.auth import current_user_display_name
from core.notifications import notify_success, notify_error
from core.business_logic import MONTHS_ES


def render():
    render_page_title(
        eyebrow="COMUNICACIÓN",
        title="Resolución de Dudas",
        subtitle="Reportes estructurados al team · feedbacks · reminders",
    )

    try:
        employees_df = read_worksheet(WS_EMPLOYEES)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    employees_active = employees_df[
        employees_df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].copy() if not employees_df.empty else pd.DataFrame()

    tab_new, tab_history = st.tabs([
        "➕  Nuevo reporte",
        "📜  Historial",
    ])

    with tab_new:
        _render_new_report(employees_active)

    with tab_history:
        _render_history(employees_active)


def _render_new_report(employees_active: pd.DataFrame):
    """Editor del nuevo reporte."""
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:16px;'
        'padding:12px 16px;background:#F8FAFC;border-left:3px solid #2563EB;'
        'border-radius:0 4px 4px 0;">'
        '<strong style="color:#0A0A0A">Estructura del reporte</strong><br>'
        '• <strong>Dudas y resoluciones</strong>: tabla por persona con la duda y la resolución<br>'
        '• <strong>Observaciones</strong>: texto libre del día<br>'
        '• <strong>Feedbacks individuales</strong>: tabla con feedback específico por persona<br>'
        '• <strong>Reminders al team</strong>: lista de bullets generales'
        '</div>',
        unsafe_allow_html=True,
    )

    # Inicializar estado de session
    if "report_dudas" not in st.session_state:
        st.session_state.report_dudas = []
    if "report_feedbacks" not in st.session_state:
        st.session_state.report_feedbacks = []
    if "report_reminders" not in st.session_state:
        st.session_state.report_reminders = []

    # ============================================================
    # METADATA
    # ============================================================
    col1, col2 = st.columns([2, 1])
    with col1:
        titulo = st.text_input(
            "Título del reporte",
            value=f"Reporte de {today_gt().strftime('%A %d de ').capitalize()}{MONTHS_ES[today_gt().month]}",
            max_chars=100,
            key="rep_titulo",
        )
    with col2:
        fecha_reporte = st.date_input(
            "Fecha",
            value=today_gt(),
            format="DD/MM/YYYY",
            key="rep_fecha",
        )

    emp_names = [""] + sorted(employees_active["nombre"].tolist()) if not employees_active.empty else [""]

    # ============================================================
    # SECCIÓN 1: DUDAS / RESOLUCIONES (tabla)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— DUDAS Y RESOLUCIONES'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.report_dudas:
        for idx, entry in enumerate(st.session_state.report_dudas):
            c1, c2, c3, c4 = st.columns([1.5, 2.5, 3, 0.5])
            with c1:
                entry["empleado"] = st.selectbox(
                    "Empleado",
                    options=emp_names,
                    index=emp_names.index(entry.get("empleado", "")) if entry.get("empleado", "") in emp_names else 0,
                    key=f"duda_emp_{idx}",
                    label_visibility="collapsed" if idx > 0 else "visible",
                )
            with c2:
                entry["duda"] = st.text_area(
                    "Duda / Situación",
                    value=entry.get("duda", ""),
                    height=80,
                    key=f"duda_q_{idx}",
                    label_visibility="collapsed" if idx > 0 else "visible",
                )
            with c3:
                entry["resolucion"] = st.text_area(
                    "Resolución",
                    value=entry.get("resolucion", ""),
                    height=80,
                    key=f"duda_r_{idx}",
                    label_visibility="collapsed" if idx > 0 else "visible",
                )
            with c4:
                st.markdown("<div style='padding-top:30px;'></div>", unsafe_allow_html=True)
                if st.button("🗑", key=f"duda_del_{idx}", help="Eliminar"):
                    st.session_state.report_dudas.pop(idx)
                    st.rerun()
    else:
        st.caption("No hay dudas registradas todavía.")

    if st.button("➕  Agregar duda / resolución", key="add_duda", use_container_width=True):
        st.session_state.report_dudas.append({"empleado": "", "duda": "", "resolucion": ""})
        st.rerun()

    # ============================================================
    # SECCIÓN 2: OBSERVACIONES (texto libre)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— OBSERVACIONES'
        '</div>',
        unsafe_allow_html=True,
    )
    observaciones = st.text_area(
        "Observaciones generales del día",
        height=150,
        placeholder="Ej: Hoy detecté tráfico inusual de SAs con error de fechas. Recomiendo revisar el filtro de validación antes de enviar.",
        key="rep_obs",
        label_visibility="collapsed",
    )

    # ============================================================
    # SECCIÓN 3: FEEDBACKS INDIVIDUALES (tabla)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— FEEDBACKS INDIVIDUALES'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.report_feedbacks:
        for idx, fb in enumerate(st.session_state.report_feedbacks):
            c1, c2, c3 = st.columns([1.5, 5, 0.5])
            with c1:
                fb["empleado"] = st.selectbox(
                    "Empleado",
                    options=emp_names,
                    index=emp_names.index(fb.get("empleado", "")) if fb.get("empleado", "") in emp_names else 0,
                    key=f"fb_emp_{idx}",
                    label_visibility="collapsed" if idx > 0 else "visible",
                )
            with c2:
                fb["feedback"] = st.text_area(
                    "Feedback",
                    value=fb.get("feedback", ""),
                    height=80,
                    key=f"fb_text_{idx}",
                    label_visibility="collapsed" if idx > 0 else "visible",
                )
            with c3:
                st.markdown("<div style='padding-top:30px;'></div>", unsafe_allow_html=True)
                if st.button("🗑", key=f"fb_del_{idx}"):
                    st.session_state.report_feedbacks.pop(idx)
                    st.rerun()
    else:
        st.caption("No hay feedbacks registrados todavía.")

    if st.button("➕  Agregar feedback individual", key="add_fb", use_container_width=True):
        st.session_state.report_feedbacks.append({"empleado": "", "feedback": ""})
        st.rerun()

    # ============================================================
    # SECCIÓN 4: REMINDERS GENERALES (bullets)
    # ============================================================
    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:24px 0 12px 0;">'
        '— REMINDERS GENERALES AL TEAM'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.report_reminders:
        for idx, rem in enumerate(st.session_state.report_reminders):
            c1, c2 = st.columns([10, 0.5])
            with c1:
                st.session_state.report_reminders[idx] = st.text_input(
                    f"Reminder {idx+1}",
                    value=rem,
                    key=f"rem_{idx}",
                    label_visibility="collapsed",
                )
            with c2:
                if st.button("🗑", key=f"rem_del_{idx}"):
                    st.session_state.report_reminders.pop(idx)
                    st.rerun()
    else:
        st.caption("No hay reminders registrados todavía.")

    if st.button("➕  Agregar reminder", key="add_rem", use_container_width=True):
        st.session_state.report_reminders.append("")
        st.rerun()

    # ============================================================
    # GUARDAR Y DESCARGAR
    # ============================================================
    st.divider()
    col_save, col_clear = st.columns(2)

    with col_clear:
        if st.button("🧹 Limpiar todo", use_container_width=True, key="rep_clear"):
            st.session_state.report_dudas = []
            st.session_state.report_feedbacks = []
            st.session_state.report_reminders = []
            st.rerun()

    with col_save:
        if st.button(
            "💾 Guardar reporte",
            use_container_width=True,
            type="primary",
            key="rep_save",
        ):
            try:
                report_id = f"REP-{now_gt().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
                timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
                row = [
                    report_id,
                    fecha_reporte.strftime("%Y-%m-%d"),
                    titulo,
                    current_user_display_name(),
                    json.dumps(st.session_state.report_dudas, ensure_ascii=False),
                    observaciones,
                    json.dumps(st.session_state.report_feedbacks, ensure_ascii=False),
                    json.dumps(st.session_state.report_reminders, ensure_ascii=False),
                    timestamp,
                ]
                append_row(WS_FEEDBACK_REPORTS, row)
                invalidate_cache()
                notify_success("Reporte guardado correctamente", title="Reporte guardado")
            except Exception as e:
                notify_error(str(e))

    # Botón descargar PDF (genera del estado actual sin guardar)
    pdf_buffer = _generate_report_pdf(
        titulo=titulo,
        fecha_reporte=fecha_reporte,
        autor=current_user_display_name(),
        dudas=st.session_state.report_dudas,
        observaciones=observaciones,
        feedbacks=st.session_state.report_feedbacks,
        reminders=st.session_state.report_reminders,
    )
    if pdf_buffer:
        filename = f"Reporte_Dudas_{fecha_reporte.strftime('%Y-%m-%d')}.pdf"
        st.download_button(
            "📄 Descargar PDF",
            data=pdf_buffer,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
            key="rep_pdf",
        )


def _render_history(employees_active: pd.DataFrame):
    """Histórico de reportes guardados."""
    try:
        df = read_worksheet(WS_FEEDBACK_REPORTS)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if df.empty:
        st.info("📭 No hay reportes guardados todavía.")
        return

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"].notna()].sort_values("fecha_parsed", ascending=False).reset_index(drop=True)

    st.markdown(
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:#DC2626;margin:16px 0 12px 0;">'
        f'— {len(df)} REPORTE{"S" if len(df) != 1 else ""} EN HISTORIAL'
        f'</div>',
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        fecha_str = row["fecha_parsed"].strftime("%d/%m/%Y") if row["fecha_parsed"] else ""
        titulo = row.get("titulo", "Sin título")
        autor = row.get("autor", "")
        rep_id = row.get("id", "")

        with st.expander(f"📋  {titulo}  ·  {fecha_str}  ·  por {autor}"):
            try:
                dudas = json.loads(row.get("dudas_json", "[]") or "[]")
            except Exception:
                dudas = []
            try:
                feedbacks = json.loads(row.get("feedbacks_json", "[]") or "[]")
            except Exception:
                feedbacks = []
            try:
                reminders = json.loads(row.get("reminders_json", "[]") or "[]")
            except Exception:
                reminders = []
            observaciones = row.get("observaciones", "") or ""

            if dudas:
                st.markdown("**Dudas y resoluciones:**")
                for d in dudas:
                    st.markdown(f"- **{d.get('empleado', '')}**: {d.get('duda', '')} → *{d.get('resolucion', '')}*")
            if observaciones:
                st.markdown("**Observaciones:**")
                st.markdown(observaciones)
            if feedbacks:
                st.markdown("**Feedbacks individuales:**")
                for fb in feedbacks:
                    st.markdown(f"- **{fb.get('empleado', '')}**: {fb.get('feedback', '')}")
            if reminders:
                st.markdown("**Reminders al team:**")
                for r in reminders:
                    st.markdown(f"- {r}")

            # Botón descargar PDF
            pdf_buffer = _generate_report_pdf(
                titulo=titulo,
                fecha_reporte=row["fecha_parsed"],
                autor=autor,
                dudas=dudas,
                observaciones=observaciones,
                feedbacks=feedbacks,
                reminders=reminders,
            )
            if pdf_buffer:
                st.download_button(
                    "📄 Descargar PDF",
                    data=pdf_buffer,
                    file_name=f"Reporte_{fecha_str.replace('/', '-')}.pdf",
                    mime="application/pdf",
                    key=f"hist_pdf_{rep_id}",
                )


def _generate_report_pdf(titulo, fecha_reporte, autor, dudas, observaciones, feedbacks, reminders):
    """Genera un PDF con el contenido del reporte. Usa reportlab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.6*inch, leftMargin=0.6*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # Encabezado STT
    header_style = ParagraphStyle(
        "stt_header", parent=styles["Normal"],
        fontSize=22, textColor=HexColor("#DC2626"),
        spaceAfter=4, leading=24,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "stt_sub", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#64748B"),
        spaceAfter=18, leading=12,
    )
    section_style = ParagraphStyle(
        "stt_section", parent=styles["Normal"],
        fontSize=11, textColor=HexColor("#DC2626"),
        spaceBefore=16, spaceAfter=8, leading=13,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "stt_body", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#0A0A0A"),
        spaceAfter=6, leading=13,
    )
    bullet_style = ParagraphStyle(
        "stt_bullet", parent=body_style,
        leftIndent=14, bulletIndent=4,
    )

    # Título y metadata
    story.append(Paragraph(_escape(titulo), header_style))
    fecha_str = fecha_reporte.strftime("%A %d de %B, %Y").capitalize() if hasattr(fecha_reporte, 'strftime') else str(fecha_reporte)
    story.append(Paragraph(f"{_escape(fecha_str)} · Reportado por {_escape(autor)}", subtitle_style))

    # Sección: Dudas
    if dudas:
        story.append(Paragraph("— RESOLUCIÓN DE DUDAS", section_style))
        for d in dudas:
            emp = d.get("empleado", "")
            duda = d.get("duda", "")
            res = d.get("resolucion", "")
            txt = f"<b>{_escape(emp)}</b>: {_escape(duda)} <font color='#64748B'>→</font> <i>{_escape(res)}</i>"
            story.append(Paragraph("• " + txt, bullet_style))

    # Sección: Observaciones
    if observaciones:
        story.append(Paragraph("— OBSERVACIONES", section_style))
        for line in observaciones.split("\n"):
            if line.strip():
                story.append(Paragraph(_escape(line), body_style))

    # Sección: Feedbacks
    if feedbacks:
        story.append(Paragraph("— FEEDBACKS INDIVIDUALES", section_style))
        for fb in feedbacks:
            emp = fb.get("empleado", "")
            feedback = fb.get("feedback", "")
            txt = f"<b>{_escape(emp)}</b>: {_escape(feedback)}"
            story.append(Paragraph("• " + txt, bullet_style))

    # Sección: Reminders
    if reminders:
        story.append(Paragraph("— REMINDERS AL TEAM", section_style))
        for r in reminders:
            if r.strip():
                story.append(Paragraph("• " + _escape(r), bullet_style))

    # Footer
    story.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle(
        "stt_footer", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#94A3B8"),
        alignment=TA_CENTER,
    )
    story.append(Paragraph("Confidential and proprietary. © STT Logistics Group. All Rights Reserved.", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _escape(text):
    """Escape básico para reportlab."""
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
