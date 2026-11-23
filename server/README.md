# JARVIS Brain — motor de reglas sin modelo de IA

Servidor experimental de aprendizaje explícito, sin dependencia de ChatGPT ni de modelos de lenguaje externos.

- GET /health: diagnóstico.
- GET /lessons: consulta enseñanzas (requiere Bearer JARVIS_API_TOKEN).
- POST /lessons: guarda enseñanza por proyecto.
- POST /chat: responde por coincidencia de reglas; acepta `message` y `project`, y reconoce `aprende:`, `recuerda:` y `cuando diga ` para registrar enseñanzas.

Limitaciones: no entiende conversación abierta ni interpreta intenciones complejas; los comandos son coincidencias textuales. Requiere configurar JARVIS_API_TOKEN como secreto de Railway. La aplicación Android aún no está conectada a este endpoint. El almacenamiento persistente debe mantenerse en /data/jarvis.sqlite con volumen Railway. No enviar claves dentro de la APK ni guardar secretos en las enseñanzas. No hay acciones automáticas en otros proyectos.
