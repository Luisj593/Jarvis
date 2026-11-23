# Actividad 10 — Registro de proyectos

`ProjectRegistry(path, principal)` registra proyectos locales en
`registered_projects`, sin modificar tablas anteriores.

## Campos
- `id`: UUID; `name`: nombre único por propietario (máximo 100 caracteres).
- `objective`: objetivo obligatorio (máximo 3000 caracteres).
- `priority`: `low`, `medium`, `high`, `critical`.
- `status`: `planned`, `active`, `paused`, `completed`, `archived`.
- `version`: aumenta en cada modificación; fechas de creación y actualización.

## Operaciones
- `create(name,objective,priority="medium",status="planned")` requiere `memory:write`.
- `get(id)`, `list(status=None)` requieren `memory:read`.
- `update(id,expected_version,**campos)` requiere `memory:write` y rechaza cambios obsoletos.
- `delete(id,expected_version,"ELIMINAR PROYECTO")` requiere `memory:delete`, versión actual y confirmación literal.

## Seguridad y límites
Cada consulta y mutación filtra por `owner_id`. El `Principal` debe venir
de autenticación externa real, aún no implementada. SQLite no está cifrado.
La eliminación afecta **solo** el registro del proyecto: no borra memorias,
reglas, ejemplos ni sesiones relacionadas; la limpieza integral requiere una
política de cascada y confirmación aparte. No hay historial de cambios de
proyecto, flujo de aprobación de transiciones ni integración conversacional.
No hay ejecución de acciones, cambios Android ni despliegue.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
