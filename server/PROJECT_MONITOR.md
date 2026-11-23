# Catálogo y observabilidad de proyectos — desarrollo

## Inventario observado (2026-11-23)
GitHub accesible: `Luisj593/Jarvis`, `Luisj593/Plazado`.
Railway accesible: JARVIS-AI, NightGest-ERP-Testing, NightGest-ERP,
SV-Personalizado, ServicioPro, Plazado - Pruebas y shimmering-gentleness.
El nombre `shimmering-gentleness` contiene servicios Plazado, pero se
conserva el nombre real del proyecto Railway.

## API autenticada
- `GET /v1/core/monitor/catalog`: inventario de referencia, no salud en vivo.
- `GET /v1/core/monitor/report`: informe de lectura, sin modificar proyectos.

## Configuración para monitoreo
- `JARVIS_MONITOR_GITHUB_TOKEN`: token de GitHub con permiso de lectura de
  metadatos, Actions y Issues de los repositorios autorizados.
- `JARVIS_MONITOR_RAILWAY_TOKEN`: token Railway de consulta; el monitor
  solo envía consultas GraphQL `query`, nunca mutaciones.

No se incluyen credenciales en el repositorio ni en la APK.
Si falta un token, se devuelve `unknown` y
`monitor_token_not_configured`; no se infiere disponibilidad.

## Alcance real y límites
- GitHub: disponibilidad de repositorio, número de issues abiertos
  (incluye PR según API), última ejecución de Actions y su conclusión.
- Railway: descubrimiento de proyectos, servicios y entornos cuando
  responde la API. **No se consultan aún logs ni despliegues de servicios**;
  cada estado de servicio permanece `unknown`.
- El informe es bajo demanda, no existe cron ni alerta automática.
- No se toca código, variables ni bases de datos de proyectos externos.
- Para acceso desde Android se reutiliza el token de API JARVIS; debe
  limitarse a dispositivos autorizados. El token del proveedor solo
  reside en el entorno del servidor.
- Este módulo no modifica main ni despliega producción.

## Pruebas
`PYTHONPATH=core python -m unittest discover -s core/tests -v`
