# Actividad 13 — Acciones controladas

Catálogo cerrado: solo `project.set_status`, operación local que actualiza el
estado de un proyecto existente. **No** ejecuta shell, GitHub, Railway, Android
ni comandos arbitrarios.

1. `catalog()`: consulta operaciones permitidas (`memory:read`).
2. `preview("project.set_status", project_id, {"status":"active"})`:
   exige `action:execute` y `memory:read`, valida propietario, proyecto,
   operación y esquema exacto de parámetros. Guarda un ticket aleatorio
   de un solo uso, con secreto almacenado como SHA-256, versión del proyecto
   y vencimiento de diez minutos. No cambia el proyecto.
3. `confirm(ticket,"CONFIRMAR ACCIÓN")`: exige `action:execute` y
   `memory:write`. En una transacción verifica identidad, token, expiración,
   versión y estado esperado; cambia el estado y consume el ticket de forma
   atómica. Rechaza reintentos, confirmaciones incompletas y cambios
   concurrentes.

Limitaciones: la identidad Principal requiere autenticación externa;
no hay interfaz Android, ni aprobación humana vinculada a una sesión real,
ni registro de auditoría de acciones independiente (actividad 15).
Los tickets caducados aún no se purgan automáticamente. SQLite no está
cifrado. La API permite solo cambios de estado locales; cualquier futura
acción externa requerirá autorización, validación y revisión separadas.

Pruebas: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
