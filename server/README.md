# JARVIS Brain API (experimental)

Endpoints: GET /health (public); GET /projects and GET/POST /lessons (Bearer JARVIS_API_TOKEN required).

**Security:** never commit tokens. Set JARVIS_API_TOKEN in Railway variables. Without token, protected endpoints are disabled. The database defaults to /tmp and **is ephemeral**; configure a persistent volume and JARVIS_DB_PATH before real training. This is a training API prototype, not an autonomous AI model, and projects are catalog-only, not connected.

## Conversación contextual (en desarrollo)

POST /chat requiere Authorization: Bearer <JARVIS_API_TOKEN> y JSON {"message":"...","history":[{"role":"user","content":"..."}],"project":"general"}. El historial se envía desde el cliente (máximo 20 turnos) y las enseñanzas del proyecto se leen desde SQLite. Requiere configurar OPENAI_API_KEY como variable privada en Railway y JARVIS_API_TOKEN. Sin ambas, el chat no está disponible. No guardar claves en GitHub ni dentro de la APK. No se realizan acciones en otros proyectos. Falta integrar el cliente Android y verificar la conversación real.
