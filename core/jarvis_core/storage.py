"""Persistencia SQLite local con aislamiento de propietarios y proyectos.

La seguridad depende de que el adaptador autentique al propietario. SQLite NO cifra
los datos; el archivo debe permanecer en un directorio privado y protegido.
"""
import os
import sqlite3
from pathlib import Path
from uuid import uuid4
from .memory import Lesson

class SQLiteMemoryStore:
    def __init__(self, path: str | Path, owner_id: str):
        if not isinstance(owner_id, str) or not owner_id.strip() or len(owner_id) > 128:
            raise ValueError("owner_id inválido")
        self.owner_id = owner_id
        self.path = str(path)
        if self.path != ":memory:":
            location = Path(self.path)
            location.parent.mkdir(parents=True, exist_ok=True)
            if location.is_symlink():
                raise ValueError("no se permiten rutas simbólicas")
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'teaching',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (length(content) BETWEEN 1 AND 3000)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS lessons_scope_idx ON lessons(owner_id,project)")
        if self.path != ":memory:":
            os.chmod(self.path, 0o600)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA busy_timeout=5000")
        return db

    @staticmethod
    def _validate(project: str, content: str | None = None):
        if not isinstance(project, str) or not project.strip() or len(project) > 100:
            raise ValueError("proyecto inválido")
        if content is not None and (not isinstance(content, str) or not content.strip() or len(content) > 3000):
            raise ValueError("contenido inválido")

    def add(self, project: str, content: str) -> Lesson:
        self._validate(project, content)
        project, content = project.strip(), content.strip()
        item = Lesson(str(uuid4()), project, content)
        with self._connect() as db:
            db.execute("INSERT INTO lessons(id,owner_id,project,content) VALUES(?,?,?,?)",
                       (item.id, self.owner_id, project, content))
        return item

    def list(self, project: str) -> list[Lesson]:
        self._validate(project)
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,project,content FROM lessons WHERE owner_id=? AND project=? ORDER BY created_at,id",
                (self.owner_id, project.strip())).fetchall()
        return [Lesson(*row) for row in rows]

    def update(self, project: str, lesson_id: str, content: str) -> bool:
        self._validate(project, content)
        with self._connect() as db:
            result = db.execute(
                "UPDATE lessons SET content=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=? AND project=?",
                (content.strip(), lesson_id, self.owner_id, project.strip()))
        return result.rowcount == 1

    def delete(self, project: str, lesson_id: str) -> bool:
        self._validate(project)
        with self._connect() as db:
            result = db.execute("DELETE FROM lessons WHERE id=? AND owner_id=? AND project=?",
                                (lesson_id, self.owner_id, project.strip()))
        return result.rowcount == 1
