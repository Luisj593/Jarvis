# JARVIS Core — arquitectura final de la fase 1–18

**Estado:** núcleo Python 3.12 de desarrollo. Sin LLM, sin red, sin conexión
a Android, sin despliegue de servicios. No equivale a una APK funcional.

## Capas y responsabilidades

| Capa | Módulos | Responsabilidad |
|---|---|---|
| Contratos iniciales | contracts.py, engine.py, intent.py, memory.py | Solicitud/respuesta y enseñanza determinista |
| Persistencia y acceso | storage.py, security.py | SQLite por owner_id; Principal y permisos |
| Aprendizaje | profile.py, learning.py, examples.py, unified.py | Preferencias, reglas versionadas, ejemplos, resolución de conflictos |
| Conversación | conversation.py, responses.py | Sesión, proyecto seleccionado, referencias, formato de respuesta |
| Proyectos | projects.py, procedures.py, tracking.py | Objetivos, tareas, dependencias, decisiones, progreso |
| Acciones | actions.py | Catálogo cerrado, simulación, ticket, confirmación, versiones, políticas |
| Auditoría | audit.py | Eventos encadenados, confirmación atómica con evento de éxito, recuperación compensatoria |

### Flujo de lectura
Adaptador autenticado → Principal → ConversationContext/ResponseComposer →
UnifiedIntentEngine → memoria de propietario/proyecto → respuesta textual.
El reconocimiento de intención **nunca ejecuta acciones**.

### Flujo de modificación
Adaptador autenticado → autorización de proyecto →
AuditedActions(strict_policies=True) → preview → mostrar detalles al usuario →
confirmación explícita → ControlledActions.confirm → actualización y evento
de auditoría en una transacción SQLite.

### Alcance real
- Los proyectos de conversación se identifican por nombre; los proyectos
  registrados y sus tareas se identifican por UUID. El adaptador futuro
  debe resolver esa relación de forma explícita y sin suposiciones.
- Los módulos de memoria y proyectos comparten SQLite si reciben la misma ruta.
- La identidad Principal no se autentica en el núcleo; el adaptador debe
  validarla antes de construirla.
- La fachada AuditedActions no impide que otro código importe ControlledActions.
- La auditoría no cubre todas las mutaciones de los demás módulos.
- Los tests actuales usan bases temporales; no verifican migraciones reales
  de usuarios Android ni integraciones de voz.

## Guía de ejecución
Desde la raíz: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
El workflow `.github/workflows/core-tests.yml` valida sintaxis y regresión
en Python 3.12 cuando cambia `core/**` en la rama de desarrollo.

## Restricciones de publicación
No modificar `app/`, `server/`, `main`, APK ni Railway sin autorización
explícita. La integración debe realizarse en una fase posterior, con
revisión de seguridad, pruebas Android y aprobación humana.
