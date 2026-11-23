# JARVIS Research — nivel autónomo (fase de desarrollo)

Implementación Python 3.12 estándar, sin modelos externos de IA.

## Funciones implementadas
- Investigación de titulares mediante RSS HTTPS de fuentes fijas: `tecnologia`
  (BBC Mundo Tecnología) y `mundo` (BBC Mundo).
- Filtro determinista por términos del tema, fecha y enlace de la fuente.
- Hasta 12 titulares por consulta, hasta 512 KiB de RSS y 8 segundos
  de espera de red. No analiza ni verifica el contenido completo.
- Programación **opt-in** de temas con intervalos de 60 a 43200 minutos;
  cancelación y aislamiento por propietario.
- Ejecución de trabajos vencidos mediante `Research.run_due()` con
  reserva SQLite transaccional, límite por lote e historial.
- No aprendizaje implícito ni ejecución de comandos.
- API autenticada por el Bearer existente:
  `POST /v1/core/research/query` con `{"topic":"Android","source":"tecnologia"}`;
  `POST /v1/core/research/schedule` con
  `{"topic":"Android","source":"tecnologia","interval_minutes":1440}`;
  `POST /v1/core/research/cancel` con `{"job_id":"..."}`;
  `GET /v1/core/research/jobs`, `GET /v1/core/research/history`.

## Estado real de autonomía
La agenda persiste y `run_due()` puede ejecutar investigaciones vencidas,
pero **NO hay planificador en segundo plano instalado**. Registrar un trabajo
no implica que se ejecute automáticamente hasta integrar un worker confiable
con autenticación y supervisión. Tampoco se envían notificaciones Android ni
respuestas de voz; requieren integración móvil futura.

## Seguridad
- No admite URL arbitraria de usuario ni destinos privados; lista de fuentes
  fija, HTTPS, redirecciones bloqueadas y límite de bytes.
- El proveedor RSS puede conocer la IP del servidor.
- Las fuentes pueden cambiar, dejar de funcionar o bloquear peticiones.
- Los titulares no son conclusiones verificadas. Se muestran fuentes.
- Las búsquedas manuales requieren `memory:read`; programar y cancelar
  requieren `memory:write`.
- El puente API usa un único token y propietario configurados en servidor;
  no equivale a identidad multiusuario ni cuota por persona.
- Antes de habilitar en un servidor público: rate limiting, auditoría de
  consultas, políticas de retención, aislamiento de red y worker seguro.
- No modificar main, APK ni Railway en esta fase.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
Las pruebas de RSS usan respuestas simuladas y no garantizan conectividad
ni disponibilidad real de BBC Mundo.
