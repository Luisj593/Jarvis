# Actividad 8 — Contexto conversacional por sesión

`ConversationContext(path, principal)` integra `UnifiedIntentEngine` y una
tabla local `conversation_sessions` con `(owner_id,session_id)` como clave.
Cada sesión debe seleccionar explícitamente un proyecto con `select_project`
antes de interpretar mensajes.

## Flujo
1. `select_project(session_id,project)` requiere permiso de escritura y
   limpia cualquier intención previa al cambiar de proyecto.
2. `respond(session_id,text)` requiere lectura; interpreta mensajes con el
   motor unificado. Las intenciones reconocidas actualizan el contexto con
   permiso de escritura.
3. Referencias exactas como «eso», «lo anterior», «ese proyecto» y «continúa»
   recuperan únicamente la última intención reconocida de esa sesión.
4. Si no hay proyecto o antecedente claro, devuelve `clarify`.
5. Una ambigüedad, conflicto o expresión desconocida borra la referencia
   previa para impedir continuaciones erróneas.
6. `clear(session_id)` requiere `memory:delete` y elimina la sesión.

## Privacidad y límites
- No se guarda el texto completo de mensajes, únicamente proyecto, última
  intención y último estado. No hay comprensión de pronombres ni análisis
  semántico general; las referencias son frases exactas predefinidas.
- El propietario se deriva de un `Principal` que debe haber sido autenticado
  por un adaptador externo. El módulo no implementa autenticación.
- El almacenamiento de contexto es persistente entre instancias, pero todavía
  no incluye caducidad automática ni limpieza por antigüedad.
- La selección del proyecto es explícita; no se permite heredar referencias
  de otro proyecto ni de otra sesión.
- Ninguna intención se ejecuta. Sin llamadas a red, Android ni Railway.
- No se modifica el motor Android ni se hace despliegue.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
