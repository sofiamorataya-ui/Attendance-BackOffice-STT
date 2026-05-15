"""
core/config.py
Constantes globales del proyecto Attendance BackOffice STT.
"""
import pytz

# ============================================================
# IDENTIDAD DE LA APP
# ============================================================
APP_NAME = "Attendance BackOffice STT"
APP_SHORT = "STT Attendance"
APP_VERSION = "1.0.0"
COMPANY = "STT Logistics Group"

# ============================================================
# ZONA HORARIA
# ============================================================
TZ_GUATEMALA = pytz.timezone("America/Guatemala")

# ============================================================
# REFRESH AUTOMÁTICO (segundos)
# ============================================================
REFRESH_LIVE_DASHBOARD = 60         # Dashboard "Asistencia en Vivo"
REFRESH_OTHER_TABS = 300            # Resto de pestañas (5 min)
CACHE_TTL_SHEETS = 30               # TTL de caché de lectura de Google Sheets

# ============================================================
# PALETA DE COLORES STT
# ============================================================
COLORS = {
    # Marca STT
    "stt_red": "#DC2626",
    "stt_red_dark": "#991B1B",
    "stt_red_light": "#FEE2E2",

    # Neutrales
    "ink": "#0A0A0A",
    "slate_900": "#0F172A",
    "slate_700": "#334155",
    "slate_500": "#64748B",
    "slate_300": "#CBD5E1",
    "slate_100": "#F1F5F9",
    "slate_50": "#F8FAFC",
    "white": "#FFFFFF",

    # Estados de asistencia
    "working": "#16A34A",       # verde - trabajando
    "working_bg": "#DCFCE7",
    "lunch": "#EA580C",         # naranja - almuerzo
    "lunch_bg": "#FFEDD5",
    "overtime": "#D97706",      # ámbar - horas extras
    "overtime_bg": "#FEF3C7",
    "late": "#DC2626",          # rojo - llegada tarde
    "late_bg": "#FEE2E2",
    "day_off": "#94A3B8",       # gris - día libre
    "day_off_bg": "#F1F5F9",
    "permit": "#2563EB",        # azul - permiso
    "permit_bg": "#DBEAFE",
    "vacation": "#0891B2",      # cyan - vacaciones
    "vacation_bg": "#CFFAFE",
    "sick": "#7C2D12",          # marrón - incapacidad
    "sick_bg": "#FED7AA",
}

# ============================================================
# BANDERAS DE PAÍSES (emoji)
# ============================================================
FLAGS = {
    "GT": "🇬🇹",
    "VE": "🇻🇪",
}

COUNTRY_NAMES = {
    "GT": "Guatemala",
    "VE": "Venezuela",
}

# ============================================================
# DÍAS DE LA SEMANA
# ============================================================
DAYS_ES = {
    0: "LUN", 1: "MAR", 2: "MIE", 3: "JUE",
    4: "VIE", 5: "SAB", 6: "DOM",
}

DAYS_FULL_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}

# ============================================================
# WORKSHEETS DEL GOOGLE SHEET
# ============================================================
WS_EMPLOYEES = "Empleados"
WS_SCHEDULES = "Horarios"
WS_ATTENDANCE = "Asistencia"
WS_OVERTIME = "Horas_Extras"
WS_VACATIONS = "Vacaciones"
WS_PERMITS = "Permisos"
WS_HOLIDAYS = "Feriados"
WS_USERS = "Usuarios"

ALL_WORKSHEETS = [
    WS_EMPLOYEES, WS_SCHEDULES, WS_ATTENDANCE, WS_OVERTIME,
    WS_VACATIONS, WS_PERMITS, WS_HOLIDAYS, WS_USERS,
]

# ============================================================
# REGLAS DE NEGOCIO
# ============================================================
VACATION_DAYS_PER_YEAR = 15

# Acumulación proporcional (1.25 días/mes) — confirmaremos con respuesta de Pablo
VACATION_ACCRUAL_MONTHLY = VACATION_DAYS_PER_YEAR / 12

# Tipos de excepción
EXCEPTION_TYPES = [
    "NORMAL",
    "LLEGADA_TARDE",
    "SALIDA_TEMPRANO",
    "AUSENTE",
    "PERMISO",
    "INCAPACIDAD",
    "DIA_LIBRE_INESPERADO",
]

# Tipos de permiso
PERMIT_TYPES = [
    "PERMISO_PERSONAL",
    "INCAPACIDAD_MEDICA",
    "DUELO",
    "OTRO",
]
