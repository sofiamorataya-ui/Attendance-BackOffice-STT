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

    TOLERANTE A HEADERS DEFECTUOSOS:
    - Si la fila 1 tiene celdas vacías o duplicadas, las limpia/renombra en memoria
    - NO modifica el Sheet, solo trabaja sobre el DataFrame en RAM
    """
    ws = get_worksheet(name)
    # Lectura robusta: NO usar get_all_records() (rompe con duplicados/vacíos)
    # Usar get_all_values() y construir el DataFrame manualmente
    all_values = ws.get_all_values()
    if not all_values:
        return pd.DataFrame()

    raw_headers = all_values[0]
    data_rows = all_values[1:]

    # Limpiar headers: rellenar vacíos con placeholder, renombrar duplicados
    seen = {}
    clean_headers = []
    for i, h in enumerate(raw_headers):
        h_str = (h or "").strip()
        if not h_str:
            h_str = f"_col_{i}"
        if h_str in seen:
            seen[h_str] += 1
            h_str = f"{h_str}_{seen[h_str]}"
        else:
            seen[h_str] = 0
        clean_headers.append(h_str)

    if not data_rows:
        return pd.DataFrame(columns=clean_headers)

    # Normalizar filas al ancho del header
    n_cols = len(clean_headers)
    normalized = []
    for row in data_rows:
        if len(row) < n_cols:
            row = row + [""] * (n_cols - len(row))
        elif len(row) > n_cols:
            row = row[:n_cols]
        normalized.append(row)

    df = pd.DataFrame(normalized, columns=clean_headers)

    # Quitar columnas placeholder (_col_N) si están totalmente vacías
    cols_to_drop = [c for c in df.columns
                    if c.startswith("_col_") and (df[c] == "").all()]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    return df


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
        "hora_inicio", "hora_fin",
    ],
    "Vacaciones": [
        "empleado_id", "empleado_nombre", "fecha", "tipo",
        "aprobado_por", "timestamp",
    ],
    "Permisos": [
        "empleado_id", "empleado_nombre", "fecha_inicio", "fecha_fin",
        "tipo", "motivo", "aprobado_por", "timestamp",
        "modalidad", "hora_inicio", "hora_fin", "estado", "id_permiso",
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
    - Si una worksheet no existe, la crea
    - Si está vacía, escribe los headers
    - Si tiene columnas SIN NOMBRE (fila 1 vacía) con datos abajo, las nombra
    - Si le FALTAN columnas al final, las agrega automáticamente
    - Si tiene columnas en orden diferente, lo reporta pero NO modifica
    Devuelve dict con el estado de cada worksheet.
    """
    status = {}
    ss = get_spreadsheet()
    existing_titles = [ws.title for ws in ss.worksheets()]

    def _col_letter(n):
        s = ""
        n0 = n
        while n0 >= 0:
            s = chr(ord("A") + n0 % 26) + s
            n0 = n0 // 26 - 1
        return s

    for ws_name in ALL_WORKSHEETS:
        if ws_name not in existing_titles:
            ss.add_worksheet(title=ws_name, rows=1000, cols=30)
            status[ws_name] = "creada"

        ws = ss.worksheet(ws_name)
        # Usar get_all_values para detectar el ancho real (columnas con datos pero sin header)
        all_values = ws.get_all_values()
        current_headers = all_values[0] if all_values else []
        expected_headers = WORKSHEET_HEADERS[ws_name]

        if not current_headers or all((h or "").strip() == "" for h in current_headers):
            ws.update("A1", [expected_headers])
            status[ws_name] = "headers_agregados_completos"
            continue

        # Detectar el ancho real (cualquier columna con datos abajo)
        max_data_col = len(current_headers)
        for row in all_values[1:]:
            if len(row) > max_data_col:
                max_data_col = len(row)

        # Si hay columnas con datos pero sin header (caso Permisos)
        # Extender current_headers con vacíos hasta max_data_col
        padded_headers = list(current_headers) + [""] * (max_data_col - len(current_headers))

        # Reparar headers: rellenar vacíos en su POSICIÓN con los expected_headers
        # que falten
        needs_fix = False
        new_headers = list(padded_headers)

        # Detectar nombres ya presentes (sin contar vacíos)
        present = [h for h in padded_headers if (h or "").strip()]
        missing_names = [h for h in expected_headers if h not in present]

        # Llenar huecos vacíos con los nombres faltantes EN ORDEN
        missing_iter = iter(missing_names)
        for i, h in enumerate(new_headers):
            if not (h or "").strip():
                try:
                    new_headers[i] = next(missing_iter)
                    needs_fix = True
                except StopIteration:
                    break

        # Si AÚN faltan nombres (caso: hay más expected_headers que slots),
        # agregarlos al final
        remaining = list(missing_iter)
        if remaining:
            new_headers = new_headers + remaining
            needs_fix = True

        if needs_fix:
            last_col = _col_letter(len(new_headers) - 1)
            ws.update(f"A1:{last_col}1", [new_headers], value_input_option="USER_ENTERED")
            status[ws_name] = f"headers_reparados (antes: {padded_headers}, ahora: {new_headers})"
            continue

        if current_headers == expected_headers:
            status[ws_name] = status.get(ws_name, "ok")
        else:
            status[ws_name] = f"orden_diferente (actual: {current_headers})"

    invalidate_cache()
    return status


# ============================================================
# DIAGNÓSTICO DE HEADERS DEFECTUOSOS
# ============================================================
def diagnose_all_headers() -> list[dict]:
    """
    Revisa todas las worksheets esperadas y reporta:
    - Headers vacíos en la fila 1
    - Headers duplicados
    - Headers que NO coinciden con WORKSHEET_HEADERS

    Returns lista de dicts: {worksheet, status, issues, headers_actual, headers_esperados}
    """
    results = []
    for ws_name in ALL_WORKSHEETS:
        try:
            ws = get_worksheet(ws_name)
            raw = ws.row_values(1)
        except Exception as e:
            results.append({
                "worksheet": ws_name,
                "status": "ERROR",
                "issues": [f"No se pudo leer: {e}"],
                "headers_actual": [],
                "headers_esperados": WORKSHEET_HEADERS.get(ws_name, []),
            })
            continue

        issues = []
        # 1. Headers vacíos
        empty_count = sum(1 for h in raw if not (h or "").strip())
        if empty_count > 0:
            issues.append(f"{empty_count} celda(s) vacía(s) en la fila 1")

        # 2. Headers duplicados
        non_empty = [(h or "").strip() for h in raw if (h or "").strip()]
        seen = set()
        dupes = set()
        for h in non_empty:
            if h in seen:
                dupes.add(h)
            seen.add(h)
        if dupes:
            issues.append(f"Headers duplicados: {sorted(dupes)}")

        # 3. Faltan headers esperados
        expected = WORKSHEET_HEADERS.get(ws_name, [])
        if expected:
            missing = [h for h in expected if h not in non_empty]
            if missing:
                issues.append(f"Faltan: {missing}")

            extra = [h for h in non_empty if h not in expected]
            if extra:
                issues.append(f"Sobran (inesperados): {extra}")

        results.append({
            "worksheet": ws_name,
            "status": "OK" if not issues else "WARN",
            "issues": issues,
            "headers_actual": raw,
            "headers_esperados": expected,
        })

    return results
