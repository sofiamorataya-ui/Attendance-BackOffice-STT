"""
core/incidents.py
Lógica de negocio para Incidencias en Vivo.

Una incidencia es un evento que ocurre durante el turno del empleado:
- Sin luz, sin internet, conexión lenta
- Tuvo que ir al doctor, emergencia familiar, cita personal
- Otro motivo libre

Estados: ACTIVA (en curso) | CERRADA (con duración calculada)
"""
import pandas as pd
from datetime import datetime, date, time, timedelta
from typing import Optional
import uuid

from core.sheets import read_worksheet, append_row, get_worksheet, invalidate_cache
from core.config import WS_INCIDENTS
from core.time_utils import now_gt, today_gt, parse_date, parse_time


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
    """
    Devuelve incidencias con estado ACTIVA del día indicado (hoy por default).
    """
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
    """
    Devuelve la incidencia ACTIVA del empleado en la fecha (o None si no tiene).
    Si por alguna razón tiene varias, devuelve la más reciente.
    """
    active = get_active_incidents(target_date)
    if active.empty:
        return None
    match = active[active["empleado_id"].astype(str) == str(employee_id)]
    if match.empty:
        return None
    # Ordenar por timestamp descendente y devolver la primera
    match = match.sort_values("timestamp", ascending=False)
    return match.iloc[0]


def register_incident(
    employee_id: int,
    employee_name: str,
    tipo: str,
    nota: str,
    registered_by: str,
) -> dict:
    """
    Registra una nueva incidencia ACTIVA para el empleado.

    Returns:
        dict con el resultado: {success: bool, message: str, incident_id: str}
    """
    # Verificar que no exista ya una activa
    existing = get_active_incident_for_employee(employee_id)
    if existing is not None:
        return {
            "success": False,
            "message": f"{employee_name} ya tiene una incidencia activa. Ciérrala primero.",
            "incident_id": None,
        }

    now = now_gt()
    incident_id = f"INC-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        incident_id,
        now.strftime("%Y-%m-%d"),
        employee_id,
        employee_name,
        tipo,
        now.strftime("%H:%M"),  # hora_inicio
        "",                      # hora_fin (vacío hasta cerrar)
        "",                      # duracion_minutos (vacío hasta cerrar)
        nota.strip(),
        registered_by,
        "",                      # cerrado_por (vacío hasta cerrar)
        "ACTIVA",
        timestamp,
    ]
    append_row(WS_INCIDENTS, row)
    invalidate_cache()
    return {
        "success": True,
        "message": f"Incidencia registrada para {employee_name}.",
        "incident_id": incident_id,
    }


def close_incident(incident_id: str, closed_by: str) -> dict:
    """
    Cierra una incidencia activa calculando duración automáticamente.
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
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) > idx_id and row[idx_id] == incident_id:
            target_row_idx = i
            target_row = row
            break

    if target_row_idx is None:
        return {"success": False, "message": "Incidencia no encontrada."}

    # Calcular duración
    hi_str = target_row[idx_hi] if len(target_row) > idx_hi else ""
    hi = parse_time(hi_str)
    now = now_gt()
    hf = now.time()
    duration_min = 0
    if hi:
        start_dt = datetime.combine(now.date(), hi)
        end_dt = datetime.combine(now.date(), hf)
        if end_dt < start_dt:
            # Edge case: cruzó medianoche (raro pero contemplado)
            end_dt += timedelta(days=1)
        duration_min = int((end_dt - start_dt).total_seconds() / 60)

    # Actualizar columnas hora_fin, duracion_minutos, cerrado_por, estado
    # Hacemos una sola actualización por celda para no sobreescribir todo
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


def format_duration(minutes: int) -> str:
    """Convierte minutos a formato '2h 15min' o '45min'."""
    if not minutes or minutes < 1:
        return "< 1min"
    if minutes < 60:
        return f"{minutes}min"
    h = minutes // 60
    m = minutes % 60
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}min"


def get_current_duration_minutes(hora_inicio_str: str) -> int:
    """Calcula minutos transcurridos desde hora_inicio hasta AHORA (para incidencias activas)."""
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
    """
    Histórico filtrable de incidencias (solo CERRADAS típicamente, pero incluye ambas).
    """
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


def get_today_summary_by_employee() -> pd.DataFrame:
    """
    Resumen del día actual por empleado:
    - cantidad de incidencias
    - tiempo total acumulado (cerradas + activas en vivo)
    """
    today = today_gt()
    df = load_incidents_df()
    if df.empty:
        return pd.DataFrame()
    today_df = df[df["fecha_parsed"] == today].copy()
    if today_df.empty:
        return pd.DataFrame()

    # Para activas, calcular duración hasta ahora
    def _row_duration(row):
        if str(row.get("estado", "")).upper() == "ACTIVA":
            return get_current_duration_minutes(row.get("hora_inicio", ""))
        try:
            return int(row.get("duracion_minutos", 0) or 0)
        except (ValueError, TypeError):
            return 0

    today_df["duracion_calc"] = today_df.apply(_row_duration, axis=1)

    summary = today_df.groupby(
        ["empleado_id", "empleado_nombre"], as_index=False,
    ).agg(
        incidencias=("id", "count"),
        minutos_totales=("duracion_calc", "sum"),
    ).sort_values("minutos_totales", ascending=False)

    return summary.reset_index(drop=True)
