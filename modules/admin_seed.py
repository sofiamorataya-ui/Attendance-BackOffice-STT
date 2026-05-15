"""
modules/admin_seed.py
Página de setup inicial. Solo se usa la PRIMERA VEZ para poblar el Sheet.
Después de inicializar todo, se puede ocultar del menú.
"""
import streamlit as st
from core.sheets import (
    ensure_headers, overwrite_worksheet, read_worksheet,
    WORKSHEET_HEADERS, get_spreadsheet,
)
from core.config import (
    WS_EMPLOYEES, WS_SCHEDULES, WS_HOLIDAYS, WS_USERS, DAYS_ES,
)
from core.schedules import SCHEDULES
from core.auth import seed_initial_users, hash_password
from data.employees_seed import EMPLOYEES_SEED, US_HOLIDAYS_2026


def render():
    """Renderiza la página de setup inicial."""
    st.markdown("### 🛠️ Setup Inicial del Google Sheet")
    st.caption(
        "Esta página solo se usa la primera vez para poblar el Google Sheet con datos base. "
        "Una vez inicializado, NO la uses de nuevo (sobrescribe datos)."
    )

    # --- Verificación de conexión ---
    st.markdown("#### 1. Verificar conexión")
    if st.button("🔌 Probar conexión a Google Sheets"):
        try:
            ss = get_spreadsheet()
            ws_names = [w.title for w in ss.worksheets()]
            st.success(f"✅ Conectado a: **{ss.title}**")
            st.write("Worksheets encontradas:", ws_names)
        except Exception as e:
            st.error(f"❌ Error de conexión: {e}")
            return

    st.divider()

    # --- Headers ---
    st.markdown("#### 2. Asegurar headers de todas las worksheets")
    if st.button("📋 Crear/verificar headers"):
        try:
            status = ensure_headers()
            st.success("Headers verificados:")
            st.json(status)
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # --- Empleados ---
    st.markdown("#### 3. Poblar empleados")
    if st.button("👥 Cargar lista de empleados"):
        try:
            headers = WORKSHEET_HEADERS[WS_EMPLOYEES]
            rows = [[emp[h] for h in headers] for emp in EMPLOYEES_SEED]
            overwrite_worksheet(WS_EMPLOYEES, headers, rows)
            st.success(f"✅ {len(rows)} empleados cargados.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # --- Horarios ---
    st.markdown("#### 4. Poblar horarios base")
    if st.button("📅 Cargar horarios semanales"):
        try:
            headers = WORKSHEET_HEADERS[WS_SCHEDULES]
            rows = []
            for emp in EMPLOYEES_SEED:
                name = emp["nombre"]
                emp_id = emp["id"]
                if name not in SCHEDULES:
                    continue
                for day in range(7):
                    sched = SCHEDULES[name].get(day)
                    if sched is None:
                        rows.append([
                            emp_id, name, day, DAYS_ES[day],
                            "", "", "", "", "TRUE",
                        ])
                    else:
                        entrada, salida, alm_i, alm_f = sched
                        rows.append([
                            emp_id, name, day, DAYS_ES[day],
                            entrada.strftime("%H:%M") if entrada else "",
                            salida.strftime("%H:%M") if salida else "",
                            alm_i.strftime("%H:%M") if alm_i else "",
                            alm_f.strftime("%H:%M") if alm_f else "",
                            "FALSE",
                        ])
            overwrite_worksheet(WS_SCHEDULES, headers, rows)
            st.success(f"✅ {len(rows)} filas de horarios cargadas.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # --- Feriados US ---
    st.markdown("#### 5. Poblar feriados US 2026")
    if st.button("🇺🇸 Cargar feriados de Estados Unidos"):
        try:
            headers = WORKSHEET_HEADERS[WS_HOLIDAYS]
            rows = [
                [h["fecha"], h["nombre"], "", "", "FALSE", ""]
                for h in US_HOLIDAYS_2026
            ]
            overwrite_worksheet(WS_HOLIDAYS, headers, rows)
            st.success(f"✅ {len(rows)} feriados cargados.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # --- Usuarios ---
    st.markdown("#### 6. Crear usuarios iniciales (Sofi y Evelyn)")
    st.caption("Las contraseñas se toman de `secrets.toml` → `[initial_users]`. Cámbialas después.")
    if st.button("🔐 Crear usuarios"):
        try:
            result = seed_initial_users()
            st.success(result)
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # --- Verificar todo ---
    st.markdown("#### 7. Verificar estado final")
    if st.button("📊 Ver resumen de todas las worksheets"):
        for ws_name in [WS_EMPLOYEES, WS_SCHEDULES, WS_HOLIDAYS, WS_USERS]:
            try:
                df = read_worksheet(ws_name)
                st.markdown(f"**{ws_name}**: {len(df)} filas")
                if ws_name == WS_USERS and not df.empty:
                    # No mostrar password hashes
                    st.dataframe(df.drop(columns=["password_hash"], errors="ignore"))
                else:
                    st.dataframe(df, height=200)
            except Exception as e:
                st.error(f"{ws_name}: {e}")
