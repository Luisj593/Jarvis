# Actividad 5 — Aprendizaje explícito y versiones

Implementación independiente `VersionedLearning`, con SQLite y permisos exigidos por operación.
La enseñanza se registra **solo** mediante `teach`; no se aprende de mensajes normales.

## Operaciones
- `teach(category,key,value,project=None)`: crea versión 1, rechaza duplicados.
- `correct(category,key,value,expected_version,project=None)`: corrige, aumenta versión.
- `current(category,key,project=None)`: consulta vigente; omite registros eliminados.
- `history(category,key,project=None)`: historial cronológico.
- `delete(category,key,expected_version,project=None)`: eliminación reversible.
- `restore(category,key,expected_version,project=None,from_version=None)`: recupera.
- `revert(category,key,expected_version,from_version,project=None)`: recupera una versión anterior sin borrar el historial.
- `purge(category,key,expected_version,confirmation,project=None)`: exige eliminación reversible previa y confirmación literal `ELIMINAR DEFINITIVAMENTE`; elimina registros de tablas activas e historial.

## Límites de seguridad
- El `Principal` debe venir de un adaptador que autentique al propietario. No hay autenticación en este módulo.
- `VersionConflict` impide sobrescribir cambios de una versión más reciente.
- No se permite editar un registro eliminado ni restaurar una versión histórica eliminada.
- `purge` no garantiza borrado físico de páginas SQLite, WAL, copias de seguridad ni medios de almacenamiento.
- El módulo usa tablas `learning_items` y `learning_history` separadas. **No migra** registros anteriores de `profile_memories` ni `lessons`. Esa integración queda pendiente.
- La capa conversacional no está conectada todavía. Sin cifrado ni sincronización.
- No almacenar secretos o datos personales sensibles.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
