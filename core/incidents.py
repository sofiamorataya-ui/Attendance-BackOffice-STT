"""
core/incidents.py
Lógica de Incidencias en Vivo con hora manual de inicio/fin.

CAMBIOS vs versión anterior:
- register_incident() recibe hora_inicio (obligatoria) y hora_fin (opcional)
- Si hora_fin se pasa → la incidencia se crea ya CERRADA con duración calculada
- Si hora_fin no se pasa → queda ACTIVA hasta que se cierre manualmente

Estados:
- ACTIVA: en curso, aparece en panel "activas" y overlay sobre el timeline
- CERRADA: ya terminó, queda en histórico con duración calculada
"""
import pandas as pd
from datetime import datetime, date, time, timedelta
from typing import Optional
import uuid

from core.sheets import read_worksheet, append_row, get_worksheet, invalidate_cache
from core.config import WS_INCIDENTS
from core.time_utils import now_gt, today_gt, parse_date, parse_time, time_to_minutes


def load_incidents_df() -> pd.DataFrame:
    """Carga incidencias con columnas parseadas."""
    try:
        df = read_worksheet(WS_INCIDENTS)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df["hi_parsed"] = df["hora_inicio"].apply(parse_time)
    df["hf_parsed"] = df["hora_fin"].apply(parse_time)
    df = df[df["fecha_parsed"].notna()].copy()
    return df.reset_index(drop=True)


def get_active_incidents(target_date: Optional[date] = None) -> pd.DataFrame:
    """Devuelve incidencias ACTIVAS del día indicado (hoy por default)."""
    df = load_incidents_df()
    if df.empty:
        return df
    ref = target_date or today_gt()
    active = df[
        (df["fecha_parsed"] == ref)
        & (df["estado"].astype(str).str.upper() == "ACTIVA")
    ].copy()
    return active.reset_index(drop=True)


def get_active_incident_for_employee(employee_id: int, target_date: Optional[date] = None):
    """Incidencia ACTIVA del empleado en la fecha (o None)."""
    active = get_active_incidents(target_date)
    if active.empty:
        return None
    match = active[active["empleado_id"].astype(str) == str(employee_id)]
    if match.empty:
        return None
    match = match.sort_values("timestamp", ascending=False)
    return match.iloc[0]


def calculate_duration_minutes(hora_inicio: time, hora_fin: time) -> int:
    """Calcula minutos entre dos times (mismo día)."""
    if not hora_inicio or not hora_fin:
        return 0
    start_min = time_to_minutes(hora_inicio)
    end_min = time_to_minutes(hora_fin)
    if end_min < start_min:
        # Cruza medianoche (raro)
        return (24 * 60 - start_min) + end_min
    return end_min - start_min


def register_incident(
    employee_id: int,
    employee_name: str,
    tipo: str,
    hora_inicio: time,
    hora_fin: time,
    nota: str,
    registered_by: str,
    fecha_incidencia: Optional[date] = None,
) -> dict:
    """
    Registra una incidencia con hora inicio y fin manuales.
    Calcula la duración automáticamente.

    Args:
        employee_id: ID del empleado
        employee_name: Nombre del empleado
        tipo: SIN_LUZ, BREAK, etc.
        hora_inicio: Hora de inicio (obligatoria)
        hora_fin: Hora de fin (obligatoria)
        nota: Observación opcional
        registered_by: Quién la registra
        fecha_incidencia: Fecha (default hoy)

    Returns:
        dict: {success, message, incident_id, duracion_min}
    """
    if not hora_inicio:
        return {"success": False, "message": "La hora de inicio es obligatoria.", "incident_id": None}
    if not hora_fin:
        return {"success": False, "message": "La hora de fin es obligatoria.", "incident_id": None}

    # Validar que hora_fin > hora_inicio
    if time_to_minutes(hora_fin) <= time_to_minutes(hora_inicio):
        return {
            "success": False,
            "message": "La hora fin debe ser posterior a la hora de inicio.",
            "incident_id": None,
        }

    fecha = fecha_incidencia or today_gt()
    duracion_min = calculate_duration_minutes(hora_inicio, hora_fin)

    now = now_gt()
    incident_id = f"INC-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        incident_id,
        fecha.strftime("%Y-%m-%d"),
        employee_id,
        employee_name,
        tipo,
        hora_inicio.strftime("%H:%M"),
        hora_fin.strftime("%H:%M"),
        duracion_min,
        nota.strip(),
        registered_by,
        registered_by,           # cerrado_por = mismo que registró
        "CERRADA",
        timestamp,
    ]
    append_row(WS_INCIDENTS, row)
    invalidate_cache()

    return {
        "success": True,
        "message": f"Incidencia registrada para {employee_name} ({format_duration(duracion_min)}).",
        "incident_id": incident_id,
        "duracion_min": duracion_min,
    }


def close_incident(incident_id: str, closed_by: str, hora_fin: Optional[time] = None) -> dict:
    """
    Cierra una incidencia activa.

    Args:
        incident_id: ID de la incidencia
        closed_by: Quién la cierra
        hora_fin: Hora fin manual; si es None, usa la hora actual
    """
    ws = get_worksheet(WS_INCIDENTS)
    all_rows = ws.get_all_values()
    if len(all_rows) < 2:
        return {"success": False, "message": "No hay incidencias en el sheet."}

    headers = all_rows[0]
    try:
        idx_id = headers.index("id")
        idx_hi = headers.index("hora_inicio")
        idx_hf = headers.index("hora_fin")
        idx_dur = headers.index("duracion_minutos")
        idx_cerr = headers.index("cerrado_por")
        idx_estado = headers.index("estado")
    except ValueError as e:
        return {"success": False, "message": f"Headers inválidos: {e}"}

    target_row_idx = None
    target_row = None
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > idx_id and row[idx_id] == incident_id:
            target_row_idx = i
            target_row = row
            break

    if target_row_idx is None:
        return {"success": False, "message": "Incidencia no encontrada."}

    # Calcular hora fin
    hi_str = target_row[idx_hi] if len(target_row) > idx_hi else ""
    hi = parse_time(hi_str)
    hf = hora_fin or now_gt().time()

    # Validar
    if hi and time_to_minutes(hf) <= time_to_minutes(hi):
        return {
            "success": False,
            "message": f"Hora fin ({hf.strftime('%H:%M')}) debe ser posterior a hora inicio ({hi.strftime('%H:%M')}).",
        }

    duration_min = calculate_duration_minutes(hi, hf) if hi else 0

    ws.update_cell(target_row_idx, idx_hf + 1, hf.strftime("%H:%M"))
    ws.update_cell(target_row_idx, idx_dur + 1, duration_min)
    ws.update_cell(target_row_idx, idx_cerr + 1, closed_by)
    ws.update_cell(target_row_idx, idx_estado + 1, "CERRADA")

    invalidate_cache()
    return {
        "success": True,
        "message": f"Incidencia cerrada. Duración: {format_duration(duration_min)}.",
        "duration_minutes": duration_min,
    }


def format_duration(minutes) -> str:
    """Convierte minutos a '2h 15min' o '45min'."""
    try:
        m = int(minutes) if minutes else 0
    except (ValueError, TypeError):
        return "—"
    if m < 1:
        return "< 1min"
    if m < 60:
        return f"{m}min"
    h = m // 60
    rem = m % 60
    if rem == 0:
        return f"{h}h"
    return f"{h}h {rem}min"


def get_current_duration_minutes(hora_inicio_str: str) -> int:
    """Para incidencias ACTIVAS: minutos transcurridos desde hora_inicio hasta AHORA."""
    hi = parse_time(hora_inicio_str)
    if not hi:
        return 0
    now = now_gt()
    start_dt = datetime.combine(now.date(), hi)
    end_dt = now
    if end_dt < start_dt:
        return 0
    return int((end_dt - start_dt).total_seconds() / 60)


def get_incidents_history(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    employee_id: Optional[int] = None,
) -> pd.DataFrame:
    """Histórico filtrable."""
    df = load_incidents_df()
    if df.empty:
        return df
    if date_from is not None:
        df = df[df["fecha_parsed"] >= date_from]
    if date_to is not None:
        df = df[df["fecha_parsed"] <= date_to]
    if employee_id is not None:
        df = df[df["empleado_id"].astype(str) == str(employee_id)]
    return df.reset_index(drop=True)


def compute_row_duration(row) -> int:
    """Duración en minutos de una fila (activa: calculada en vivo; cerrada: del sheet)."""
    if str(row.get("estado", "")).upper() == "ACTIVA":
        return get_current_duration_minutes(str(row.get("hora_inicio", "")))
    try:
        return int(row.get("duracion_minutos", 0) or 0)
    except (ValueError, TypeError):
        return 0
