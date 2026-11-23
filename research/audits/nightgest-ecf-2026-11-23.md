# JARVIS — Auditoría inicial de facturación electrónica NightGest
Fecha: 2026-11-23
Proyecto examinado: NightGest-ERP-Testing (Railway)
Alcance: lectura del código desplegado de cuatro funciones Bun; sin acceso al código de otros componentes o a pruebas transaccionales.
No se modificó NightGest.

## Veredicto
El módulo e-CF observado es mayormente una interfaz de demostración. No se halló un motor de emisión real en los cuatro servicios examinados. No se puede concluir que el sistema completo carezca de toda funcionalidad no accesible; sí que los servicios inspeccionados la señalan como pendiente o simulada.

## Evidencia por servicio
- nightgest-web-demo: interfaz «Fiscal (simulación)», declara expresamente que no firma, numera ni envía e-CF. Guarda datos del piloto en el navegador. Muestra aviso «SIN FACTURACIÓN REAL».
- nightgest-shared-pos-test: admite solicitud de comprobante fiscal, nombre y RNC/cédula del cliente; sus recibos llevan «Sin valor fiscal», «SIM-» y «e-CF pendiente de integración DGII. NO EMITIDO.»
- nightgest-pos-commercial: facturas de prueba almacenadas en navegador, sin valor fiscal; el código dice que no genera e-CF.
- nightgest-auth-testing: menú «DGII / e-CF» y submenús de comprobantes, estados DGII, reportes. La pantalla del módulo informa «Motor fiscal e-CF pendiente de integración y certificación», estado «No operativo».

## Matriz de evaluación
1. Menús y navegación: evidencia de existencia; funcionalidad fiscal no demostrada.
2. Solicitud de factura y datos fiscales del cliente: existe en flujo POS de pruebas; validar persistencia y reglas.
3. Numeración e-NCF y control de secuencias: no identificado.
4. Construcción XML e-CF: no identificada.
5. Validación con XSD DGII: no identificada.
6. Firma digital de e-CF: no identificada.
7. Envío a DGII: no identificado.
8. Acuse y estados de DGII: menús presentes, lógica real no identificada.
9. Notas de crédito/débito electrónicas: menús de notas de crédito presentes; flujo real no identificado.
10. Contingencia y reintentos: no identificados.
11. Persistencia y trazabilidad fiscal: no demostrada en servicios revisados.
12. Impuestos, ITBIS y conciliación de importes: requieren pruebas con casos de uso y evidencia de código adicional.

## Prioridad de trabajo recomendada
P0. Documentar arquitectura, inventario de endpoints, esquema de datos y estado real de cada función; separar simulación de producción.
P1. Diseñar entidades fiscales: empresa/RNC, cliente, impuestos, tipo e-CF, secuencia, estados, XML, firma, respuesta y bitácora.
P2. Implementar XML y validación XSD según versión DGII aplicable, con pruebas automatizadas.
P3. Implementar firma, transporte, idempotencia, consulta de estado, reintentos y contingencia según documentación vigente.
P4. Integrar al ciclo POS: cierre de mesa, división de cuentas, devoluciones, nota de crédito, impresión y reportes.
P5. Ejecutar pruebas funcionales y de seguridad en entorno de pruebas antes de considerar producción.

## Referencias oficiales
- https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Paginas/documentacionSobreE-CF.aspx
- https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/Paginas/TipoyEstructurae-CF.aspx

Esta auditoría es diagnóstica y de solo lectura; no constituye certificación DGII ni autorización para emitir.
