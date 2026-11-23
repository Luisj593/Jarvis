"""Registro local de proyectos con permisos y control de versiones."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .security import Principal, require_permission
from .storage import SQLiteMemoryStore

STATES=frozenset({"planned","active","paused","completed","archived"})
PRIORITIES=frozenset({"low","medium","high","critical"})

class ProjectConflict(Exception):
    pass

@dataclass(frozen=True)
class Project:
    id: str
    name: str
    objective: str
    priority: str
    status: str
    version: int
    created_at: str
    updated_at: str

class ProjectRegistry:
    def __init__(self,path: str | Path,principal: Principal):
        self.principal=principal
        self.store=SQLiteMemoryStore(path,principal.owner_id)
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS registered_projects(
                id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,name TEXT NOT NULL,
                objective TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_id,name),
                CHECK(version>0)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS registered_projects_owner ON registered_projects(owner_id,status)")

    @staticmethod
    def _name(name):
        if not isinstance(name,str) or not name.strip() or len(name)>100:
            raise ValueError("nombre inválido")
        return name.strip()

    @staticmethod
    def _objective(objective):
        if not isinstance(objective,str) or not objective.strip() or len(objective)>3000:
            raise ValueError("objetivo inválido")
        return objective.strip()

    @staticmethod
    def _choice(value,allowed,field):
        if value not in allowed:
            raise ValueError(field+" inválido")
        return value

    @staticmethod
    def _record(row):
        return Project(*row)

    def _get(self,db,project_id):
        return db.execute("""SELECT id,name,objective,priority,status,version,created_at,updated_at
            FROM registered_projects WHERE id=? AND owner_id=?""",
            (project_id,self.principal.owner_id)).fetchone()

    def create(self,name,objective,priority="medium",status="planned"):
        require_permission(self.principal,"memory:write")
        name=self._name(name)
        objective=self._objective(objective)
        self._choice(priority,PRIORITIES,"prioridad")
        self._choice(status,STATES,"estado")
        project_id=str(uuid4())
        with self.store._connect() as db:
            db.execute("INSERT INTO registered_projects(id,owner_id,name,objective,priority,status) VALUES(?,?,?,?,?,?)",
                       (project_id,self.principal.owner_id,name,objective,priority,status))
            return self._record(self._get(db,project_id))

    def get(self,project_id):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            row=self._get(db,project_id)
        return self._record(row) if row else None

    def list(self,status=None):
        require_permission(self.principal,"memory:read")
        if status is not None:
            self._choice(status,STATES,"estado")
        with self.store._connect() as db:
            rows=db.execute("""SELECT id,name,objective,priority,status,version,created_at,updated_at
                FROM registered_projects WHERE owner_id=? AND (? IS NULL OR status=?)
                ORDER BY name,id""",(self.principal.owner_id,status,status)).fetchall()
        return [self._record(row) for row in rows]

    def update(self,project_id,expected_version,*,name=None,objective=None,priority=None,status=None):
        require_permission(self.principal,"memory:write")
        if type(expected_version) is not int or expected_version<1:
            raise ValueError("versión inválida")
        changes={}
        if name is not None: changes["name"]=self._name(name)
        if objective is not None: changes["objective"]=self._objective(objective)
        if priority is not None: changes["priority"]=self._choice(priority,PRIORITIES,"prioridad")
        if status is not None: changes["status"]=self._choice(status,STATES,"estado")
        if not changes:
            raise ValueError("no hay modificaciones")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self._get(db,project_id)
            if row is None:
                raise KeyError("proyecto no encontrado")
            if row[5]!=expected_version:
                raise ProjectConflict("versión desactualizada")
            assignments=", ".join(field+"=?" for field in changes)
            db.execute("UPDATE registered_projects SET "+assignments+
                       ",version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=?",
                       (*changes.values(),project_id,self.principal.owner_id))
            return self._record(self._get(db,project_id))

    def delete(self,project_id,expected_version,confirmation):
        """Borrado controlado del registro, no de memorias asociadas."""
        require_permission(self.principal,"memory:delete")
        if confirmation!="ELIMINAR PROYECTO":
            raise PermissionError("confirmación requerida")
        if type(expected_version) is not int or expected_version<1:
            raise ValueError("versión inválida")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self._get(db,project_id)
            if row is None:
                return False
            if row[5]!=expected_version:
                raise ProjectConflict("versión desactualizada")
            db.execute("DELETE FROM registered_projects WHERE id=? AND owner_id=?",
                       (project_id,self.principal.owner_id))
        return True
