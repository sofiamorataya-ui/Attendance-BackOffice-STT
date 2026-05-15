"""
core/time_utils.py
Helpers de fecha/hora SIEMPRE en zona horaria de Guatemala.
Todo en la app debe usar estas funciones, nunca datetime.now() directo.
"""
from datetime import datetime, date, time, timedelta
from typing import Optional
from core.config import TZ_GUATEMALA, DAYS_ES, DAYS_FULL_ES


def now_gt() -> datetime:
    """Datetime actual en Guatemala (timezone-aware)."""
    return datetime.now(TZ_GUATEMALA)


def today_gt() -> date:
    """Fecha de hoy en Guatemala."""
    return now_gt().date()


def current_time_gt() -> time:
    """Hora actual en Guatemala."""
    return now_gt().time()


def parse_time(t_str: str) -> Optional[time]:
    """Parsea string 'HH:MM' a objeto time. Devuelve None si vacío/inválido."""
    if not t_str or t_str.strip() == "":
        return None
    t_str = t_str.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(t_str, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(d_str: str) -> Optional[date]:
    """Parsea string de fecha a date. Soporta varios formatos."""
    if not d_str or str(d_str).strip() == "":
        return None
    d_str = str(d_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(d_str, fmt).date()
        except ValueError:
            continue
    return None


def format_time(t: Optional[time]) -> str:
    """Formatea time como 'HH:MM AM/PM' (ej: '9:00 AM')."""
    if t is None:
        return ""
    return t.strftime("%I:%M %p").lstrip("0")


def format_time_24h(t: Optional[time]) -> str:
    """Formatea time como 'HH:MM' (24h)."""
    if t is None:
        return ""
    return t.strftime("%H:%M")


def format_date_long(d: date) -> str:
    """Formatea fecha como 'Viernes 15 de Mayo, 2026'."""
    if d is None:
        return ""
    day_name = DAYS_FULL_ES[d.weekday()]
    months = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    return f"{day_name} {d.day} de {months[d.month]}, {d.year}"


def format_date_short(d: date) -> str:
    """Formatea fecha como 'DD/MM/YYYY'."""
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")


def day_of_week_es(d: date) -> str:
    """Devuelve día de semana abreviado: LUN, MAR..."""
    return DAYS_ES[d.weekday()]


def days_between(start: date, end: date) -> int:
    """Días entre dos fechas (end - start)."""
    return (end - start).days


def days_until(target_date: date, from_date: Optional[date] = None) -> int:
    """
    Días hasta una fecha objetivo desde una fecha base (hoy por defecto).
    Si la fecha ya pasó este año, calcula para el próximo año.
    """
    base = from_date or today_gt()
    return (target_date - base).days


def next_birthday(birth_date: date, from_date: Optional[date] = None) -> date:
    """
    Devuelve el próximo cumpleaños desde una fecha base.
    Si ya pasó este año, devuelve el del próximo año.
    """
    base = from_date or today_gt()
    this_year_bday = date(base.year, birth_date.month, birth_date.day)
    if this_year_bday < base:
        return date(base.year + 1, birth_date.month, birth_date.day)
    return this_year_bday


def years_months_days(start: date, end: Optional[date] = None) -> tuple[int, int, int]:
    """
    Calcula años, meses y días entre dos fechas.
    Usado para antigüedad de empleados.
    """
    end = end or today_gt()
    years = end.year - start.year
    months = end.month - start.month
    days = end.day - start.day

    if days < 0:
        months -= 1
        # Días del mes anterior
        prev_month = end.month - 1 if end.month > 1 else 12
        prev_year = end.year if end.month > 1 else end.year - 1
        # Días en el mes anterior
        import calendar
        days += calendar.monthrange(prev_year, prev_month)[1]

    if months < 0:
        years -= 1
        months += 12

    return years, months, days


def format_tenure(start: date, end: Optional[date] = None) -> str:
    """Formatea antigüedad como '3 años, 2 meses y 14 días'."""
    y, m, d = years_months_days(start, end)
    parts = []
    if y > 0:
        parts.append(f"{y} año{'s' if y != 1 else ''}")
    if m > 0:
        parts.append(f"{m} mes{'es' if m != 1 else ''}")
    if d > 0 or not parts:
        parts.append(f"{d} día{'s' if d != 1 else ''}")
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + f" y {parts[-1]}"
    return parts[0]


def time_to_minutes(t: time) -> int:
    """Convierte time a minutos desde medianoche."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convierte minutos desde medianoche a time."""
    minutes = max(0, min(minutes, 24 * 60 - 1))
    return time(minutes // 60, minutes % 60)


def time_to_position_pct(t: time, day_start: time = time(5, 0), day_end: time = time(21, 0)) -> float:
    """
    Convierte un time a porcentaje horizontal (0-100%) dentro de un rango horario.
    Usado para posicionar elementos en el timeline del dashboard.
    """
    total_minutes = time_to_minutes(day_end) - time_to_minutes(day_start)
    current_minutes = time_to_minutes(t) - time_to_minutes(day_start)
    pct = (current_minutes / total_minutes) * 100
    return max(0.0, min(100.0, pct))


def is_today_weekend() -> bool:
    """True si hoy es sábado o domingo."""
    return today_gt().weekday() >= 5
