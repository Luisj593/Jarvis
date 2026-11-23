# Actividad 3 — Diseño de datos, privacidad y permisos

## Modelo de datos
Tabla `lessons`: id UUID, owner_id, project, content, category, created_at, updated_at.
Índice `(owner_id, project)`. Toda lectura, edición y eliminación usa **ambos**
atributos como filtro obligatorio. El núcleo no accede a otras bases de datos.

## Límites de seguridad
- `owner_id` **no se autentica** por sí solo: lo debe proporcionar un adaptador
  que haya autenticado previamente al usuario. No aceptar identidades directamente
  de un parámetro público de API.
- `Principal` define permisos; los adaptadores deberán llamar
  `require_permission` antes de realizar operaciones protegidas. La clase
  `SQLiteMemoryStore` por sí sola **no aplica permisos**: su límite es el aislamiento
  por propietario y proyecto.
- El archivo SQLite se configura con permisos 0600 en sistemas POSIX. Esto **no es
  cifrado**; no almacenar contraseñas, tokens, documentos de identidad ni secretos.
- El directorio padre debe estar restringido por el administrador del entorno.
- No se ha implementado exportación, respaldo cifrado, retención, migraciones
  versionadas, historial de modificaciones ni borrado criptográfico.
- Los datos de esta etapa son de prueba; no conectar a Railway ni a la APK.
- Los proyectos se tratan como identificadores de alcance, no como autorización
  para ejecutar tareas. Ninguna herramienta externa está habilitada.

## Contrato
`SQLiteMemoryStore(path, owner_id)` expone `add(project, content)`,
`list(project)`, `update(project, lesson_id, content)` y
`delete(project, lesson_id)`. Devuelve `Lesson` o booleano para operaciones
de cambio. Errores de validación lanzan `ValueError`.

## Pruebas
```bash
PYTHONPATH=core python -m unittest discover -s core/tests -v
```

## Criterios de aceptación
Persistencia después de reiniciar instancias, aislamiento por propietario y proyecto,
operaciones de edición/borrado acotadas, SQL parametrizado, límites de tamaño y
denegación de permisos de la política. Estas pruebas no sustituyen una auditoría de
seguridad ni pruebas de concurrencia/carga.
