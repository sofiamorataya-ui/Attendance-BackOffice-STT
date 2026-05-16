"""
core/attendance_engine.py
Motor que calcula el estado actual de cada empleado en tiempo real.

Cruza:
  - Horarios base (worksheet Horarios)
  - Excepciones del día (worksheet Asistencia)
  - Permisos/incapacidades (worksheet Permisos)
  - Vacaciones (worksheet Vacaciones)
  - Horas extras aprobadas (worksheet Horas_Extras)
  - Feriados US con coverage (worksheet Feriados)

Estados posibles:
  - SCHEDULED_NOT_YET   → tiene turno hoy pero aún no empieza
  - WORKING             → está trabajando ahora
  - LUNCH               → en almuerzo
  - WORKED_DONE         → ya salió hoy
  - DAY_OFF             → día libre programado
  - LATE                → debió haber entrado y aún no llega (sin marcar excepción)
  - VACATION            → en vacaciones
  - PERMIT              → con permiso
  - SICK                → incapacidad
  - ABSENT              → ausente
  - OVERTIME            → trabajando horas extras aprobadas fuera del turno
"""
from datetime import date, time, datetime, timedelta
from typing import Optional
import pandas as pd

from core.sheets import read_worksheet
from core.config import (
    WS_EMPLOYEES, WS_SCHEDULES, WS_ATTENDANCE, WS_OVERTIME,
    WS_VACATIONS, WS_PERMITS, COLORS,
)
from core.time_utils import (
    today_gt, current_time_gt, parse_time, parse_date,
    time_to_minutes, time_to_position_pct,
)


# ============================================================
# ENUM DE ESTADOS
# ============================================================
class Status:
    SCHEDULED_NOT_YET = "SCHEDULED_NOT_YET"
    WORKING = "WORKING"
    LUNCH = "LUNCH"
    WORKED_DONE = "WORKED_DONE"
    DAY_OFF = "DAY_OFF"
    LATE = "LATE"
    VACATION = "VACATION"
    PERMIT = "PERMIT"
    SICK = "SICK"
    ABSENT = "ABSENT"
    OVERTIME = "OVERTIME"


# Mapeo de estado → color/label para la UI
STATUS_META = {
    Status.SCHEDULED_NOT_YET: {"label": "Por iniciar", "color": COLORS["slate_300"], "bg": COLORS["slate_100"]},
    Status.WORKING:           {"label": "Trabajando", "color": COLORS["working"],    "bg": COLORS["working_bg"]},
    Status.LUNCH:             {"label": "Almuerzo",   "color": COLORS["lunch"],      "bg": COLORS["lunch_bg"]},
    Status.WORKED_DONE:       {"label": "Finalizado", "color": COLORS["slate_500"],  "bg": COLORS["slate_100"]},
    Status.DAY_OFF:           {"label": "Día libre",  "color": COLORS["day_off"],    "bg": COLORS["day_off_bg"]},
    Status.LATE:              {"label": "Llegada tarde","color": COLORS["late"],     "bg": COLORS["late_bg"]},
    Status.VACATION:          {"label": "Vacaciones", "color": COLORS["vacation"],   "bg": COLORS["vacation_bg"]},
    Status.PERMIT:            {"label": "Permiso",    "color": COLORS["permit"],     "bg": COLORS["permit_bg"]},
    Status.SICK:              {"label": "Incapacidad","color": COLORS["sick"],       "bg": COLORS["sick_bg"]},
    Status.ABSENT:            {"label": "Ausente",    "color": COLORS["late"],       "bg": COLORS["late_bg"]},
    Status.OVERTIME:          {"label": "Hora extra", "color": COLORS["overtime"],   "bg": COLORS["overtime_bg"]},
}


# ============================================================
# CARGA DE DATOS DEL DÍA
# ============================================================
def load_employees() -> pd.DataFrame:
    """Empleados activos."""
    df = read_worksheet(WS_EMPLOYEES)
    if df.empty:
        return df
    df = df[df["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])]
    return df.reset_index(drop=True)


def load_schedule_for_today(target_date: Optional[date] = None) -> pd.DataFrame:
    """
    Filtra horarios para el día de la semana correspondiente.
    Devuelve DataFrame con una fila por empleado activo.
    """
    target_date = target_date or today_gt()
    weekday = target_date.weekday()

    df = read_worksheet(WS_SCHEDULES)
    if df.empty:
        return df

    df = df[df["dia_semana"].astype(int) == weekday].copy()
    return df.reset_index(drop=True)


def load_attendance_exceptions(target_date: Optional[date] = None) -> pd.DataFrame:
    """Excepciones registradas para una fecha."""
    target_date = target_date or today_gt()
    df = read_worksheet(WS_ATTENDANCE)
    if df.empty:
        return df

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"] == target_date].copy()
    return df.reset_index(drop=True)


def load_vacations_for_date(target_date: Optional[date] = None) -> pd.DataFrame:
    """Vacaciones activas en una fecha."""
    target_date = target_date or today_gt()
    df = read_worksheet(WS_VACATIONS)
    if df.empty:
        return df

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"] == target_date].copy()
    return df.reset_index(drop=True)


def load_permits_for_date(target_date: Optional[date] = None) -> pd.DataFrame:
    """Permisos activos en una fecha (rango fecha_inicio → fecha_fin)."""
    target_date = target_date or today_gt()
    df = read_worksheet(WS_PERMITS)
    if df.empty:
        return df

    df["fi_parsed"] = df["fecha_inicio"].apply(parse_date)
    df["ff_parsed"] = df["fecha_fin"].apply(parse_date)
    mask = df.apply(
        lambda r: r["fi_parsed"] is not None and r["ff_parsed"] is not None
                  and r["fi_parsed"] <= target_date <= r["ff_parsed"],
        axis=1,
    )
    df = df[mask].copy()
    return df.reset_index(drop=True)


def load_overtime_for_date(target_date: Optional[date] = None) -> pd.DataFrame:
    """Horas extras aprobadas para una fecha."""
    target_date = target_date or today_gt()
    df = read_worksheet(WS_OVERTIME)
    if df.empty:
        return df

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"] == target_date].copy()
    return df.reset_index(drop=True)


# ============================================================
# CÁLCULO DE ESTADO POR EMPLEADO
# ============================================================
def compute_employee_status(
    emp_row: pd.Series,
    schedule_row: Optional[pd.Series],
    attendance_row: Optional[pd.Series],
    vacation_row: Optional[pd.Series],
    permit_row: Optional[pd.Series],
    now: Optional[datetime] = None,
) -> dict:
    """
    Devuelve dict completo con el estado actual del empleado y datos para la UI.

    Returns:
        {
          "status": Status.*,
          "status_label": str,
          "status_color": str,
          "status_bg": str,
          "entrada": time | None,
          "salida": time | None,
          "almuerzo_inicio": time | None,
          "almuerzo_fin": time | None,
          "is_day_off": bool,
          "scheduled_hours": float,
          "timeline_segments": list[dict],  -> para dibujar barras
          "note": str  -> texto adicional
        }
    """
    from datetime import datetime as _dt
    from core.time_utils import now_gt

    now = now or now_gt()
    current = now.time()

    result = {
        "status": Status.DAY_OFF,
        "status_label": "Día libre",
        "status_color": COLORS["day_off"],
        "status_bg": COLORS["day_off_bg"],
        "entrada": None, "salida": None,
        "almuerzo_inicio": None, "almuerzo_fin": None,
        "is_day_off": True,
        "scheduled_hours": 0.0,
        "timeline_segments": [],
        "note": "",
    }

    # ============================================================
    # PRIORIDAD 1: Vacaciones
    # ============================================================
    if vacation_row is not None:
        return _build_status(result, Status.VACATION,
                             note=f"Vacaciones · {vacation_row.get('tipo', '')}")

    # ============================================================
    # PRIORIDAD 2: Permiso o incapacidad
    # ============================================================
    if permit_row is not None:
        permit_type = str(permit_row.get("tipo", "")).upper()
        if permit_type == "INCAPACIDAD_MEDICA":
            return _build_status(result, Status.SICK,
                                 note=permit_row.get("motivo", "Incapacidad médica"))
        return _build_status(result, Status.PERMIT,
                             note=permit_row.get("motivo", "Permiso"))

    # ============================================================
    # PRIORIDAD 3: Día libre programado
    # ============================================================
    if schedule_row is None:
        return _build_status(result, Status.DAY_OFF, note="No hay horario para hoy")

    is_day_off = str(schedule_row.get("es_dia_libre", "")).upper() in ("TRUE", "VERDADERO", "SI", "1")
    if is_day_off:
        return _build_status(result, Status.DAY_OFF, note="Día libre programado")

    # ============================================================
    # PRIORIDAD 4: Ausencia explícita registrada
    # ============================================================
    if attendance_row is not None:
        tipo_exc = str(attendance_row.get("tipo_excepcion", "")).upper()
        if tipo_exc == "AUSENTE":
            return _build_status(result, Status.ABSENT,
                                 note=attendance_row.get("observaciones", "Ausente"))
        if tipo_exc == "DIA_LIBRE_INESPERADO":
            return _build_status(result, Status.DAY_OFF,
                                 note=attendance_row.get("observaciones", "Día libre inesperado"))

    # ============================================================
    # Tiene horario hoy: parsear horarios
    # ============================================================
    entrada = parse_time(str(schedule_row.get("hora_entrada", "")))
    salida = parse_time(str(schedule_row.get("hora_salida", "")))
    alm_ini = parse_time(str(schedule_row.get("almuerzo_inicio", "")))
    alm_fin = parse_time(str(schedule_row.get("almuerzo_fin", "")))

    # Si hay excepción de llegada tarde / salida temprano, override
    entrada_real = None
    salida_real = None
    if attendance_row is not None:
        entrada_real = parse_time(str(attendance_row.get("hora_entrada_real", "")))
        salida_real = parse_time(str(attendance_row.get("hora_salida_real", "")))

    effective_entrada = entrada_real or entrada
    effective_salida = salida_real or salida

    if effective_entrada is None or effective_salida is None:
        return _build_status(result, Status.DAY_OFF, note="Horario incompleto")

    # Calcular horas programadas (descontando almuerzo)
    total_min = time_to_minutes(effective_salida) - time_to_minutes(effective_entrada)
    if alm_ini and alm_fin:
        total_min -= (time_to_minutes(alm_fin) - time_to_minutes(alm_ini))
    scheduled_hours = round(total_min / 60, 2)

    # Construir segmentos del timeline
    segments = _build_timeline_segments(effective_entrada, effective_salida, alm_ini, alm_fin)

    # Determinar estado según hora actual
    cur_min = time_to_minutes(current)
    ent_min = time_to_minutes(effective_entrada)
    sal_min = time_to_minutes(effective_salida)
    alm_i_min = time_to_minutes(alm_ini) if alm_ini else None
    alm_f_min = time_to_minutes(alm_fin) if alm_fin else None

    if cur_min < ent_min:
        # Aún no es hora de entrar
        status = Status.SCHEDULED_NOT_YET
    elif cur_min >= sal_min:
        # Ya salió
        status = Status.WORKED_DONE
    elif alm_i_min is not None and alm_f_min is not None and alm_i_min <= cur_min < alm_f_min:
        # En almuerzo
        status = Status.LUNCH
    else:
        # Trabajando
        # Detectar llegada tarde solo si la excepción lo dice
        if attendance_row is not None and str(attendance_row.get("tipo_excepcion", "")).upper() == "LLEGADA_TARDE":
            status = Status.LATE
        else:
            status = Status.WORKING

    result.update({
        "entrada": effective_entrada,
        "salida": effective_salida,
        "almuerzo_inicio": alm_ini,
        "almuerzo_fin": alm_fin,
        "is_day_off": False,
        "scheduled_hours": scheduled_hours,
        "timeline_segments": segments,
    })

    meta = STATUS_META[status]
    result.update({
        "status": status,
        "status_label": meta["label"],
        "status_color": meta["color"],
        "status_bg": meta["bg"],
    })
    return result


def _build_status(base: dict, status: str, note: str = "") -> dict:
    """Helper para construir un dict de estado con metadata."""
    meta = STATUS_META[status]
    base.update({
        "status": status,
        "status_label": meta["label"],
        "status_color": meta["color"],
        "status_bg": meta["bg"],
        "note": note,
    })
    return base


def _build_timeline_segments(entrada: time, salida: time, alm_ini: Optional[time], alm_fin: Optional[time]) -> list[dict]:
    """
    Construye los segmentos para dibujar la barra de horario del empleado.
    Cada segmento tiene: start_pct, end_pct, type ('work' | 'lunch'), label
    """
    segments = []

    if alm_ini and alm_fin:
        # Pre-lunch work segment
        if time_to_minutes(alm_ini) > time_to_minutes(entrada):
            segments.append({
                "start_pct": time_to_position_pct(entrada),
                "end_pct": time_to_position_pct(alm_ini),
                "type": "work",
                "label_left": entrada.strftime("%I:%M %p").lstrip("0"),
                "label_right": "",
            })
        # Lunch segment
        segments.append({
            "start_pct": time_to_position_pct(alm_ini),
            "end_pct": time_to_position_pct(alm_fin),
            "type": "lunch",
            "label_left": "",
            "label_right": "",
        })
        # Post-lunch work segment
        if time_to_minutes(salida) > time_to_minutes(alm_fin):
            segments.append({
                "start_pct": time_to_position_pct(alm_fin),
                "end_pct": time_to_position_pct(salida),
                "type": "work",
                "label_left": "",
                "label_right": f"SALE {salida.strftime('%I:%M %p').lstrip('0')}",
            })
    else:
        # Sin almuerzo, solo un bloque de trabajo
        segments.append({
            "start_pct": time_to_position_pct(entrada),
            "end_pct": time_to_position_pct(salida),
            "type": "work",
            "label_left": entrada.strftime("%I:%M %p").lstrip("0"),
            "label_right": f"SALE {salida.strftime('%I:%M %p').lstrip('0')}",
        })

    return segments


# ============================================================
# AGREGADOR: ESTADO DE TODOS LOS EMPLEADOS
# ============================================================
def get_all_statuses(target_date: Optional[date] = None) -> list[dict]:
    """
    Devuelve el estado actual de todos los empleados activos.
    Cada elemento contiene los datos del empleado + el dict de status.
    """
    target_date = target_date or today_gt()

    employees = load_employees()
    schedules = load_schedule_for_today(target_date)
    attendance = load_attendance_exceptions(target_date)
    vacations = load_vacations_for_date(target_date)
    permits = load_permits_for_date(target_date)

    result = []
    for _, emp in employees.iterrows():
        emp_id = int(emp["id"])

        # Buscar registros relacionados
        sched_row = None
        if not schedules.empty:
            match = schedules[schedules["empleado_id"].astype(int) == emp_id]
            if not match.empty:
                sched_row = match.iloc[0]

        att_row = None
        if not attendance.empty:
            match = attendance[attendance["empleado_id"].astype(int) == emp_id]
            if not match.empty:
                att_row = match.iloc[0]

        vac_row = None
        if not vacations.empty:
            match = vacations[vacations["empleado_id"].astype(int) == emp_id]
            if not match.empty:
                vac_row = match.iloc[0]

        per_row = None
        if not permits.empty:
            match = permits[permits["empleado_id"].astype(int) == emp_id]
            if not match.empty:
                per_row = match.iloc[0]

        status = compute_employee_status(emp, sched_row, att_row, vac_row, per_row)

        result.append({
            "employee": emp.to_dict(),
            **status,
        })

    return result


# ============================================================
# KPIs DEL DÍA
# ============================================================
def compute_daily_kpis(statuses: list[dict]) -> dict:
    """KPIs para el header del dashboard."""
    total = len(statuses)

    # Total programados = empleados con horario hoy (no día libre, no vacaciones, no permiso/incapacidad)
    programmed = sum(1 for s in statuses if not s["is_day_off"]
                     and s["status"] not in (Status.VACATION, Status.PERMIT, Status.SICK))

    working = sum(1 for s in statuses if s["status"] == Status.WORKING)
    lunch = sum(1 for s in statuses if s["status"] == Status.LUNCH)
    day_off = sum(1 for s in statuses if s["status"] == Status.DAY_OFF)
    vacation = sum(1 for s in statuses if s["status"] == Status.VACATION)
    permit = sum(1 for s in statuses if s["status"] == Status.PERMIT)
    sick = sum(1 for s in statuses if s["status"] == Status.SICK)
    absent = sum(1 for s in statuses if s["status"] == Status.ABSENT)
    late = sum(1 for s in statuses if s["status"] == Status.LATE)
    not_yet = sum(1 for s in statuses if s["status"] == Status.SCHEDULED_NOT_YET)
    done = sum(1 for s in statuses if s["status"] == Status.WORKED_DONE)

    other_absences = vacation + permit + sick + absent

    return {
        "total": total,
        "programmed": programmed,
        "working": working,
        "lunch": lunch,
        "day_off": day_off,
        "other_absences": other_absences,
        "late": late,
        "not_yet": not_yet,
        "done": done,
    }
