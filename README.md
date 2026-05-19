[README.md](https://github.com/user-attachments/files/28032314/README.md)
# Attendance BackOffice STT

Sistema integral de gestión de asistencia para el equipo BackOffice de STT Logistics Group.

## 🎯 Módulos disponibles

| Módulo | Descripción |
|---|---|
| **🟢 Asistencia en Vivo** | Timeline visual en tiempo real (auto-refresh 60s). Botón 🚨 por empleado para iniciar incidencias (puede iniciar AHORA → queda activa, o registrar con hora fin manual). Tooltip al hover con detalles. |
| **🚨 Incidencias** | Histórico con filtros día/semana/mes/año. Rankings duales (cantidad y tiempo). Cerrar incidencias activas con hora fin manual o "ahora". |
| **📋 Registro Asistencia** | Excepciones (llegada tarde, salida temprano, ausente, permiso, incapacidad). |
| **⏱️ Horas Extras** | Matriz mensual + formulario + detalle día/semana/mes. Cache invalidado al registrar (los datos se reflejan inmediato). |
| **🏖️ Vacaciones** | 15 días/empleado/año con acumulación proporcional. |
| **🚦 Permisos** | Personales, incapacidad, duelo, otros. Badge ACTIVO si está vigente. |
| **🇺🇸 Feriados US** | 13 feriados federales 2026. Cards con grid responsive (renderizado vía components.html para evitar fragmentación de Streamlit). |
| **🎂 Cumpleaños** | Hero card del próximo con countdown. |
| **📅 Antigüedad** | Tiempo en la empresa en tiempo real con badge VETERANO si ≥3 años. |
| **🧠 Resolución de Dudas** ⭐ | NUEVO. Reportes estructurados al team (dudas, observaciones, feedbacks individuales, reminders generales). Descarga PDF con formato corporativo STT. |
| **📝 Feedback Process** ⭐ | NUEVO. Replica el template DOCX corporativo. Genera link único por feedback que Sofi comparte por WhatsApp. El empleado abre el link sin login → lee → firma virtualmente → Sofi recibe la firma. Descarga PDF y DOCX del documento. |
| **👥 Empleados** | CRUD completo con horarios semanales. |
| **🛠️ Setup Inicial** | Wizard de 7 pasos para inicializar el Google Sheet. |

## 🆕 Firma virtual (vista pública sin login)

Cuando Sofi guarda un Feedback Process, se genera un link como:

```
https://attendance-backoffice-stt.streamlit.app/?feedback=FB-20260519143012-ABC123
```

El empleado abre ese link en su navegador (desde WhatsApp), ve el feedback, escribe su nombre,
opcionalmente deja un comentario, y firma virtualmente. La firma queda registrada en el sheet
y Sofi puede verla desde el historial.

## 🚀 Deploy

1. Sube todo a GitHub
2. Reboot la app en Streamlit Cloud
3. Login → Setup Inicial → Paso 2 (crea las 11 worksheets necesarias: Empleados, Horarios,
   Asistencia, Horas_Extras, Vacaciones, Permisos, Feriados, Usuarios, Incidencias,
   Reportes_Dudas, Feedback_Process)

## 🔧 Stack

- Streamlit 1.42+ + Google Sheets (gspread)
- bcrypt para auth
- Twemoji SVG para banderas (renderizan igual en todos los SO)
- reportlab para PDFs corporativos
- python-docx para exportar DOCX (formato Word)
- Auto-refresh: 60s en dashboard, 5 min en otros módulos
- Timezone: America/Guatemala

## 📊 Worksheets

| Hoja | Propósito |
|---|---|
| Empleados | Datos maestros del equipo |
| Horarios | Horario semanal por empleado |
| Asistencia | Log de excepciones de asistencia |
| Horas_Extras | Horas extras autorizadas |
| Vacaciones | Días de vacaciones tomados |
| Permisos | Permisos y ausencias |
| Feriados | Feriados US + coverage |
| Incidencias | Reportes en vivo durante el turno |
| Reportes_Dudas | Reportes diarios estructurados al team |
| Feedback_Process | Feedback formal con firma virtual |
| Usuarios | Credenciales (bcrypt) |

---

Construido por Pablo para Sofia Morataya · STT Logistics Group · 2026
