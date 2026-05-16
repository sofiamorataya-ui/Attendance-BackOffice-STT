[README.md](https://github.com/user-attachments/files/27839369/README.md)
# Attendance BackOffice STT

Sistema integral de gestión de asistencia para el equipo BackOffice de STT Logistics Group.

## 🎯 Módulos disponibles

| Módulo | Descripción |
|---|---|
| **🟢 Asistencia en Vivo** | Timeline visual en tiempo real (auto-refresh 60s). Quién trabaja, en almuerzo, día libre o ausente. Línea "AHORA" móvil. |
| **📋 Registro Asistencia** | Excepciones (llegada tarde, salida temprano, ausente, permiso, incapacidad). El selector de hora calcula los minutos tarde automáticamente. |
| **⏱️ Horas Extras** | Matriz mensual + formulario + detalle día/semana/mes. Sábados de Henry auto-inyectados (7h c/u). |
| **🏖️ Vacaciones** | 15 días/empleado/año. Tomados, disponibles, acumulados (1.25 días/mes). |
| **🚨 Permisos** | Personales, incapacidad, duelo, otros. Rango fechas, motivo, badge ACTIVO. |
| **🇺🇸 Feriados US** | 13 feriados federales. Asignación de coverage. Badge HOY/PASADO/EN Xd. |
| **🎂 Cumpleaños** | Hero card del próximo. Ordenado por proximidad. |
| **📅 Antigüedad** | Tiempo en la empresa en vivo (años, meses, días). Badge 🌟 VETERANO si 3+ años. |
| **👥 Empleados** | CRUD: directorio, crear, editar, configurar horarios semanales. |
| **🛠️ Setup Inicial** | Wizard de 7 pasos para inicializar el Google Sheet la primera vez. |

## 🚀 Deploy en Streamlit Community Cloud

1. Subir todo el contenido del ZIP a GitHub (sobrescribiendo lo anterior)
2. No olvides el archivo `.python-version` con `3.12`
3. Verificar `secrets.toml` (variables raíz ANTES del bloque `[gcp_service_account]`)
4. Reboot app en Streamlit Cloud
5. Primera vez: contraseña de setup → Setup Inicial → ejecuta los 7 pasos

## 🔧 Stack técnico

- Streamlit 1.42+ con CSS custom + componentes HTML embebidos
- Google Sheets vía gspread (8 worksheets)
- bcrypt + sesión Streamlit para auth
- Twemoji SVG (renderiza igual en Windows/Mac/Linux/iOS/Android)
- Snackbar Material Design custom (4 seg auto-dismiss, sin globos infantiles)
- Timezone: America/Guatemala
- Auto-refresh: 60s en dashboard, 5 min en otros módulos

## 📊 Worksheets de Google Sheets

| Hoja | Propósito |
|---|---|
| Empleados | Datos maestros del equipo |
| Horarios | Horario semanal por empleado (7 filas c/u) |
| Asistencia | Log de excepciones |
| Horas_Extras | Horas extras autorizadas |
| Vacaciones | Días de vacaciones tomados |
| Permisos | Permisos y ausencias |
| Feriados | Feriados US + coverage |
| Usuarios | Credenciales (bcrypt) |

## 👥 Equipo BackOffice (8 personas)

- **GT** 🇬🇹 — Evelyn (Manager), Sofia (Supervisora), Alessandro, Javier, Sebastian
- **VE** 🇻🇪 — Anny, Henry (sábados recurrentes), Mark

---

Construido por Pablo para Sofia Morataya · STT Logistics Group · 2026
