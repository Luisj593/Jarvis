# Actividad 15 — Auditoría y recuperación controlada

`AuditedActions` es una fachada sobre `ControlledActions` que registra
simulaciones, confirmaciones, cambios de políticas y rechazos. Guarda el tipo
de error, sin incluir secretos, tokens ni frases de confirmación.

La cadena de eventos usa SHA-256 del contenido y del hash anterior, con
secuencia global por propietario. `verify_integrity()` detecta alteraciones
accidentales de registros existentes; **no es a prueba de un atacante con
acceso de escritura a SQLite**, que puede recomputar la cadena. No hay
firma externa, almacenamiento inmutable ni protección ante eliminación
completa de eventos.

`recovery_preview(project_id,previous_status)` prepara una acción
compensatoria; no revierte automáticamente ni elude confirmaciones,
políticas o control de versiones.

**Limitaciones importantes:** la auditoría cubre únicamente las operaciones
invocadas a través de `AuditedActions`. Llamadas directas a
`ControlledActions` no quedan registradas. La escritura del evento de
éxito ocurre después de la transacción de la acción; si falla el registro,
puede haber una acción aplicada sin evento. Los rechazos se registran en
una transacción aparte. No usar todavía como auditoría de cumplimiento
ni como garantía de integridad forense. El siguiente endurecimiento debe
unificar operación y auditoría en una misma transacción y restringir
el acceso directo a la API de acciones.

No hay despliegue, cambios en Android ni cambios en main.
Pruebas: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
