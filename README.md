[README.md](https://github.com/user-attachments/files/27818474/README.md)
# Attendance BackOffice STT

Sistema de gestión de asistencia para el departamento de BackOffice de **STT Logistics Group**.

![Built with Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B?logo=streamlit&logoColor=white)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Database-Google_Sheets-34A853?logo=googlesheets&logoColor=white)

---

## ✨ Features

- 🟢 **Asistencia en Vivo** — Timeline visual del día actual con la línea "AHORA" en tiempo real
- 📋 **Registro de Excepciones** — Llegadas tarde, salidas tempranas, ausencias
- ⏱️ **Horas Extras** — Tracking diario, semanal y mensual con autorización
- 🏖️ **Vacaciones** — 15 días/año por empleado, cálculo automático de disponibles
- 🇺🇸 **Feriados US** — Coverage por feriado
- 🎂 **Cumpleaños** — Countdown de días faltantes
- 📅 **Antigüedad** — Tiempo en la empresa actualizado en tiempo real
- 🔄 **Auto-refresh** — Dashboard cada 60s, otras vistas cada 5 min

## 🏗️ Stack

- **Frontend**: Streamlit + CSS custom
- **Backend**: Google Sheets (vía gspread)
- **Auth**: bcrypt
- **Charts**: Plotly
- **TZ**: America/Guatemala (toda la app)

## 🚀 Setup local

```bash
git clone https://github.com/sofiamorataya-ui/Attendance-BackOffice-STT.git
cd Attendance-BackOffice-STT
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

1. Crea un Google Sheet llamado `Attendance_BackOffice_STT_DB`
2. Comparte el Sheet con tu service account (permisos de Editor)
3. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completa
4. Ejecuta:

```bash
streamlit run app.py
```

5. Login con `sofi` o `evelyn` (contraseñas definidas en `secrets.toml`)
6. Ve a **🛠️ Setup Inicial** y ejecuta los pasos 1 → 7 una sola vez

## ☁️ Deploy en Streamlit Cloud

1. Push el repo a GitHub
2. Conecta en https://streamlit.io/cloud
3. En **Settings → Secrets** pega el contenido de tu `secrets.toml`
4. Deploy 🚀

## 📂 Estructura

```
app.py                   # Entry point + auth + routing
core/
  config.py              # Constantes, paleta, TZ
  auth.py                # Login bcrypt
  sheets.py              # Cliente Google Sheets cacheado
  schedules.py           # Horarios base de cada empleado
  time_utils.py          # Helpers TZ Guatemala
  ui.py                  # Componentes UI reutilizables
modules/
  dashboard_live.py      # Asistencia en vivo
  attendance_log.py      # Registro de excepciones
  overtime.py            # Horas extras
  vacations.py           # Vacaciones
  holidays.py            # Feriados US
  birthdays.py           # Cumpleaños
  tenure.py              # Antigüedad
  exceptions.py          # Permisos
  admin_seed.py          # Setup inicial (oculto en prod)
data/
  employees_seed.py      # Datos maestros iniciales
```

## 👥 Roles

| Usuario | Rol | Permisos |
|---|---|---|
| `sofi` | Supervisora | Lectura + escritura completa |
| `evelyn` | Manager | Lectura + escritura completa |

## 📝 Notas

- **Refresh**: Dashboard cada 60s, otras vistas cada 5 min
- **TZ**: Toda la app opera en `America/Guatemala`
- **Vacaciones**: 15 días/año, acumulación proporcional 1.25 días/mes
- **Henry**: Sábados 7:00–14:00 son 7 hrs extras recurrentes automáticas

---

© STT Logistics Group · 2026
