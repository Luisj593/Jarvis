# Actividad 9 — Respuestas personalizadas sin inventar información

`ResponseComposer(path, principal)` utiliza `ConversationContext` y
`UnifiedIntentEngine`. Devuelve `PersonalizedResponse` con texto, estado,
intención, proyecto, nivel de certeza, origen y `executed=False`.

## Personalización
Lee únicamente la preferencia explícita global `preference/tono`.
Valores admitidos: breve, conciso, directo, respuestas directas,
detallado, explicativo o formal. Otros valores usan tono neutral.
No extrae datos personales ni usa contenido de proyectos para afirmar
hechos sobre su estado.

## Incertidumbre
- `recognized`: intención conocida, **no** implica ejecución ni datos reales.
- `ambiguous`: varias intenciones; pide elegir.
- `conflict`: instrucción incompatible con un comando reservado.
- `insufficient`: falta proyecto o antecedente; solicita contexto.
- `unknown`: expresión no enseñada; pide explicación.

## Límites
No hay generación libre, búsqueda semántica, voz, conexión Android, acceso
a herramientas externas, consulta de estado de proyectos ni ejecución.
No se almacena una transcripción nueva. El texto de las respuestas no es
evidencia de que se haya realizado una operación.
La autenticación del Principal debe proporcionarla un adaptador confiable.
La preferencia de tono es leída desde ProfileMemory, cuya API directa
no aplica permisos por sí sola. No almacenar secretos en SQLite sin cifrado.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
