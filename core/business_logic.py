"""
core/business_logic.py
Lógica de negocio del dominio:
- Inyección automática de horas extras recurrentes de Henry (sábados 7h)
- Agregaciones de horas extras por día/semana/mes
- Cálculos de matriz mensual (réplica de tu Excel de horas extras)
"""
from datetime import date, datetime, timedelta
from typing import Optional
import pandas as pd

from core.sheets import read_worksheet, append_rows, invalidate_cache
from core.config import WS_OVERTIME, WS_EMPLOYEES
from core.time_utils import today_gt, parse_date, now_gt


# ============================================================
# CONSTANTES DE NEGOCIO
# ============================================================
HENRY_NAME = "Henry"
HENRY_SATURDAY_HOURS = 7.0
HENRY_SATURDAY_START_YEAR = 2026  # Desde cuándo empieza la recurrencia

# Meses en español para la matriz mensual
MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


# ============================================================
# HENRY SÁBADOS RECURRENTES
# ============================================================
def get_saturdays_in_year(year: int, until: Optional[date] = None) -> list[date]:
    """Devuelve todos los sábados de un año hasta una fecha límite."""
    until = until or today_gt()
    saturdays = []
    d = date(year, 1, 1)
    # Avanzar al primer sábado
    while d.weekday() != 5:
        d += timedelta(days=1)
    # Recolectar todos los sábados
    while d.year == year and d <= until:
        saturdays.append(d)
        d += timedelta(days=7)
    return saturdays


def ensure_henry_saturdays(year: Optional[int] = None) -> dict:
    """
    Asegura que todos los sábados pasados de Henry estén registrados como horas extras.
    Se ejecuta automáticamente al cargar la pestaña de horas extras.
    Idempotente: si ya está registrado, no duplica.

    Returns: {"insertados": int, "ya_existian": int, "total_sabados": int}
    """
    year = year or today_gt().year

    # Cargar empleados para encontrar a Henry
    employees = read_worksheet(WS_EMPLOYEES)
    if employees.empty:
        return {"error": "No hay empleados cargados", "insertados": 0}

    henry_match = employees[employees["nombre"].str.lower() == HENRY_NAME.lower()]
    if henry_match.empty:
        return {"error": f"{HENRY_NAME} no encontrado", "insertados": 0}

    henry = henry_match.iloc[0]
    henry_id = int(henry["id"])

    # Verificar que Henry esté activo
    if str(henry.get("activo", "")).upper() not in ("TRUE", "VERDADERO", "SI", "1"):
        return {"error": f"{HENRY_NAME} no está activo", "insertados": 0}

    # Cargar horas extras existentes
    overtime_df = read_worksheet(WS_OVERTIME)

    # Sábados pasados del año
    saturdays = get_saturdays_in_year(year)

    if overtime_df.empty:
        existing_saturdays = set()
    else:
        # Filtrar registros de Henry recurrentes
        mask = (
            (overtime_df["empleado_id"].astype(str) == str(henry_id))
            & (overtime_df["recurrente"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"]))
        )
        henry_recurrent = overtime_df[mask].copy()
        if not henry_recurrent.empty:
            henry_recurrent["fecha_parsed"] = henry_recurrent["fecha"].apply(parse_date)
            existing_saturdays = set(d for d in henry_recurrent["fecha_parsed"] if d is not None)
        else:
            existing_saturdays = set()

    # Construir filas faltantes
    timestamp = now_gt().strftime("%Y-%m-%d %H:%M:%S")
    rows_to_insert = []
    for sat in saturdays:
        if sat not in existing_saturdays:
            rows_to_insert.append([
                sat.strftime("%Y-%m-%d"),       # fecha
                henry_id,                        # empleado_id
                HENRY_NAME,                      # empleado_nombre
                HENRY_SATURDAY_HOURS,            # horas
                "Sábado recurrente (7:00-14:00)", # motivo
                "SISTEMA",                        # aprobado_por
                timestamp,                        # timestamp
                "TRUE",                           # recurrente
            ])

    if rows_to_insert:
        append_rows(WS_OVERTIME, rows_to_insert)
        invalidate_cache()

    return {
        "insertados": len(rows_to_insert),
        "ya_existian": len(existing_saturdays),
        "total_sabados": len(saturdays),
    }


# ============================================================
# AGREGACIONES DE HORAS EXTRAS
# ============================================================
def load_overtime_df(year: Optional[int] = None) -> pd.DataFrame:
    """Carga la worksheet de horas extras con fecha parseada y filtrada por año."""
    df = read_worksheet(WS_OVERTIME)
    if df.empty:
        return df

    df["fecha_parsed"] = df["fecha"].apply(parse_date)
    df = df[df["fecha_parsed"].notna()].copy()
    df["horas"] = pd.to_numeric(df["horas"], errors="coerce").fillna(0)

    if year is not None:
        df = df[df["fecha_parsed"].apply(lambda d: d.year == year)]

    return df.reset_index(drop=True)


def get_overtime_today() -> pd.DataFrame:
    """Horas extras registradas hoy."""
    df = load_overtime_df()
    if df.empty:
        return df
    today = today_gt()
    return df[df["fecha_parsed"] == today].reset_index(drop=True)


def get_overtime_this_week() -> pd.DataFrame:
    """Horas extras de la semana en curso (lunes a domingo)."""
    df = load_overtime_df()
    if df.empty:
        return df
    today = today_gt()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    mask = df["fecha_parsed"].apply(lambda d: monday <= d <= sunday)
    return df[mask].reset_index(drop=True)


def get_overtime_this_month() -> pd.DataFrame:
    """Horas extras del mes en curso."""
    df = load_overtime_df()
    if df.empty:
        return df
    today = today_gt()
    mask = df["fecha_parsed"].apply(
        lambda d: d.year == today.year and d.month == today.month
    )
    return df[mask].reset_index(drop=True)


def get_overtime_matrix(year: int) -> pd.DataFrame:
    """
    Genera la matriz mensual de horas extras: filas=empleados, columnas=meses.
    Réplica de tu Excel "HORAS EXTRAS BO - 2,026".

    Returns: DataFrame con columnas [Empleado, Enero, Febrero, ..., Diciembre, TOTAL]
    """
    employees = read_worksheet(WS_EMPLOYEES)
    if employees.empty:
        return pd.DataFrame()

    # Filtrar activos y ordenar por id
    employees = employees[
        employees["activo"].astype(str).str.upper().isin(["TRUE", "VERDADERO", "SI", "1"])
    ].sort_values("id").reset_index(drop=True)

    overtime = load_overtime_df(year)

    # Inicializar matriz con ceros
    matrix_rows = []
    for _, emp in employees.iterrows():
        emp_id = int(emp["id"])
        emp_name = emp["nombre"]
        row = {"Empleado": emp_name.upper()}
        emp_total = 0.0

        for month_num in range(1, 13):
            if overtime.empty:
                hours = 0.0
            else:
                mask = (
                    (overtime["empleado_id"].astype(str) == str(emp_id))
                    & (overtime["fecha_parsed"].apply(lambda d: d.month == month_num))
                )
                hours = overtime[mask]["horas"].sum()
            row[MONTHS_ES[month_num]] = hours
            emp_total += hours

        row["TOTAL"] = emp_total
        matrix_rows.append(row)

    df_matrix = pd.DataFrame(matrix_rows)

    # Fila TOTAL al final
    totals_row = {"Empleado": "TOTAL"}
    monthly_totals_total = 0.0
    for month_num in range(1, 13):
        col = MONTHS_ES[month_num]
        total = df_matrix[col].sum()
        totals_row[col] = total
        monthly_totals_total += total
    totals_row["TOTAL"] = monthly_totals_total
    df_matrix = pd.concat([df_matrix, pd.DataFrame([totals_row])], ignore_index=True)

    return df_matrix


def format_hours_cell(h: float) -> str:
    """Formato 'X hrs' para celdas, vacío si es 0."""
    if h is None or h == 0:
        return ""
    if h == int(h):
        return f"{int(h)} hrs"
    return f"{h:.1f} hrs"


# ============================================================
# AGGREGADOS POR EMPLEADO
# ============================================================
def total_overtime_by_employee(year: Optional[int] = None) -> pd.DataFrame:
    """Total de horas extras por empleado en el año."""
    df = load_overtime_df(year)
    if df.empty:
        return pd.DataFrame(columns=["empleado_id", "empleado_nombre", "total_horas"])

    grouped = df.groupby(["empleado_id", "empleado_nombre"], as_index=False)["horas"].sum()
    grouped = grouped.rename(columns={"horas": "total_horas"})
    return grouped.sort_values("total_horas", ascending=False).reset_index(drop=True)
