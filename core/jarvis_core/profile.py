"""Memoria estructurada explícita: personal, preferencias y proyectos.

No hay extracción automática de datos personales ni aprendizaje implícito.
El identificador del propietario debe proceder de un adaptador autenticado.
"""
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
import sqlite3
from .storage import SQLiteMemoryStore

CATEGORIES = frozenset({"personal", "preference", "project"})
GLOBAL_SCOPE = "__personal__"

@dataclass(frozen=True)
class MemoryEntry:
    id: str
    category: str
    project: str | None
    key: str
    value: str
    created_at: str
    updated_at: str

class ProfileMemory:
    def __init__(self, path: str | Path, owner_id: str):
        # Reutiliza validación del propietario y permisos del archivo.
        self._store = SQLiteMemoryStore(path, owner_id)
        self.owner_id = self._store.owner_id
        with self._store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profile_memories(
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('personal','preference','project')),
                project TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_id,category,project,key)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS profile_scope_idx ON profile_memories(owner_id,category,project)")

    @staticmethod
    def _scope(category: str, project: str | None) -> str:
        if category not in CATEGORIES:
            raise ValueError("categoría inválida")
        if category == "project":
            if not isinstance(project, str) or not project.strip() or len(project) > 100 or project.strip() == GLOBAL_SCOPE:
                raise ValueError("proyecto inválido")
            return project.strip()
        if project is not None:
            raise ValueError("la memoria personal y preferencias no aceptan proyecto")
        return GLOBAL_SCOPE

    @staticmethod
    def _validate(key: str, value: str):
        if not isinstance(key, str) or not key.strip() or len(key) > 120:
            raise ValueError("clave inválida")
        if not isinstance(value, str) or not value.strip() or len(value) > 3000:
            raise ValueError("valor inválido")

    @staticmethod
    def _entry(row):
        return MemoryEntry(row[0],row[1],None if row[2]==GLOBAL_SCOPE else row[2],row[3],row[4],row[5],row[6])

    def put(self, category: str, key: str, value: str, project: str | None = None) -> MemoryEntry:
        scope = self._scope(category, project)
        self._validate(key,value)
        key,value=key.strip(),value.strip()
        with self._store._connect() as db:
            found=db.execute("SELECT id FROM profile_memories WHERE owner_id=? AND category=? AND project=? AND key=?",
                             (self.owner_id,category,scope,key)).fetchone()
            if found:
                db.execute("UPDATE profile_memories SET value=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=?",
                           (value,found[0],self.owner_id))
                item_id=found[0]
            else:
                item_id=str(uuid4())
                db.execute("INSERT INTO profile_memories(id,owner_id,category,project,key,value) VALUES(?,?,?,?,?,?)",
                           (item_id,self.owner_id,category,scope,key,value))
            row=db.execute("SELECT id,category,project,key,value,created_at,updated_at FROM profile_memories WHERE id=? AND owner_id=?",
                           (item_id,self.owner_id)).fetchone()
        return self._entry(row)

    def list(self, category: str, project: str | None = None) -> list[MemoryEntry]:
        scope=self._scope(category,project)
        with self._store._connect() as db:
            rows=db.execute("SELECT id,category,project,key,value,created_at,updated_at FROM profile_memories WHERE owner_id=? AND category=? AND project=? ORDER BY key",
                            (self.owner_id,category,scope)).fetchall()
        return [self._entry(row) for row in rows]

    def get(self, category: str, key: str, project: str | None = None) -> MemoryEntry | None:
        scope=self._scope(category,project)
        if not isinstance(key,str) or not key.strip():
            raise ValueError("clave inválida")
        with self._store._connect() as db:
            row=db.execute("SELECT id,category,project,key,value,created_at,updated_at FROM profile_memories WHERE owner_id=? AND category=? AND project=? AND key=?",
                           (self.owner_id,category,scope,key.strip())).fetchone()
        return self._entry(row) if row else None

    def delete(self, category: str, key: str, project: str | None = None) -> bool:
        scope=self._scope(category,project)
        if not isinstance(key,str) or not key.strip():
            raise ValueError("clave inválida")
        with self._store._connect() as db:
            result=db.execute("DELETE FROM profile_memories WHERE owner_id=? AND category=? AND project=? AND key=?",
                              (self.owner_id,category,scope,key.strip()))
        return result.rowcount==1

    def context(self, project: str | None = None, include_personal: bool = False) -> list[MemoryEntry]:
        """Recuperación explícita: preferencias generales y proyecto seleccionado.
        Los datos personales se excluyen por defecto.
        """
        entries=self.list("preference")
        if include_personal:
            entries+=self.list("personal")
        if project is not None:
            entries+=self.list("project",project)
        return entries
