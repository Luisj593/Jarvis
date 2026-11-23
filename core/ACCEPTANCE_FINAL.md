# Actividad 18 — criterios de aceptación y cierre verificable

## Matriz de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Núcleo Python sin dependencias de IA externa | core/jarvis_core | Implementado |
| Memoria y enseñanza explícita | learning.py, profile.py, examples.py | Implementado |
| Resolución determinista de intenciones | unified.py | Implementado |
| Conversación por propietario y sesión | conversation.py | Implementado |
| Proyectos, procedimientos y tareas | projects.py, procedures.py | Implementado |
| Progreso, bloqueos y decisiones | tracking.py | Implementado |
| Catálogo cerrado y confirmaciones | actions.py | Implementado |
| Auditoría de confirmación atómica | audit.py, test_hardening_day17.py | Implementado en fachada |
| Políticas estrictas | strict_policies=True | Disponible, no predeterminado |
| Integración Android y voz | Contrato futuro | Pendiente |
| Autenticación real y cifrado | Manual de seguridad | Pendiente |
| Auditoría obligatoria para toda mutación | Acceso directo posible | Pendiente |
| Pruebas de seguridad en dispositivo | Requiere APK autorizada | Pendiente |

## Verificación reproducible
- Rama: `feature/jarvis-core-architecture-day02`.
- Workflow: `.github/workflows/core-tests.yml`.
- Comando: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
- Compilación sintáctica: `python -m compileall -q core`.
- El número de pruebas y resultado final deben tomarse del **último**
  GitHub Actions verde posterior a estos documentos, no de cifras anteriores.

## Criterio de salida
Se cierra la fase de documentación y núcleo en desarrollo, **no** el
producto JARVIS ni la integración móvil. No fusionar a main, reconstruir
APK o desplegar Railway sin nueva autorización.

## Trabajo recomendado posterior
1. Integración autenticada y cifrado de datos.
2. Auditoría obligatoria y atómica para todas las mutaciones críticas.
3. Política estricta por defecto y migración de proyectos anteriores.
4. Pruebas Android, permisos, activación por voz y consumo energético.
5. Pruebas de carga, restauración, revisión independiente y aceptación humana.
