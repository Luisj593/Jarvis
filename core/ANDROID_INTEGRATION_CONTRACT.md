# Contrato propuesto para futura integración Android — NO implementado

## 1. Límites de confianza
La futura aplicación Android debe autenticar la identidad local del usuario,
aislar los datos por cuenta, proteger la clave del almacenamiento y generar
`Principal(owner_id, frozenset(permisos))` **solo después** de autenticar.
Nunca aceptar `owner_id` ni permisos arbitrarios de un texto hablado o de
una petición sin validar. La voz por sí sola no autentica a una persona.

## 2. Interfaces existentes (Python, no Kotlin)
- `Request(text, project="general", session_id="default")` y
  `Response(text, intent, memory_ids, requires_confirmation)`: contrato
  original del motor básico; no representa todas las funciones posteriores.
- `ConversationContext(path,principal).select_project(session_id,project)`
  y `.respond(session_id,text)`: requiere permisos de memoria y devuelve
  `ConversationTurn(status,project,intent,response,candidates,source)`.
- `ResponseComposer(path,principal)`: capa de respuestas personalizadas.
- `ProjectRegistry(path,principal)`: `create/get/list/update/delete`;
  cambios con `expected_version`.
- `ProcedureRegistry(path,principal)`: procedimientos, tareas y dependencias.
- `ProjectTracking(path,principal)`: `report/reports/decide/revise/history`.
- `AuditedActions(path,principal,strict_policies=True)`: `preview`,
  `confirm`, `set_project_permission`, `history`, `verify_integrity`,
  `recovery_preview`.

## 3. Protocolo de acciones que deberá implementar el adaptador
1. Mostrar el proyecto por ID y nombre, operación, estado previo y posterior,
   nivel de riesgo, versión y vencimiento del ticket.
2. Consultar permisos de proyecto; con modo estricto, denegar por defecto.
3. Guardar el ticket únicamente durante el flujo de confirmación; no incluir
   en logs, analítica, notificaciones ni mensajes de voz.
4. Solicitar confirmación humana con interfaz protegida. La frase requerida
   para riesgo alto es `CONFIRMAR ACCIÓN DE ALTO RIESGO`; para riesgo bajo,
   `CONFIRMAR ACCIÓN`. El núcleo no verifica biometría ni presencia física.
5. Confirmar una sola vez; si la versión cambió, volver a simular.
6. Mostrar resultado de la operación solo después de confirmación exitosa;
   registrar errores de forma segura y sin exponer secretos.

## 4. Puente tecnológico pendiente
No existe puente Python/Kotlin ni API de integración definida o implementada.
Elegir posteriormente entre núcleo embebido revisado y un servicio autenticado,
sin asumir que Python se ejecutará automáticamente en Android.
No se habilita `Hey Jarvis`, permisos de micrófono, accesibilidad, acciones
de sistema ni segundo plano en esta fase.

## 5. Pruebas obligatorias antes de integración
Identidad y bloqueo de pantalla, persistencia cifrada, restauración,
reinstalación, permisos Android, audio, reintentos, cancelación, expiración,
concurrencia, consumo de batería, funcionamiento sin red, migración de datos
y prueba real en dispositivos. La APK actual no se ha tocado.
