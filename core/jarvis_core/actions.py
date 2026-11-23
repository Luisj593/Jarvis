"""Catálogo cerrado de acciones internas con simulación y confirmación de un solo uso."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import uuid4
from .projects import ProjectRegistry, ProjectConflict, STATES
from .security import Principal, require_permission

ALLOWED = ("project.set_status",)

@dataclass(frozen=True)
class ActionPreview:
    ticket: str
    action: str
    project_id: str
    before: str
    after: str
    version: int
    expires_at: str
    executed: bool = False
    risk: str = "low"

@dataclass(frozen=True)
class ActionResult:
    action: str
    project_id: str
    before: str
    after: str
    version: int
    executed: bool = True

class ControlledActions:
    """No admite plugins, comandos arbitrarios, shell, red ni acciones externas."""
    def __init__(self, path, principal: Principal):
        self.principal=principal
        self.projects=ProjectRegistry(path,principal)
        self.store=self.projects.store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS action_tickets(
                id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,project_id TEXT NOT NULL,
                action TEXT NOT NULL,before_status TEXT NOT NULL,after_status TEXT NOT NULL,
                project_version INTEGER NOT NULL,secret_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,consumed INTEGER NOT NULL DEFAULT 0)""")
            db.execute("""CREATE TABLE IF NOT EXISTS project_action_policies(
                owner_id TEXT NOT NULL,project_id TEXT NOT NULL,
                allowed INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(owner_id,project_id))""")
            cols={row[1] for row in db.execute("PRAGMA table_info(action_tickets)")}
            if "policy_version" not in cols:
                db.execute("ALTER TABLE action_tickets ADD COLUMN policy_version INTEGER NOT NULL DEFAULT 0")
            if "risk" not in cols:
                db.execute("ALTER TABLE action_tickets ADD COLUMN risk TEXT NOT NULL DEFAULT 'low'")

    def set_project_permission(self, project_id, allowed, expected_version=None):
        """Configuración explícita del propietario, con versión y revocación."""
        require_permission(self.principal,"action:execute")
        require_permission(self.principal,"memory:write")
        if type(allowed) is not bool: raise ValueError("permiso inválido")
        if expected_version is not None and (type(expected_version) is not int or expected_version<1):
            raise ValueError("versión inválida")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.projects._get(db,project_id) is None:
                raise KeyError("proyecto inexistente o sin acceso")
            row=db.execute("SELECT version FROM project_action_policies WHERE owner_id=? AND project_id=?",
                           (self.principal.owner_id,project_id)).fetchone()
            if row is None:
                if expected_version is not None: raise ProjectConflict("política desactualizada")
                db.execute("INSERT INTO project_action_policies(owner_id,project_id,allowed) VALUES(?,?,?)",
                           (self.principal.owner_id,project_id,int(allowed)))
                return 1
            if row[0]!=expected_version: raise ProjectConflict("política desactualizada")
            db.execute("UPDATE project_action_policies SET allowed=?,version=version+1 WHERE owner_id=? AND project_id=?",
                       (int(allowed),self.principal.owner_id,project_id))
            return row[0]+1

    def _policy(self,db,project_id):
        row=db.execute("SELECT allowed,version FROM project_action_policies WHERE owner_id=? AND project_id=?",
                       (self.principal.owner_id,project_id)).fetchone()
        # Compatibilidad con proyectos anteriores a la actividad 14.
        if row is None: return (1,0)
        return row

    def catalog(self):
        require_permission(self.principal,"memory:read")
        return ALLOWED

    def preview(self, action, project_id, params):
        require_permission(self.principal,"action:execute")
        require_permission(self.principal,"memory:read")
        if action not in ALLOWED:
            raise ValueError("acción no permitida")
        if not isinstance(params,dict) or set(params)!={"status"}:
            raise ValueError("parámetros no permitidos")
        status=params["status"]
        if not isinstance(status,str) or status not in STATES:
            raise ValueError("estado inválido")
        if not isinstance(project_id,str) or not project_id:
            raise ValueError("proyecto inválido")
        token=token_urlsafe(32)
        ticket_id=str(uuid4())
        expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=self.projects._get(db,project_id)
            if row is None: raise KeyError("proyecto inexistente o sin acceso")
            if row[4]==status: raise ValueError("el proyecto ya tiene ese estado")
            allowed,policy_version=self._policy(db,project_id)
            if not allowed: raise PermissionError("acción prohibida para este proyecto")
            risk="high" if status in ("archived","completed") else "low"
            db.execute("""INSERT INTO action_tickets
                (id,owner_id,project_id,action,before_status,after_status,project_version,secret_hash,expires_at)
                ,policy_version,risk) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (ticket_id,self.principal.owner_id,project_id,action,row[4],status,row[5],
                 sha256(token.encode()).hexdigest(),expires,policy_version,risk))
        return ActionPreview(ticket_id+"."+token,action,project_id,row[4],status,row[5],expires,False,risk)

    def confirm(self, ticket, confirmation):
        require_permission(self.principal,"action:execute")
        require_permission(self.principal,"memory:write")
        if confirmation not in ("CONFIRMAR ACCIÓN","CONFIRMAR ACCIÓN DE ALTO RIESGO"):
            raise PermissionError("confirmación explícita requerida")
        if not isinstance(ticket,str) or "." not in ticket:
            raise ValueError("ticket inválido")
        ticket_id,secret=ticket.split(".",1)
        if not ticket_id or not secret: raise ValueError("ticket inválido")
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("""SELECT project_id,action,before_status,after_status,
                project_version,secret_hash,expires_at,consumed,policy_version,risk FROM action_tickets
                WHERE id=? AND owner_id=?""",(ticket_id,self.principal.owner_id)).fetchone()
            if row is None or row[7] or not compare_digest(sha256(secret.encode()).hexdigest(),row[5]):
                raise PermissionError("ticket inválido, consumido o ajeno")
            if datetime.now(timezone.utc)>=datetime.fromisoformat(row[6]):
                raise PermissionError("ticket caducado")
            project_id,action,before,after,version=row[:5]
            if row[9]=="high" and confirmation!="CONFIRMAR ACCIÓN DE ALTO RIESGO":
                raise PermissionError("confirmación reforzada requerida")
            allowed,policy_version=self._policy(db,project_id)
            if not allowed or policy_version!=row[8]:
                raise PermissionError("política revocada o modificada")
            current=self.projects._get(db,project_id)
            if current is None or current[5]!=version or current[4]!=before:
                raise ProjectConflict("el proyecto cambió desde la simulación")
            updated=db.execute("""UPDATE registered_projects SET status=?,version=version+1,
                updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=? AND version=? AND status=?""",
                (after,project_id,self.principal.owner_id,version,before))
            if updated.rowcount!=1: raise ProjectConflict("cambio concurrente")
            db.execute("UPDATE action_tickets SET consumed=1 WHERE id=? AND owner_id=?",
                       (ticket_id,self.principal.owner_id))
            return ActionResult(action,project_id,before,after,version+1)
