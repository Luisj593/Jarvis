# Actividad 7 — Motor unificado de intenciones

`UnifiedIntentEngine(path, principal)` integra los componentes existentes
`ExampleLearning`, `VersionedLearning` y `ProfileMemory` sin alterar sus tablas.

## Consultas
- `resolve(text,project=None)` devuelve `UnifiedResult` con estado
  `matched`, `ambiguous`, `conflict`, `unknown` o `clarify`.
- `context(project=None,include_personal=False)` devuelve preferencias globales
  y memorias del proyecto; datos personales solo mediante solicitud explícita.
- `current_rule(category,key,project=None)` consulta una regla versionada.
- `teach_example`, `teach_rule` y `correct_rule` son escrituras explícitas,
  protegidas con `memory:write`.

## Precedencia
1. Verificar permisos de lectura y validar entrada/proyecto.
2. Detectar comandos internos reservados (`teach`, `recall`).
3. Consultar ejemplos del proyecto, luego ejemplos globales.
4. Si los ejemplos son ambiguos, solicitar aclaración.
5. Si una intención aprendida contradice un comando reservado, bloquear por conflicto.
6. En ausencia de conflicto, reconocer comando reservado o intención enseñada.
7. No ejecutar acciones ni inferir nuevas intenciones de texto desconocido.

## Límites
- El motor es deliberadamente de **solo reconocimiento**: no despacha acciones,
  no escribe memoria en `resolve`, no interpreta contexto conversacional y no
  llama a servicios externos.
- `ProfileMemory` sigue siendo una API de almacenamiento sin permisos internos;
  el acceso controlado se realiza mediante `UnifiedIntentEngine.context`.
- Las memorias estructuradas y versionadas continúan en tablas separadas.
  No hay migración automática ni lectura unificada de ambas como reglas activas.
- `Principal` debe proceder de autenticación externa real, todavía no implementada.
- No almacenar secretos o información personal sensible; SQLite no está cifrado.
- No modificar APK, main ni Railway.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
