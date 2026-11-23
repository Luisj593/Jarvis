"""Seguimiento consolidado y decisiones versionadas; lectura sin acciones externas."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .projects import ProjectRegistry
from .procedures import ProcedureRegistry
from .security import Principal, require_permission

class DecisionConflict(Exception):
    pass

@dataclass(frozen=True)
class Blocker:
    task_id: str
    procedure_id: str
    title: str
    reason: str
    pending_dependencies: tuple[str, ...]

@dataclass(frozen=True)
class ProjectReport:
    project_id: str
    name: str
    status: str
    priority: str
    procedures: int
    tasks: int
    completed: int
    percent: float
    blockers: tuple[Blocker, ...]

@dataclass(frozen=True)
class Decision:
    id: str
    project_id: str
    title: str
    rationale: str
    outcome: str
    version: int
    created_at: str

class ProjectTracking:
    def __init__(self, path: str | Path, principal: Principal):
        self.principal=principal
        self.procedures=ProcedureRegistry(path,principal)
        self.projects=self.procedures.projects
        self.store=self.procedures.store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS project_decisions(
                id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,project_id TEXT NOT NULL,
                title TEXT NOT NULL,rationale TEXT NOT NULL,outcome TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS project_decision_history(
                decision_id TEXT NOT NULL,owner_id TEXT NOT NULL,project_id TEXT NOT NULL,
                version INTEGER NOT NULL,title TEXT NOT NULL,rationale TEXT NOT NULL,
                outcome TEXT NOT NULL,changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(decision_id,version))""")
            db.execute("CREATE INDEX IF NOT EXISTS decision_scope ON project_decisions(owner_id,project_id)")

    def report(self, project_id: str) -> ProjectReport:
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            db.execute("BEGIN")
            p=self.projects._get(db,project_id)
            if p is None: raise KeyError("proyecto inexistente o sin acceso")
            rows=db.execute("""SELECT t.id,t.procedure_id,t.title,t.status
                FROM procedure_tasks t JOIN procedures pr ON pr.id=t.procedure_id
                WHERE t.owner_id=? AND t.project_id=? AND pr.owner_id=? AND pr.project_id=?""",
                (self.principal.owner_id,project_id,self.principal.owner_id,project_id)).fetchall()
            proc_count=db.execute("""SELECT COUNT(*) FROM procedures WHERE owner_id=? AND project_id=?""",
                                  (self.principal.owner_id,project_id)).fetchone()[0]
            blockers=[]
            for task_id,procedure_id,title,status in rows:
                if status in ("done","cancelled"): continue
                pending=db.execute("""SELECT d.prerequisite_id FROM task_dependencies d
                    LEFT JOIN procedure_tasks pre ON pre.id=d.prerequisite_id
                    AND pre.owner_id=d.owner_id AND pre.project_id=d.project_id
                    AND pre.procedure_id=?
                    WHERE d.owner_id=? AND d.project_id=? AND d.task_id=?
                    AND (pre.id IS NULL OR pre.status!='done') ORDER BY d.prerequisite_id""",
                    (procedure_id,self.principal.owner_id,project_id,task_id)).fetchall()
                pending_ids=tuple(x[0] for x in pending)
                if status=="blocked" or pending_ids:
                    reason="explicitly_blocked" if status=="blocked" else "pending_dependencies"
                    blockers.append(Blocker(task_id,procedure_id,title,reason,pending_ids))
            total=len(rows)
            done=sum(row[3]=="done" for row in rows)
            return ProjectReport(project_id,p[1],p[4],p[3],proc_count,total,done,
                                 round(100*done/total,2) if total else 0.0,tuple(blockers))

    def reports(self) -> list[ProjectReport]:
        require_permission(self.principal,"memory:read")
        return [self.report(p.id) for p in self.projects.list()]

    @staticmethod
    def _fields(title,rationale,outcome):
        return (ProjectRegistry._objective(title),ProjectRegistry._objective(rationale),
                ProjectRegistry._objective(outcome))

    def _read(self,db,project_id,decision_id):
        return db.execute("""SELECT id,project_id,title,rationale,outcome,version,created_at
            FROM project_decisions WHERE owner_id=? AND project_id=? AND id=?""",
            (self.principal.owner_id,project_id,decision_id)).fetchone()

    def decide(self,project_id,title,rationale,outcome) -> Decision:
        require_permission(self.principal,"memory:write")
        title,rationale,outcome=self._fields(title,rationale,outcome)
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.procedures._project(db,project_id)
            identifier=str(uuid4())
            db.execute("""INSERT INTO project_decisions(id,owner_id,project_id,title,rationale,outcome)
                VALUES(?,?,?,?,?,?)""",(identifier,self.principal.owner_id,project_id,title,rationale,outcome))
            db.execute("""INSERT INTO project_decision_history
                (decision_id,owner_id,project_id,version,title,rationale,outcome)
                VALUES(?,?,?,?,?,?,?)""",(identifier,self.principal.owner_id,project_id,1,title,rationale,outcome))
            return Decision(*self._read(db,project_id,identifier))

    def revise(self,project_id,decision_id,expected_version,title,rationale,outcome) -> Decision:
        require_permission(self.principal,"memory:write")
        if type(expected_version) is not int or expected_version<1:
            raise ValueError("versión inválida")
        title,rationale,outcome=self._fields(title,rationale,outcome)
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.procedures._project(db,project_id)
            row=self._read(db,project_id,decision_id)
            if row is None: raise KeyError("decisión inexistente o sin acceso")
            if row[5]!=expected_version: raise DecisionConflict("versión desactualizada")
            version=expected_version+1
            db.execute("""UPDATE project_decisions SET title=?,rationale=?,outcome=?,version=?
                WHERE id=? AND owner_id=? AND project_id=?""",
                (title,rationale,outcome,version,decision_id,self.principal.owner_id,project_id))
            db.execute("""INSERT INTO project_decision_history
                (decision_id,owner_id,project_id,version,title,rationale,outcome)
                VALUES(?,?,?,?,?,?,?)""",(decision_id,self.principal.owner_id,project_id,version,title,rationale,outcome))
            return Decision(*self._read(db,project_id,decision_id))

    def decisions(self,project_id) -> list[Decision]:
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            self.procedures._project(db,project_id)
            rows=db.execute("""SELECT id,project_id,title,rationale,outcome,version,created_at
                FROM project_decisions WHERE owner_id=? AND project_id=? ORDER BY created_at,id""",
                (self.principal.owner_id,project_id)).fetchall()
            return [Decision(*row) for row in rows]

    def history(self,project_id,decision_id) -> list[Decision]:
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            self.procedures._project(db,project_id)
            current=self._read(db,project_id,decision_id)
            if current is None: raise KeyError("decisión inexistente o sin acceso")
            rows=db.execute("""SELECT decision_id,project_id,title,rationale,outcome,version,changed_at
                FROM project_decision_history WHERE owner_id=? AND project_id=? AND decision_id=?
                ORDER BY version""",(self.principal.owner_id,project_id,decision_id)).fetchall()
            return [Decision(*row) for row in rows]
