# Actividad 11 — Procedimientos, tareas y dependencias

`ProcedureRegistry(path,principal)` gestiona procedimientos y tareas
asociados a proyectos existentes en `ProjectRegistry`.

## API
- `create_procedure(project_id,title)`, `get_procedure`, `list_procedures`.
- `add_task(project_id,procedure_id,title,assignee=None,depends_on=(),expected_version=None)`.
- `list_tasks(project_id,procedure_id)`.
- `update_task(project_id,procedure_id,task_id,expected_version,title=None,assignee=None,status=None)`.
- `progress(project_id,procedure_id)`: número de tareas y porcentaje completado.

Estados de tarea: `pending`, `in_progress`, `blocked`, `done`, `cancelled`.
Las dependencias solo pueden apuntar a tareas del mismo propietario,
proyecto y procedimiento. Una tarea no puede completarse hasta que todas
sus dependencias estén completadas. Las dependencias se fijan al crear la
tarea; esta API no ofrece edición posterior de dependencias, evitando ciclos.
No se puede reabrir un prerrequisito si una tarea dependiente ya está completada.

## Seguridad
- Consultas: `memory:read`; creación y actualización: `memory:write`.
- `owner_id` debe derivarse de identidad autenticada en una capa externa.
- Las modificaciones usan transacciones y control optimista de versión.
- El responsable es una etiqueta textual, no una cuenta autenticada ni
  una delegación de permisos.
- No hay ejecución automática de tareas, notificaciones ni despliegues.
- No hay eliminación en esta API ni cascadas de datos.
- SQLite no está cifrado y la integridad referencial entre tablas depende
  de las comprobaciones de la API; no hay claves foráneas declaradas.
- El registro de procedimientos no se conecta todavía al diálogo Android.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
