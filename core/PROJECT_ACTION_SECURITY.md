# Actividad 14 — Políticas por proyecto y riesgo

La capa de acciones incorpora `set_project_permission(project_id, allowed,
expected_version=None)`. Requiere permisos `action:execute` y
`memory:write`, verifica el propietario y mantiene versión de política.
Una política configurada con `allowed=False` bloquea nuevas simulaciones
y confirmaciones pendientes. Cualquier cambio de versión invalida los tickets
anteriores, incluso si se vuelve a permitir la acción.

El riesgo se calcula desde el destino: `archived` y `completed` son
`high`, y requieren la frase exacta `CONFIRMAR ACCIÓN DE ALTO RIESGO`.
Otros estados requieren `CONFIRMAR ACCIÓN`. La validación de política,
ticket, versión del proyecto y modificación se realiza dentro de una misma
transacción SQLite. El ticket se consume una sola vez.

**Compatibilidad importante:** proyectos sin política explícita conservan el
comportamiento de la actividad 13 (permitidos si el Principal tiene los
permisos globales). Para entornos con autorización estricta, configurar una
política explícita para cada proyecto antes de habilitar acciones. Este
comportamiento no es un esquema de denegación predeterminada universal.

**Límites:** no existe autenticación de usuario ni segunda aprobación humana
real; el Principal debe venir de un adaptador autenticado. Los riesgos solo
clasifican el cambio de estado local, no operaciones externas. El SQLite
no está cifrado. La auditoría independiente se aborda en actividad 15.
No se modifica Android, main ni Railway.

Pruebas: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
