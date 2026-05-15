"""
core/schedules.py
Horarios base de cada empleado. Estos son los horarios estándar semanales.
Se cargan al Google Sheet la primera vez vía seed.
"""
from datetime import time
from typing import Optional

# ============================================================
# DEFINICIÓN DE HORARIOS BASE
# Estructura: { dia_semana: (entrada, salida, almuerzo_inicio, almuerzo_fin) }
# dia_semana: 0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie, 5=Sab, 6=Dom
# None en la tupla = es día libre
# ============================================================

SCHEDULES = {
    # ---- Alessandro (Agente, GT) ----
    # L,M,Mi: 6:00-18:00 (almuerzo 13:30-14:30)
    # Jueves: 13:00-21:00 (almuerzo 13:00-14:00) -- nota: el horario empieza con almuerzo (inusual)
    # V,S,D: libres
    "Alessandro": {
        0: (time(6, 0), time(18, 0), time(13, 30), time(14, 30)),
        1: (time(6, 0), time(18, 0), time(13, 30), time(14, 30)),
        2: (time(6, 0), time(18, 0), time(13, 30), time(14, 30)),
        3: (time(13, 0), time(21, 0), time(13, 0), time(14, 0)),
        4: None,
        5: None,
        6: None,
    },

    # ---- Sebastian (Agente, GT) ----
    # L-V: 6:00-15:00 (almuerzo 13:00-14:00)
    "Sebastian": {
        0: (time(6, 0), time(15, 0), time(13, 0), time(14, 0)),
        1: (time(6, 0), time(15, 0), time(13, 0), time(14, 0)),
        2: (time(6, 0), time(15, 0), time(13, 0), time(14, 0)),
        3: (time(6, 0), time(15, 0), time(13, 0), time(14, 0)),
        4: (time(6, 0), time(15, 0), time(13, 0), time(14, 0)),
        5: None,
        6: None,
    },

    # ---- Sofia (Supervisora, GT) ----
    # L-V: 7:00-16:00 (almuerzo 14:00-15:00)
    "Sofia": {
        0: (time(7, 0), time(16, 0), time(14, 0), time(15, 0)),
        1: (time(7, 0), time(16, 0), time(14, 0), time(15, 0)),
        2: (time(7, 0), time(16, 0), time(14, 0), time(15, 0)),
        3: (time(7, 0), time(16, 0), time(14, 0), time(15, 0)),
        4: (time(7, 0), time(16, 0), time(14, 0), time(15, 0)),
        5: None,
        6: None,
    },

    # ---- Anny (Agente, VE) ----
    # L-V: 8:00-17:00 (almuerzo 11:30-12:30)
    "Anny": {
        0: (time(8, 0), time(17, 0), time(11, 30), time(12, 30)),
        1: (time(8, 0), time(17, 0), time(11, 30), time(12, 30)),
        2: (time(8, 0), time(17, 0), time(11, 30), time(12, 30)),
        3: (time(8, 0), time(17, 0), time(11, 30), time(12, 30)),
        4: (time(8, 0), time(17, 0), time(11, 30), time(12, 30)),
        5: None,
        6: None,
    },

    # ---- Henry (Agente, VE) ----
    # L-V: 8:00-17:00 (almuerzo 12:00-13:00)
    # Sábados: 7:00-14:00 = 7 horas extras recurrentes
    "Henry": {
        0: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        1: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        2: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        3: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        4: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        5: None,  # Sábado se registra como hora extra recurrente, no como horario base
        6: None,
    },

    # ---- Javier (Agente, GT) ----
    # L,M,Mi: 16:00-21:00 (sin almuerzo registrado, turno tarde corto)
    # Jueves: libre
    # Viernes: 16:00-21:00
    # Sábados: libres
    # Domingos: 7:00-20:00 (jornada larga - almuerzo asumido 13:00-14:00)
    "Javier": {
        0: (time(16, 0), time(21, 0), None, None),
        1: (time(16, 0), time(21, 0), None, None),
        2: (time(16, 0), time(21, 0), None, None),
        3: None,
        4: (time(16, 0), time(21, 0), None, None),
        5: None,
        6: (time(7, 0), time(20, 0), time(13, 0), time(14, 0)),
    },

    # ---- Mark (Agente, VE) ----
    # L-V: 8:00-17:00 (almuerzo 15:00-16:00)
    "Mark": {
        0: (time(8, 0), time(17, 0), time(15, 0), time(16, 0)),
        1: (time(8, 0), time(17, 0), time(15, 0), time(16, 0)),
        2: (time(8, 0), time(17, 0), time(15, 0), time(16, 0)),
        3: (time(8, 0), time(17, 0), time(15, 0), time(16, 0)),
        4: (time(8, 0), time(17, 0), time(15, 0), time(16, 0)),
        5: None,
        6: None,
    },

    # ---- Evelyn (Manager, GT) ----
    # Asumiendo L-V 8:00-17:00 con almuerzo 12:00-13:00 (no fue especificado, ajustar después)
    "Evelyn": {
        0: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        1: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        2: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        3: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        4: (time(8, 0), time(17, 0), time(12, 0), time(13, 0)),
        5: None,
        6: None,
    },
}


def get_schedule_for_day(employee_name: str, weekday: int) -> Optional[tuple]:
    """
    Devuelve el horario de un empleado para un día específico de la semana.
    weekday: 0=Lun ... 6=Dom
    Retorna tupla (entrada, salida, almuerzo_inicio, almuerzo_fin) o None si es día libre.
    """
    emp = SCHEDULES.get(employee_name)
    if not emp:
        return None
    return emp.get(weekday)


def scheduled_hours_for_day(employee_name: str, weekday: int) -> float:
    """Calcula horas programadas (descontando almuerzo) para un día."""
    sched = get_schedule_for_day(employee_name, weekday)
    if sched is None:
        return 0.0
    entrada, salida, alm_ini, alm_fin = sched

    def to_min(t):
        return t.hour * 60 + t.minute

    total = to_min(salida) - to_min(entrada)
    if alm_ini and alm_fin:
        total -= (to_min(alm_fin) - to_min(alm_ini))
    return round(total / 60, 2)


def total_weekly_hours(employee_name: str) -> float:
    """Suma horas programadas en una semana estándar."""
    return sum(scheduled_hours_for_day(employee_name, d) for d in range(7))
