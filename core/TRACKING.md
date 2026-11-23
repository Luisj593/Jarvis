# Actividad 12 — Seguimiento consolidado y decisiones

`ProjectTracking(path,principal)` ofrece:
- `report(project_id)`: resumen de proyecto, procedimientos, tareas, completadas, porcentaje y bloqueos.
- `reports()`: reportes de todos los proyectos del propietario.
- `decide(project_id,title,rationale,outcome)`: registra decisión explícita.
- `revise(project_id,decision_id,expected_version,title,rationale,outcome)`: nueva versión con control de concurrencia.
- `decisions(project_id)` y `history(project_id,decision_id)`: consultas y versiones anteriores.

Bloqueos: tarea marcada `blocked` o tarea no completada con dependencias
no completadas. Una tarea `cancelled` no cuenta como completada. Porcentaje:
tareas completadas / todas las tareas; si no hay tareas, 0%.

Todas las operaciones validan `owner_id` y `project_id`, exigen permisos
`memory:read` o `memory:write`, y usan SQL parametrizado. El historial de
decisiones es append-only a través de esta API. Las revisiones usan transacción
`BEGIN IMMEDIATE` y versión esperada.

Limitaciones: el reporte describe únicamente registros internos, no comprueba
el estado real de sistemas externos. Los bloqueos no infieren causas externas.
Las decisiones no ejecutan acciones. No hay integración con Android, no hay
cifrado SQLite, y el Principal debe autenticarse fuera del módulo.
No hay integración de decisiones con el motor conversacional todavía.

Pruebas: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
