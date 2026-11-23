# JARVIS OpenAI Bridge (pruebas)

Servicio HTTP mínimo que recibe instrucciones de JARVIS y consulta la API Responses de OpenAI. **No implementa todavía edición de código, memoria persistente, integración Android ni despliegues automáticos.**

## Configuración

Requiere Node.js 20 o superior. En el servidor (por ejemplo, un servicio aislado de Railway), configurar secretos:
- `OPENAI_API_KEY`: clave de API de OpenAI, solo en servidor.
- `JARVIS_BRIDGE_TOKEN`: token aleatorio largo para autenticar peticiones. **No insertar este token fijo en la APK pública**; antes de conectar Android, implementar autenticación de usuarios con tokens de corta duración.
- `OPENAI_MODEL`: modelo opcional (por defecto gpt-4.1-mini).
- `PORT`: puerto HTTP (Railway lo proporciona).

Ejecutar `npm test` y `npm start` desde este directorio.

## Endpoints

`GET /health` → `{"status":"ok"}`

`POST /v1/command` con cabecera `Authorization: Bearer <token>` y JSON:
```json
{"project":"Sistema nocturno","instruction":"Analiza el módulo de inventario"}
```
Respuesta: `{"answer":"...","response_id":"..."}`

## Seguridad y próximos pasos

- Solo desplegar detrás de HTTPS; nunca publicar secretos en GitHub.
- Antes de permitir tráfico real desde la APK: autenticación por usuario, límites de peticiones, auditoría, control de costes y autorización granular para herramientas.
- Las herramientas GitHub/Railway deben operar exclusivamente en ramas de pruebas; producción requiere aprobación explícita.
- No conectar a producción hasta completar pruebas de integración y autorización del usuario.
