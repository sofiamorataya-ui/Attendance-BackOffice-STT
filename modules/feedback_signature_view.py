"""
modules/feedback_signature_view.py
Vista pública para que el empleado lea y firme el feedback desde un link de WhatsApp.

URL: https://app.streamlit.app/?feedback=FB-XXX
No requiere login. Solo lectura + firma virtual + comentario.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

from core.sheets import read_worksheet, get_worksheet, invalidate_cache
from core.config import WS_FEEDBACK_PROCESS
from core.time_utils import now_gt


def is_signature_view() -> bool:
    """¿La URL actual es para vista de firma?"""
    qp = st.query_params
    return "feedback" in qp and bool(qp["feedback"])


def render_signature_view():
    """Renderiza la vista pública de firma (no requiere login)."""
    qp = st.query_params
    fb_id = qp.get("feedback", "")
    if not fb_id:
        st.error("Link inválido.")
        return

    # Estilos básicos para que se vea bonito sin sidebar
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .stApp { background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%); }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="background:#0A0A0A;color:#FFFFFF;padding:24px;border-radius:8px;
                margin-bottom:24px;text-align:center;">
        <div style="background:#DC2626;color:#FFFFFF;padding:8px 16px;border-radius:4px;
                    display:inline-block;font-weight:800;font-size:14px;letter-spacing:2px;
                    margin-bottom:12px;">STT</div>
        <div style="font-size:11px;letter-spacing:2px;color:#94A3B8;">ATTENDANCE · BACKOFFICE</div>
        <div style="font-size:28px;font-weight:700;margin-top:12px;letter-spacing:-1px;">
            Feedback Process
        </div>
        <div style="font-size:13px;color:#94A3B8;margin-top:6px;">
            Documento confidencial · STT Logistics Group
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cargar feedback
    try:
        df = read_worksheet(WS_FEEDBACK_PROCESS)
    except Exception as e:
        st.error(f"Error al cargar el feedback: {e}")
        return

    if df.empty:
        st.error("Feedback no encontrado.")
        return

    match = df[df["id"].astype(str) == str(fb_id)]
    if match.empty:
        st.error(f"Feedback con ID `{fb_id}` no encontrado.")
        st.caption("Verifica que el link sea correcto.")
        return

    row = match.iloc[0]
    estado = str(row.get("estado_firma", "")).upper()

    # ============================================================
    # CONTENIDO DEL FEEDBACK
    # ============================================================
    st.markdown(f"### Hola, **{row.get('empleado_nombre', '')}**")
    st.caption(f"De parte de **{row.get('manager', '')}** · {row.get('fecha', '')}")

    if estado == "FIRMADO":
        st.success(f"✓ Ya firmaste este feedback el {row.get('fecha_firma', '')}.")
        st.caption(f"Tu comentario: {row.get('comentario_firma', '') or '—'}")

    # Bloques de contenido
    st.markdown("---")

    sections = [
        ("Tipo de Feedback", row.get("tipo_feedback", "")),
        ("Área", row.get("area_feedback", "") + (f" — {row.get('area_otro', '')}" if row.get("area_otro") else "")),
        ("Descripción de la situación", row.get("descripcion_situacion", "")),
        ("Feedback dado", row.get("feedback_dado", "")),
        ("Comportamiento esperado", row.get("comportamiento_esperado", "")),
    ]
    if row.get("accion_empleado"):
        sections.append(("Acción esperada de tu parte", row.get("accion_empleado", "")))
    if row.get("apoyo_manager"):
        sections.append(("Apoyo del manager", row.get("apoyo_manager", "")))
    if row.get("fecha_seguimiento"):
        sections.append(("Fecha de seguimiento", row.get("fecha_seguimiento", "")))

    for label, content in sections:
        if not content:
            continue
        st.markdown(
            f'<div style="margin-bottom:16px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:#DC2626;margin-bottom:6px;">— {label}</div>'
            f'<div style="font-size:14px;color:#0A0A0A;background:#FFFFFF;'
            f'padding:14px 18px;border-radius:6px;border:1px solid #E2E8F0;'
            f'line-height:1.5;white-space:pre-wrap;">{_esc(content)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # FIRMA (solo si está pendiente)
    # ============================================================
    st.markdown("---")

    if estado == "FIRMADO":
        st.markdown(
            '<div style="background:#DCFCE7;border:1px solid #86EFAC;border-radius:8px;'
            'padding:18px;text-align:center;color:#15803D;font-weight:600;">'
            '✓ Este feedback ya fue firmado. Puedes cerrar esta ventana.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
        'text-transform:uppercase;color:#DC2626;margin:8px 0 12px 0;">'
        '— FIRMA VIRTUAL'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:12px;">'
        'Al firmar virtualmente confirmas que has leído y entendido el feedback.'
        '</div>',
        unsafe_allow_html=True,
    )

    confirmed = st.checkbox(
        "Confirmo haber leído y entendido el feedback",
        key="sig_confirm",
    )

    comentario = st.text_area(
        "Comentario (opcional)",
        placeholder="Si quieres dejar una respuesta, comentario o aclaración...",
        max_chars=1000,
        height=120,
        key="sig_comment",
    )

    nombre_firma = st.text_input(
        "Escribe tu nombre completo para firmar",
        placeholder=row.get("empleado_nombre", ""),
        max_chars=80,
        key="sig_name",
    )

    if st.button(
        "✓ Firmar y enviar",
        use_container_width=True,
        type="primary",
        disabled=(not confirmed or not nombre_firma.strip()),
        key="sig_submit",
    ):
        try:
            # Encontrar la fila y actualizar
            ws = get_worksheet(WS_FEEDBACK_PROCESS)
            all_rows = ws.get_all_values()
            headers = all_rows[0]
            idx_id = headers.index("id")
            target_row_idx = None
            for i, r in enumerate(all_rows[1:], start=2):
                if len(r) > idx_id and r[idx_id] == fb_id:
                    target_row_idx = i
                    break
            if not target_row_idx:
                st.error("No se pudo encontrar el feedback en la base de datos.")
                return

            now = now_gt()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            # Actualizar las columnas específicas
            updates = {
                "empleado_acknowledged": "Yes",
                "comentario_empleado": comentario,
                "estado_firma": "FIRMADO",
                "fecha_firma": timestamp,
                "comentario_firma": f"{nombre_firma.strip()} — {comentario}" if comentario.strip() else nombre_firma.strip(),
                "ip_firma": "",  # Streamlit Cloud no expone IP del cliente fácilmente
                "timestamp_modificacion": timestamp,
            }
            for col_name, value in updates.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    ws.update_cell(target_row_idx, col_idx, value)

            invalidate_cache()
            st.success("✓ Tu firma ha sido registrada. Sofi recibirá la notificación.")
            st.balloons()  # Aquí sí es apropiado: es para el empleado, no Sofi
        except Exception as e:
            st.error(f"Error al firmar: {e}")


def _esc(text):
    """HTML escape básico."""
    if text is None:
        return ""
    s = str(text)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br>"))
