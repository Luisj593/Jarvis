# Actividad 6 — Aprendizaje de expresiones equivalentes

`ExampleLearning` es un módulo Python independiente, sin LLM, llamadas de red ni dependencias de terceros.

## Contrato
- `teach(intent, expression, project=None)`: enseña explícitamente una frase asociada a una intención.
- `resolve(expression, project=None)`: devuelve `IntentMatch(status, intent, scope, candidates)`.
- `examples(intent, project=None)`: consulta frases enseñadas.
- `remove(identifier, project=None)`: elimina un ejemplo con permiso.
- `status`: `matched`, `ambiguous` o `unknown`.

## Reglas de resolución
1. Normalizar mayúsculas, acentos, puntuación y espacios.
2. Buscar coincidencias exactas en el proyecto indicado.
3. Si el proyecto no tiene coincidencias, buscar en el alcance global.
4. Si una expresión tiene varias intenciones en el alcance elegido, devolver `ambiguous` y no ejecutar ninguna.
5. Si no hay coincidencia, devolver `unknown`. No usar semejanza de palabras para adivinar.

## Seguridad y límites
- Requiere un `Principal` previamente autenticado; el módulo no autentica.
- Permisos `memory:read`, `memory:write`, `memory:delete` por operación.
- Los ejemplos se aíslan por propietario y proyecto; el global se comparte solo dentro del mismo propietario.
- No ejecuta herramientas, no aprende implícitamente y no modifica el motor Android.
- Se almacena en tabla separada `intent_examples`, sin migrar ni alterar tablas previas.
- No hay comprensión semántica: las frases equivalentes deben enseñarse individualmente.
- No conectar directamente una intención aprendida a operaciones sensibles sin confirmación.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
