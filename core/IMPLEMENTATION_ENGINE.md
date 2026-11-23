# Motor de implementaciones JARVIS — versión inicial

Objetivo: administrar solicitudes de implementación con seguimiento hasta
una entrega verificable, evitando cierres falsos.

Etapas: analysis → plan → implementation → tests → verification → delivery.
Cada transición exige evidencia textual, conserva el historial y aplica hasta
3 intentos por defecto. Los fallos se mantienen en su etapa y bloquean
cuando se agota el límite. Los cambios en main, despliegues a producción,
migraciones, secretos y acciones destructivas bloquean la ejecución para
obtener autorización específica.

API autenticada (desarrollo):
- POST /v1/core/implementation/create: {project_id,request}
- GET /v1/core/implementation/runs
- POST /v1/core/implementation/advance:
  {run_id,stage,evidence,passed,gate}; gate debe ser null si no aplica.

**Límites actuales:** es un motor de control y registro, no un agente que
modifique código por sí mismo. El campo passed es una declaración del cliente,
no una comprobación automática. No se debe usar como prueba independiente.
Para autonomía real faltan un trabajador persistente, integraciones de
lectura y escritura acotadas por repositorio, sandbox para ejecutar tests,
verificación de artefactos/CI, recuperación tras reinicio y aprobación
verificable del propietario. Ninguna acción externa se ejecuta aquí.

Seguridad: las credenciales de proveedores no se exponen en la APK; un
trabajador futuro debe tener permisos mínimos, entornos aislados y no debe
poder eludir aprobaciones por el campo gate del cliente.
