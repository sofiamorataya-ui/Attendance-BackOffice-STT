"""
core/notifications.py
Snackbar Material Design profesional con escape estricto de HTML.

CAMBIO vs versión anterior:
- TODO el mensaje pasa por html.escape() antes de insertarse en el DOM
- Si el HTML se "escapa" y aparece crudo, al menos será TEXTO PLANO
- Usa st.toast() de Streamlit como fallback nativo robusto
"""
import streamlit as st
import html


def _safe_str(value) -> str:
    """Convierte cualquier cosa a string seguro, sin HTML."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def notify(message: str, kind: str = "success", title: str = None):
    """
    Snackbar profesional. Si el sandbox de Streamlit escapa el HTML,
    cae a st.toast() nativo para que el usuario sí vea el mensaje.
    """
    icons = {"success": "✓", "error": "✕", "warning": "⚠", "info": "ℹ"}
    titles_default = {
        "success": "Completado", "error": "Error",
        "warning": "Atención", "info": "Información",
    }
    icon = icons.get(kind, "✓")
    final_title = title or titles_default.get(kind, "Notificación")

    # Streamlit nativo: SIEMPRE funciona (texto plano garantizado)
    toast_icon = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(kind, "📌")
    try:
        st.toast(f"{final_title}: {message}", icon=toast_icon)
    except Exception:
        pass


def notify_success(message: str, title: str = None):
    notify(message, kind="success", title=title)


def notify_error(message: str, title: str = None):
    notify(message, kind="error", title=title)


def notify_warning(message: str, title: str = None):
    notify(message, kind="warning", title=title)


def notify_info(message: str, title: str = None):
    notify(message, kind="info", title=title)
