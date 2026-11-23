# Actividad 4 — Memoria personal, preferencias y proyectos

## Categorías
- `personal`: datos enseñados explícitamente por el propietario; **no** se incluyen en el contexto por defecto.
- `preference`: preferencias generales reutilizables en distintos proyectos.
- `project`: datos limitados a un proyecto específico, nunca mezclados con otro.

## API
`ProfileMemory(path, owner_id)` utiliza la misma base SQLite que `SQLiteMemoryStore`, pero una tabla separada `profile_memories`.
`put(category,key,value,project=None)`, `get(...)`, `list(...)`, `delete(...)` y
`context(project=None,include_personal=False)`. `put` actualiza por clave en su alcance y conserva ID.

## Ejemplo
```python
from jarvis_core.profile import ProfileMemory
memory = ProfileMemory("/ruta/privada/jarvis.sqlite", "usuario-autenticado")
memory.put("preference", "estilo", "respuestas directas")
memory.put("project", "regla", "no desplegar sin autorización", project="JARVIS")
print(memory.context("JARVIS"))
```

## Limitaciones y privacidad
- El sistema **no infiere automáticamente** preferencias ni extrae datos de conversaciones.
- `owner_id` debe ser establecido por un adaptador autenticado. Este módulo no autentica.
- La recuperación de contexto es explícita y determinista; no es búsqueda semántica.
- SQLite no cifra datos. No guardar secretos ni información sensible en esta fase.
- El motor de conversación existente todavía no utiliza esta memoria estructurada.
- No hay exportación, respaldo, historial de cambios ni migraciones versionadas.
- El permiso por operación se debe aplicar en la futura capa de acceso; esta clase no lo impone.

## Validación
`PYTHONPATH=core python -m unittest discover -s core/tests -v`

## Política
Solo rama de desarrollo; no modificar Android, main, servidor Railway ni desplegar.
