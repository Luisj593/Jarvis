# Actividad 16 — Pruebas integrales

Escenarios automatizados: flujo completo proyecto → procedimiento → tareas
dependientes → reporte → decisión → simulación de acción de riesgo alto →
confirmación → auditoría; aislamiento entre propietarios; aislamiento de
conversación; revocación de permisos; cambios concurrentes; conflictos de
versión; recuperación compensatoria y detección de alteración de auditoría.

Ejecutar: `PYTHONPATH=core python -m unittest discover -s core/tests -v`.
La regresión se ejecuta en GitHub Actions para la rama de desarrollo.

**Límites:** las pruebas usan SQLite temporal y no validan autenticación
real, integración Android, voz, despliegues, red, cifrado ni servicios
externos. La auditoría de actividad 15 no es atómica con la acción;
la detección de integridad no es a prueba de administradores maliciosos.
El resultado verde no certifica preparación para producción.

No se modifica APK, `main` ni Railway.
