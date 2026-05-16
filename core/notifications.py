"""
core/notifications.py
Sistema de notificaciones snackbar estilo Material Design.
Reemplaza st.balloons() y st.toast() por algo más profesional.
"""
import streamlit as st
import uuid


SNACKBAR_CSS = """
<style>
.stt-snackbar {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 99999;
    min-width: 280px;
    max-width: 420px;
    background: #0F172A;
    color: #FFFFFF;
    border-radius: 6px;
    padding: 14px 18px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25), 0 2px 6px rgba(0,0,0,0.15);
    font-family: 'Inter Tight', -apple-system, sans-serif;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: snackbar-in 0.3s cubic-bezier(0.16, 1, 0.3, 1),
               snackbar-out 0.3s cubic-bezier(0.7, 0, 0.84, 0) 3.7s forwards;
    border-left: 4px solid #16A34A;
}
.stt-snackbar-error { border-left-color: #DC2626; }
.stt-snackbar-warning { border-left-color: #D97706; }
.stt-snackbar-info { border-left-color: #2563EB; }

.stt-snackbar-icon {
    font-size: 18px;
    line-height: 1;
    flex-shrink: 0;
}
.stt-snackbar-content {
    flex: 1;
    line-height: 1.4;
}
.stt-snackbar-title {
    font-weight: 700;
    font-size: 13px;
    margin-bottom: 2px;
    letter-spacing: 0.2px;
}
.stt-snackbar-message {
    font-size: 12px;
    color: #CBD5E1;
    line-height: 1.4;
}

@keyframes snackbar-in {
    from {
        transform: translateX(120%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
@keyframes snackbar-out {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(120%);
        opacity: 0;
    }
}

@media (max-width: 599px) {
    .stt-snackbar {
        right: 10px;
        top: 10px;
        min-width: 240px;
        max-width: calc(100vw - 20px);
        padding: 12px 14px;
        font-size: 12px;
    }
}
</style>
"""


def notify(message: str, kind: str = "success", title: str = None):
    """
    Muestra un snackbar profesional.

    Args:
        message: Mensaje principal
        kind: 'success' | 'error' | 'warning' | 'info'
        title: Título opcional (por default según kind)
    """
    icons = {
        "success": "✓",
        "error": "✕",
        "warning": "⚠",
        "info": "ℹ",
    }
    titles = {
        "success": "Completado",
        "error": "Error",
        "warning": "Atención",
        "info": "Información",
    }
    icon = icons.get(kind, "✓")
    final_title = title or titles.get(kind, "Notificación")

    snackbar_id = f"snack-{uuid.uuid4().hex[:8]}"

    html = f"""
    {SNACKBAR_CSS}
    <div id="{snackbar_id}" class="stt-snackbar stt-snackbar-{kind}">
        <div class="stt-snackbar-icon">{icon}</div>
        <div class="stt-snackbar-content">
            <div class="stt-snackbar-title">{final_title}</div>
            <div class="stt-snackbar-message">{message}</div>
        </div>
    </div>
    <script>
        setTimeout(function() {{
            var el = document.getElementById('{snackbar_id}');
            if (el) el.remove();
        }}, 4500);
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)


def notify_success(message: str, title: str = None):
    notify(message, kind="success", title=title)


def notify_error(message: str, title: str = None):
    notify(message, kind="error", title=title)


def notify_warning(message: str, title: str = None):
    notify(message, kind="warning", title=title)


def notify_info(message: str, title: str = None):
    notify(message, kind="info", title=title)
