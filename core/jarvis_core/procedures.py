"""Procedimientos y tareas con dependencias, versiones y aislamiento por propietario."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .projects import ProjectRegistry
from .security import Principal, require_permission

STATES = frozenset({"pending", "in_progress", "blocked", "done", "cancelled"})

class TaskConflict(Exception):
    """Una versión de tarea o procedimiento quedó desactualizada."""

class DependencyBlocked(Exception):
    """No se puede completar una tarea con dependencias pendientes."""

@dataclass(frozen=True)
class Procedure:
    id: str
    project_id: str
    title: str
    version: int
    created_at: str

@dataclass(frozen=True)
class Task:
    id: str
    procedure_id: str
    project_id: str
    title: str
    assignee: str | None
    status: str
    position: int
    version: int
    depends_on: tuple[str, ...]

@dataclass(frozen=True)
class Progress:
    total: int
    done: int
    percent: float

class ProcedureRegistry:
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.projects = ProjectRegistry(path, principal)
        self.store = self.projects.store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS procedures(
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, project_id TEXT NOT NULL,
                title TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS procedure_tasks(
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, project_id TEXT NOT NULL,
                procedure_id TEXT NOT NULL, title TEXT NOT NULL, assignee TEXT,
                status TEXT NOT NULL DEFAULT 'pending', position INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                UNIQUE(owner_id,procedure_id,position))""")
            db.execute("""CREATE TABLE IF NOT EXISTS task_dependencies(
                owner_id TEXT NOT NULL, project_id TEXT NOT NULL,
                task_id TEXT NOT NULL, prerequisite_id TEXT NOT NULL,
                PRIMARY KEY(owner_id,task_id,prerequisite_id),
                CHECK(task_id <> prerequisite_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS task_scope_idx ON procedure_tasks(owner_id,project_id,procedure_id)")

    @staticmethod
    def _text(value: str, field: str, limit: int = 300) -> str:
        if not isinstance(value, str) or not value.strip() or len(value)>limit:
            raise ValueError(field+" inválido")
        return value.strip()

    @staticmethod
    def _version(value: int):
        if type(value) is not int or value<1:
            raise ValueError("versión inválida")

    def _project(self, db, project_id):
        row=db.execute("SELECT id FROM registered_projects WHERE id=? AND owner_id=?",
                       (project_id,self.principal.owner_id)).fetchone()
        if not row:
            raise KeyError("proyecto inexistente o sin acceso")

    def _procedure(self, db, project_id, procedure_id):
        row=db.execute("""SELECT id,project_id,title,version,created_at FROM procedures
            WHERE id=? AND project_id=? AND owner_id=?""",
            (procedure_id,project_id,self.principal.owner_id)).fetchone()
        if not row:
            raise KeyError("procedimiento inexistente o sin acceso")
        return Procedure(*row)

    def _task(self, db, project_id, procedure_id, task_id):
        row=db.execute("""SELECT id,procedure_id,project_id,title,assignee,status,position,version
            FROM procedure_tasks WHERE id=? AND procedure_id=? AND project_id=? AND owner_id=?""",
            (task_id,procedure_id,project_id,self.principal.owner_id)).fetchone()
        if not row:
            raise KeyError("tarea inexistente o sin acceso")
        deps=db.execute("""SELECT prerequisite_id FROM task_dependencies
            WHERE owner_id=? AND project_id=? AND task_id=? ORDER BY prerequisite_id""",
            (self.principal.owner_id,project_id,task_id)).fetchall()
        return Task(*row,tuple(x[0] for x in deps))

    def create_procedure(self, project_id, title):
        require_permission(self.principal,"memory:write")
        title=self._text(title,"título")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._project(db,project_id)
            identifier=str(uuid4())
            db.execute("INSERT INTO procedures(id,owner_id,project_id,title) VALUES(?,?,?,?)",
                       (identifier,self.principal.owner_id,project_id,title))
            return self._procedure(db,project_id,identifier)

    def get_procedure(self, project_id, procedure_id):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            self._project(db,project_id)
            return self._procedure(db,project_id,procedure_id)

    def list_procedures(self, project_id):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            self._project(db,project_id)
            rows=db.execute("""SELECT id,project_id,title,version,created_at FROM procedures
                WHERE owner_id=? AND project_id=? ORDER BY created_at,id""",
                (self.principal.owner_id,project_id)).fetchall()
        return [Procedure(*r) for r in rows]

    def add_task(self, project_id, procedure_id, title, assignee=None, depends_on=(), expected_version=None):
        require_permission(self.principal,"memory:write")
        title=self._text(title,"tarea")
        if assignee is not None:
            assignee=self._text(assignee,"responsable",120)
        if not isinstance(depends_on,(list,tuple)) or len(depends_on)>100 or len(set(depends_on))!=len(depends_on):
            raise ValueError("dependencias inválidas")
        if expected_version is not None:
            self._version(expected_version)
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._project(db,project_id)
            procedure=self._procedure(db,project_id,procedure_id)
            if expected_version is not None and procedure.version!=expected_version:
                raise TaskConflict("versión de procedimiento desactualizada")
            for dep in depends_on:
                self._task(db,project_id,procedure_id,dep)
            position=db.execute("""SELECT COALESCE(MAX(position),0)+1 FROM procedure_tasks
                WHERE owner_id=? AND project_id=? AND procedure_id=?""",
                (self.principal.owner_id,project_id,procedure_id)).fetchone()[0]
            identifier=str(uuid4())
            db.execute("""INSERT INTO procedure_tasks(id,owner_id,project_id,procedure_id,title,assignee,position)
                VALUES(?,?,?,?,?,?,?)""",(identifier,self.principal.owner_id,project_id,procedure_id,title,assignee,position))
            for dep in depends_on:
                db.execute("""INSERT INTO task_dependencies(owner_id,project_id,task_id,prerequisite_id)
                    VALUES(?,?,?,?)""",(self.principal.owner_id,project_id,identifier,dep))
            db.execute("UPDATE procedures SET version=version+1 WHERE id=? AND owner_id=?",
                       (procedure_id,self.principal.owner_id))
            return self._task(db,project_id,procedure_id,identifier)

    def list_tasks(self, project_id, procedure_id):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            self._project(db,project_id)
            self._procedure(db,project_id,procedure_id)
            rows=db.execute("""SELECT id FROM procedure_tasks WHERE owner_id=? AND project_id=?
                AND procedure_id=? ORDER BY position""",
                (self.principal.owner_id,project_id,procedure_id)).fetchall()
            return [self._task(db,project_id,procedure_id,r[0]) for r in rows]

    def update_task(self, project_id, procedure_id, task_id, expected_version, *,
                    title=None, assignee=None, status=None):
        require_permission(self.principal,"memory:write")
        self._version(expected_version)
        changes={}
        if title is not None: changes["title"]=self._text(title,"tarea")
        if assignee is not None: changes["assignee"]=self._text(assignee,"responsable",120)
        if status is not None:
            if status not in STATES: raise ValueError("estado inválido")
            changes["status"]=status
        if not changes: raise ValueError("sin cambios")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._project(db,project_id)
            self._procedure(db,project_id,procedure_id)
            current=self._task(db,project_id,procedure_id,task_id)
            if current.version!=expected_version:
                raise TaskConflict("versión de tarea desactualizada")
            if status=="done":
                for dep in current.depends_on:
                    prerequisite=self._task(db,project_id,procedure_id,dep)
                    if prerequisite.status!="done":
                        raise DependencyBlocked("dependencia pendiente: "+dep)
            if status in ("pending","in_progress","blocked","cancelled") and current.status=="done":
                # No deshacer tareas completadas de las que dependen otras ya completadas.
                dependent=db.execute("""SELECT 1 FROM task_dependencies d
                    JOIN procedure_tasks t ON t.id=d.task_id AND t.owner_id=d.owner_id
                    WHERE d.owner_id=? AND d.project_id=? AND d.prerequisite_id=?
                    AND t.status='done' LIMIT 1""",
                    (self.principal.owner_id,project_id,task_id)).fetchone()
                if dependent: raise DependencyBlocked("existen tareas completadas dependientes")
            assignments=", ".join(k+"=?" for k in changes)
            db.execute("UPDATE procedure_tasks SET "+assignments+
                       ",version=version+1 WHERE id=? AND owner_id=? AND project_id=? AND procedure_id=?",
                       (*changes.values(),task_id,self.principal.owner_id,project_id,procedure_id))
            return self._task(db,project_id,procedure_id,task_id)

    def progress(self, project_id, procedure_id):
        require_permission(self.principal,"memory:read")
        tasks=self.list_tasks(project_id,procedure_id)
        done=sum(t.status=="done" for t in tasks)
        return Progress(len(tasks),done,round(done*100/len(tasks),2) if tasks else 0.0)
