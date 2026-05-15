"""
data/employees_seed.py
Datos maestros iniciales de empleados.
Las fechas_ingreso usan 2026-01-01 como placeholder (se editarán manualmente luego).
"""

# Colores pastel para avatares (similar a la imagen 1)
EMPLOYEES_SEED = [
    {
        "id": 1, "nombre": "Alessandro", "rol": "Agente", "pais": "GT",
        "email": "", "cumpleanos": "2000-12-03", "fecha_ingreso": "2026-01-01",
        "iniciales": "AL", "color_avatar": "#FEE2E2", "activo": "TRUE",
    },
    {
        "id": 2, "nombre": "Javier", "rol": "Agente", "pais": "GT",
        "email": "", "cumpleanos": "2000-06-27", "fecha_ingreso": "2026-01-01",
        "iniciales": "JA", "color_avatar": "#DBEAFE", "activo": "TRUE",
    },
    {
        "id": 3, "nombre": "Sebastian", "rol": "Agente", "pais": "GT",
        "email": "", "cumpleanos": "2000-02-01", "fecha_ingreso": "2026-01-01",
        "iniciales": "SE", "color_avatar": "#FEF3C7", "activo": "TRUE",
    },
    {
        "id": 4, "nombre": "Sofia", "rol": "Supervisora", "pais": "GT",
        "email": "", "cumpleanos": "2000-04-09", "fecha_ingreso": "2020-03-12",
        "iniciales": "SO", "color_avatar": "#FCE7F3", "activo": "TRUE",
    },
    {
        "id": 5, "nombre": "Anny", "rol": "Agente", "pais": "VE",
        "email": "", "cumpleanos": "2000-09-26", "fecha_ingreso": "2024-08-13",
        "iniciales": "AN", "color_avatar": "#DCFCE7", "activo": "TRUE",
    },
    {
        "id": 6, "nombre": "Henry", "rol": "Agente", "pais": "VE",
        "email": "", "cumpleanos": "2000-01-27", "fecha_ingreso": "2025-08-06",
        "iniciales": "HE", "color_avatar": "#E0E7FF", "activo": "TRUE",
    },
    {
        "id": 7, "nombre": "Mark", "rol": "Agente", "pais": "VE",
        "email": "", "cumpleanos": "2000-02-22", "fecha_ingreso": "2025-11-24",
        "iniciales": "MA", "color_avatar": "#CFFAFE", "activo": "TRUE",
    },
    {
        "id": 8, "nombre": "Evelyn", "rol": "Manager", "pais": "GT",
        "email": "", "cumpleanos": "2000-07-07", "fecha_ingreso": "2019-01-07",
        "iniciales": "EV", "color_avatar": "#F3E8FF", "activo": "TRUE",
    },
]


# ============================================================
# FERIADOS US 2026
# ============================================================
US_HOLIDAYS_2026 = [
    {"fecha": "2026-01-01", "nombre": "New Year's Day"},
    {"fecha": "2026-01-19", "nombre": "Martin Luther King Jr. Day"},
    {"fecha": "2026-02-16", "nombre": "Presidents' Day"},
    {"fecha": "2026-05-25", "nombre": "Memorial Day"},
    {"fecha": "2026-06-19", "nombre": "Juneteenth"},
    {"fecha": "2026-07-03", "nombre": "Independence Day (observed)"},
    {"fecha": "2026-09-07", "nombre": "Labor Day"},
    {"fecha": "2026-10-12", "nombre": "Columbus Day"},
    {"fecha": "2026-11-11", "nombre": "Veterans Day"},
    {"fecha": "2026-11-26", "nombre": "Thanksgiving Day"},
    {"fecha": "2026-12-24", "nombre": "Christmas Eve"},
    {"fecha": "2026-12-25", "nombre": "Christmas Day"},
    {"fecha": "2026-12-31", "nombre": "New Year's Eve"},
]
