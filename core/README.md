# JARVIS Core — Actividad 2

Núcleo Python 3.12 puro, sin modelos de IA, red, proveedores externos ni acceso a proyectos.

## Arquitectura
- `contracts.py`: solicitudes y respuestas inmutables.
- `intent.py`: normalización y clasificación determinista.
- `memory.py`: interfaz MemoryStore e implementación temporal InMemoryStore.
- `engine.py`: orquestador sin dependencias de Android ni Railway.
- `tests/`: pruebas unitarias.

Flujo: adaptador futuro -> Request -> clasificador -> motor -> MemoryStore -> Response -> adaptador.

## Ejecución local
Desde la raíz del repositorio:
```bash
PYTHONPATH=core python -m unittest discover -s core/tests -v
```

## Contratos y límites
Request(text, project, session_id) -> Response(text, intent, memory_ids, requires_confirmation).
Se aprende exclusivamente con órdenes explícitas. Las memorias se aíslan por proyecto. No hay ejecución de acciones, persistencia, sincronización, autenticación ni conversaciones abiertas en esta fase. `session_id` se reserva para la fase de contexto. Las consultas no reconocidas se rechazan de manera segura.

## Criterios de aceptación
1. Importar el núcleo sin Android, Railway ni bibliotecas de terceros.
2. Registrar y consultar una enseñanza explícita.
3. Aislar las enseñanzas por proyecto.
4. No aprender de mensajes casuales.
5. Rechazar entradas inválidas y no ejecutar acciones externas.
6. Ejecutar pruebas unitarias en Python 3.12.

## Política de despliegue
Esta rama no modifica `app/`, `server/` ni workflows. No fusionar con `main` ni desplegar sin autorización.
