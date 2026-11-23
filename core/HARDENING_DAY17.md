# Actividad 17 — Endurecimiento y rendimiento

## Correcciones
- `ControlledActions(..., strict_policies=True)` activa **denegación por defecto**:
  sin política explícita el proyecto no permite acciones. Para no romper
  los consumidores anteriores, `strict_policies=False` sigue siendo el
  valor predeterminado; un adaptador nuevo debe activar el modo estricto.
- `AuditedActions(..., strict_policies=True)` ofrece el mismo modo.
- La confirmación exitosa a través de `AuditedActions` ahora registra
  acción y evento en **la misma transacción**. Si el INSERT del evento
  falla, se revierte también el cambio de estado y consumo del ticket.
- Los rechazos se registran aparte porque la transacción fallida debe
  revertirse; si falla la escritura de rechazo, puede no conservarse
  evidencia de ese intento.
- El registro no almacena tickets ni frases de confirmación.

## Privacidad e integridad
- Archivo SQLite creado con permisos 0600 en sistemas compatibles.
- La cadena SHA-256 detecta alteraciones simples, no ofrece protección
  criptográfica contra un administrador que reescriba toda la cadena.
- El cifrado en reposo **no está implementado**; se requiere almacenamiento
  cifrado del sistema operativo o una solución criptográfica revisada.
- El acceso directo a `ControlledActions` sigue siendo posible y evita
  la fachada de auditoría. No declarar cumplimiento ni seguridad total.
- `Principal` necesita autenticación real en la futura integración Android.

## Rendimiento
Se añade una prueba de humo con 40 simulaciones y umbral amplio de
15 segundos en CI. No es un benchmark de carga ni una garantía de
latencia en Android.

## Ejecución
`PYTHONPATH=core python -m unittest discover -s core/tests -v`.
Solo se modifica la rama de desarrollo, nunca APK, main o Railway.
