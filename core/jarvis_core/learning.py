"""Aprendizaje explícito versionado y reversible; sin IA ni acceso a red."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .profile import ProfileMemory
from .security import Principal, require_permission

@dataclass(frozen=True)
class Revision:
    memory_id: str
    version: int
    category: str
    project: str | None
    key: str
    value: str
    deleted: bool
    operation: str
    created_at: str

class VersionConflict(Exception):
    """La memoria cambió desde la última lectura."""

class VersionedLearning:
    """Fachada de operaciones explícitas; owner_id se deriva del Principal.

    El Principal debe haber sido autenticado previamente por un adaptador confiable.
    No migrar ni mezclar registros de ProfileMemory automáticamente.
    """
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.profile = ProfileMemory(path, principal.owner_id)
        self.store = self.profile._store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS learning_items(
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, category TEXT NOT NULL,
                project TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                version INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                UNIQUE(owner_id,category,project,key))""")
            db.execute("""CREATE TABLE IF NOT EXISTS learning_history(
                memory_id TEXT NOT NULL, owner_id TEXT NOT NULL, version INTEGER NOT NULL,
                category TEXT NOT NULL, project TEXT NOT NULL, key TEXT NOT NULL,
                value TEXT NOT NULL, deleted INTEGER NOT NULL, operation TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(memory_id,version))""")
            db.execute("CREATE INDEX IF NOT EXISTS learning_history_owner ON learning_history(owner_id,memory_id)")

    def _scope(self, category: str, key: str, project: str | None):
        scope=self.profile._scope(category,project)
        if not isinstance(key,str) or not key.strip() or len(key)>120:
            raise ValueError("clave inválida")
        return scope,key.strip()

    def _read(self, db, category, scope, key):
        return db.execute("SELECT id,value,version,deleted FROM learning_items WHERE owner_id=? AND category=? AND project=? AND key=?",
                          (self.principal.owner_id,category,scope,key)).fetchone()

    def _write(self, db, memory_id, category, scope, key, value, version, deleted, operation):
        db.execute("INSERT INTO learning_history(memory_id,owner_id,version,category,project,key,value,deleted,operation) VALUES(?,?,?,?,?,?,?,?,?)",
                   (memory_id,self.principal.owner_id,version,category,scope,key,value,int(deleted),operation))
        return Revision(memory_id,version,category,None if scope=="__personal__" else scope,key,value,deleted,operation,"")

    def teach(self, category: str, key: str, value: str, project: str | None = None) -> Revision:
        """Solo crea una enseñanza nueva. No sobrescribe ni revive registros."""
        require_permission(self.principal,"memory:write")
        scope,key=self._scope(category,key,project)
        self.profile._validate(key,value)
        value=value.strip()
        with self.store._connect() as db:
            if self._read(db,category,scope,key):
                raise ValueError("ya existe: utilice correct con la versión actual")
            memory_id=str(uuid4())
            db.execute("INSERT INTO learning_items(id,owner_id,category,project,key,value,version,deleted) VALUES(?,?,?,?,?,?,1,0)",
                       (memory_id,self.principal.owner_id,category,scope,key,value))
            return self._write(db,memory_id,category,scope,key,value,1,False,"teach")

    def current(self, category: str, key: str, project: str | None = None) -> Revision | None:
        require_permission(self.principal,"memory:read")
        scope,key=self._scope(category,key,project)
        with self.store._connect() as db:
            row=self._read(db,category,scope,key)
        if row is None or row[3]:
            return None
        return Revision(row[0],row[2],category,project,key,row[1],False,"current","")

    def history(self, category: str, key: str, project: str | None = None) -> list[Revision]:
        require_permission(self.principal,"memory:read")
        scope,key=self._scope(category,key,project)
        with self.store._connect() as db:
            rows=db.execute("""SELECT h.memory_id,h.version,h.value,h.deleted,h.operation,h.created_at
                FROM learning_history h JOIN learning_items i ON i.id=h.memory_id
                WHERE i.owner_id=? AND i.category=? AND i.project=? AND i.key=? AND h.owner_id=?
                ORDER BY h.version""",(self.principal.owner_id,category,scope,key,self.principal.owner_id)).fetchall()
        return [Revision(r[0],r[1],category,project,key,r[2],bool(r[3]),r[4],r[5]) for r in rows]

    def _transition(self, category, key, project, expected_version, operation, value=None, restore_version=None):
        permission="memory:delete" if operation in ("delete","purge") else "memory:write"
        require_permission(self.principal,permission)
        scope,key=self._scope(category,key,project)
        if type(expected_version) is not int or expected_version<1:
            raise ValueError("versión esperada inválida")
        if operation=="correct":
            self.profile._validate(key,value)
            value=value.strip()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self._read(db,category,scope,key)
            if not row:
                raise KeyError("enseñanza no encontrada")
            memory_id,old_value,version,deleted=row
            if version!=expected_version:
                raise VersionConflict("versión desactualizada")
            if operation=="correct" and deleted:
                raise ValueError("no se puede corregir una enseñanza eliminada")
            if operation=="delete":
                if deleted:
                    raise ValueError("ya eliminada")
                value=old_value
                next_deleted=True
            elif operation=="restore":
                if not deleted:
                    raise ValueError("solo se restauran enseñanzas eliminadas")
                if restore_version is None:
                    value=old_value
                else:
                    if type(restore_version) is not int or restore_version<1:
                        raise ValueError("versión a recuperar inválida")
                    old=db.execute("""SELECT value,deleted FROM learning_history
                        WHERE memory_id=? AND owner_id=? AND version=?""",
                        (memory_id,self.principal.owner_id,restore_version)).fetchone()
                    if old is None or old[1]:
                        raise ValueError("versión histórica inexistente o eliminada")
                    value=old[0]
                next_deleted=False
            elif operation=="revert":
                if deleted:
                    raise ValueError("primero restaure la enseñanza eliminada")
                if type(restore_version) is not int or restore_version<1:
                    raise ValueError("versión a recuperar inválida")
                old=db.execute("SELECT value,deleted FROM learning_history WHERE memory_id=? AND owner_id=? AND version=?",
                               (memory_id,self.principal.owner_id,restore_version)).fetchone()
                if old is None or old[1]:
                    raise ValueError("versión histórica inexistente o eliminada")
                value=old[0]
                next_deleted=False
            else:
                next_deleted=False
            new_version=version+1
            db.execute("UPDATE learning_items SET value=?,version=?,deleted=? WHERE id=? AND owner_id=?",
                       (value,new_version,int(next_deleted),memory_id,self.principal.owner_id))
            return self._write(db,memory_id,category,scope,key,value,new_version,next_deleted,operation)

    def correct(self, category, key, value, expected_version, project=None):
        return self._transition(category,key,project,expected_version,"correct",value=value)

    def delete(self, category, key, expected_version, project=None):
        return self._transition(category,key,project,expected_version,"delete")

    def restore(self, category, key, expected_version, project=None, from_version=None):
        return self._transition(category,key,project,expected_version,"restore",restore_version=from_version)

    def revert(self, category, key, expected_version, from_version, project=None):
        return self._transition(category,key,project,expected_version,"revert",restore_version=from_version)

    def purge(self, category, key, expected_version, confirmation: str, project=None) -> bool:
        """Elimina registro e historial de forma lógica en SQLite; no garantiza borrado forense."""
        require_permission(self.principal,"memory:delete")
        if confirmation!="ELIMINAR DEFINITIVAMENTE":
            raise PermissionError("confirmación explícita requerida")
        scope,key=self._scope(category,key,project)
        if type(expected_version) is not int or expected_version<1:
            raise ValueError("versión esperada inválida")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self._read(db,category,scope,key)
            if row is None:
                return False
            if row[2]!=expected_version:
                raise VersionConflict("versión desactualizada")
            if not row[3]:
                raise ValueError("primero debe eliminarse de forma reversible")
            db.execute("DELETE FROM learning_history WHERE memory_id=? AND owner_id=?",(row[0],self.principal.owner_id))
            db.execute("DELETE FROM learning_items WHERE id=? AND owner_id=?",(row[0],self.principal.owner_id))
        return True
