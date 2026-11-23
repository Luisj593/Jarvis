# Seguridad, privacidad, recuperación y operación — manual de desarrollo

## Principios
- Mínimo privilegio: permisos `memory:read`, `memory:write`,
  `memory:delete` y `action:execute` según operación.
- Aislamiento lógico: consultas SQLite filtradas por `owner_id` y, cuando
  corresponda, proyecto. No sustituye separación física ni autenticación.
- Acciones cerradas: únicamente `project.set_status` en el catálogo actual.
  No se autorizan shell, red, GitHub, Railway ni despliegues.
- Confirmación de un solo uso y expiración aproximada de diez minutos.
- Para adaptadores nuevos, usar `strict_policies=True` y configurar
  autorizaciones explícitas; el valor predeterminado legacy es permisivo
  si el Principal tiene permisos globales.
- No colocar tickets, contraseñas, secretos, datos biométricos ni transcripciones
  sensibles en registros.

## Operación segura
1. Mantener base de datos en almacenamiento privado y cifrado del sistema.
2. Autenticar identidad y conceder permisos desde una fuente confiable.
3. Validar autorización de proyecto y mostrar simulación antes de confirmar.
4. Ejecutar mediante `AuditedActions` y comprobar `verify_integrity()`.
5. Si una acción falla, consultar el estado real antes de reintentar.
6. Para recuperar, utilizar `recovery_preview` y nueva confirmación.
7. Guardar respaldos cifrados y probar restauración fuera de producción.

## Respuesta ante incidentes
Revocar política del proyecto; detener nuevas confirmaciones; preservar
copia de base y registros; verificar cadena de auditoría; investigar
versiones, propietarios y acciones; restaurar solo tras revisión.
La revocación invalida tickets existentes al cambiar la versión de política.

## Riesgos residuales no resueltos
- SQLite no está cifrado por el núcleo; `chmod 0600` no cifra.
- `Principal` no acredita identidad; un adaptador inseguro puede falsificarla.
- El acceso directo a `ControlledActions` puede omitir la auditoría.
- La auditoría de éxito de `AuditedActions.confirm` es atómica, pero
  simulaciones, políticas y rechazos se registran en transacciones separadas.
- La cadena SHA-256 no es una firma ni registro externo inmutable.
- No se ha hecho pentest, auditoría independiente ni pruebas de Android.
- La retención y borrado seguro de datos deben definirse antes de producción.

## Regla de cierre
Suite verde = núcleo probado en CI, **no** certificación de seguridad,
autonomía total ni autorización para desplegar.
