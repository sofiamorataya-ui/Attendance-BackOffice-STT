"""
core/sheets.py
Cliente de Google Sheets: conexión, lectura cacheada y escritura.
Usa el patrón de service account (mismo que Viáticos Argos).
"""
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from typing import Optional
from core.config import CACHE_TTL_SHEETS, ALL_WORKSHEETS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ============================================================
# CLIENTE GSPREAD (cacheado a nivel sesión)
# ============================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client() -> gspread.Client:
    """Crea y cachea el cliente de gspread."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_spreadsheet() -> gspread.Spreadsheet:
    """Abre el spreadsheet principal."""
    client = get_gspread_client()
    sheet_id = st.secrets["GOOGLE_SHEET_ID"]
    return client.open_by_key(sheet_id)


def get_worksheet(name: str) -> gspread.Worksheet:
    """Obtiene una worksheet por nombre. Sin caché para evitar tokens expirados en escrituras."""
    ss = get_spreadsheet()
    return ss.worksheet(name)


# ============================================================
# LECTURA CACHEADA
# ============================================================
@st.cache_data(ttl=CACHE_TTL_SHEETS, show_spinner=False)
def read_worksheet(name: str) -> pd.DataFrame:
    """
    Lee una worksheet completa como DataFrame.
    Cacheada con TTL para no saturar la API de Google.
    """
    ws = get_worksheet(name)
    records = ws.get_all_records()
    if not records:
        # Si no hay datos, devolver DF vacío con los headers
        headers = ws.row_values(1)
        return pd.DataFrame(columns=headers)
    return pd.DataFrame(records)


def invalidate_cache():
    """Invalida el caché de lectura. Llamar después de cualquier escritura."""
    read_worksheet.clear()


# ============================================================
# ESCRITURA
# ============================================================
def append_row(worksheet_name: str, row: list) -> None:
    """Agrega una fila al final de la worksheet."""
    ws = get_worksheet(worksheet_name)
    ws.append_row(row, value_input_option="USER_ENTERED")
    invalidate_cache()


def append_rows(worksheet_name: str, rows: list[list]) -> None:
    """Agrega múltiples filas al final."""
    ws = get_worksheet(worksheet_name)
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    invalidate_cache()


def update_cell(worksheet_name: str, row_idx: int, col_idx: int, value) -> None:
    """Actualiza una celda específica (índices 1-based)."""
    ws = get_worksheet(worksheet_name)
    ws.update_cell(row_idx, col_idx, value)
    invalidate_cache()


def update_row(worksheet_name: str, row_idx: int, values: list) -> None:
    """Actualiza una fila completa por índice (1-based)."""
    ws = get_worksheet(worksheet_name)
    end_col = chr(ord("A") + len(values) - 1)
    ws.update(f"A{row_idx}:{end_col}{row_idx}", [values], value_input_option="USER_ENTERED")
    invalidate_cache()


def delete_row(worksheet_name: str, row_idx: int) -> None:
    """Elimina una fila por índice (1-based)."""
    ws = get_worksheet(worksheet_name)
    ws.delete_rows(row_idx)
    invalidate_cache()


def overwrite_worksheet(worksheet_name: str, headers: list, rows: list[list]) -> None:
    """Borra y reescribe completamente una worksheet (usado para seed)."""
    ws = get_worksheet(worksheet_name)
    ws.clear()
    ws.update("A1", [headers] + rows, value_input_option="USER_ENTERED")
    invalidate_cache()


# ============================================================
# HEADERS DE CADA WORKSHEET
# ============================================================
WORKSHEET_HEADERS = {
    "Empleados": [
        "id", "nombre", "rol", "pais", "email",
        "cumpleanos", "fecha_ingreso", "iniciales", "color_avatar", "activo",
    ],
    "Horarios": [
        "empleado_id", "empleado_nombre", "dia_semana", "dia_nombre",
        "hora_entrada", "hora_salida", "almuerzo_inicio", "almuerzo_fin", "es_dia_libre",
    ],
    "Asistencia": [
        "fecha", "empleado_id", "empleado_nombre",
        "hora_entrada_real", "hora_salida_real",
        "tipo_excepcion", "observaciones", "registrado_por", "timestamp",
    ],
    "Horas_Extras": [
        "fecha", "empleado_id", "empleado_nombre",
        "horas", "motivo", "aprobado_por", "timestamp", "recurrente",
    ],
    "Vacaciones": [
        "empleado_id", "empleado_nombre", "fecha", "tipo",
        "aprobado_por", "timestamp",
    ],
    "Permisos": [
        "empleado_id", "empleado_nombre", "fecha_inicio", "fecha_fin",
        "tipo", "motivo", "aprobado_por", "timestamp",
    ],
    "Feriados": [
        "fecha", "nombre_feriado", "empleado_id_cubre", "empleado_nombre_cubre",
        "confirmado", "observaciones",
    ],
    "Usuarios": [
        "username", "password_hash", "nombre_completo", "rol", "activo",
    ],
    "Incidencias": [
        "id", "fecha", "empleado_id", "empleado_nombre", "tipo",
        "hora_inicio", "hora_fin", "duracion_minutos", "nota",
        "registrado_por", "cerrado_por", "estado", "timestamp",
    ],
    "Reportes_Dudas": [
        "id", "fecha", "titulo", "autor",
        "dudas_json", "observaciones", "feedbacks_json", "reminders_json",
        "timestamp",
    ],
    "Feedback_Process": [
        "id", "fecha", "empleado_id", "empleado_nombre", "posicion", "departamento",
        "manager", "tipo_feedback", "area_feedback", "area_otro",
        "descripcion_situacion", "feedback_dado", "comportamiento_esperado",
        "accion_empleado", "apoyo_manager", "fecha_seguimiento",
        "empleado_acknowledged", "comentario_empleado",
        "followup_required", "followup_date", "followup_notes",
        "estado_firma", "fecha_firma", "comentario_firma", "ip_firma",
        "timestamp_creacion", "timestamp_modificacion",
    ],
}


def ensure_headers() -> dict:
    """
    Verifica que todas las worksheets tengan los headers correctos.
    Si una está vacía, escribe los headers.
    Devuelve dict con el estado de cada worksheet.
    """
    status = {}
    ss = get_spreadsheet()
    existing_titles = [ws.title for ws in ss.worksheets()]

    for ws_name in ALL_WORKSHEETS:
        if ws_name not in existing_titles:
            ss.add_worksheet(title=ws_name, rows=1000, cols=20)
            status[ws_name] = "creada"

        ws = ss.worksheet(ws_name)
        current_headers = ws.row_values(1)
        expected_headers = WORKSHEET_HEADERS[ws_name]

        if not current_headers:
            ws.update("A1", [expected_headers])
            status[ws_name] = status.get(ws_name, "headers_agregados")
        elif current_headers != expected_headers:
            status[ws_name] = f"headers_diferentes (actual: {current_headers})"
        else:
            status[ws_name] = status.get(ws_name, "ok")

    invalidate_cache()
    return status
