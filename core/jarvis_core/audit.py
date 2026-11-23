"""Auditoría encadenada de operaciones y recuperación compensatoria explícita."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from .actions import ControlledActions
from .security import Principal, require_permission

@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    owner_id: str
    project_id: str
    kind: str
    outcome: str
    details: str
    previous_hash: str
    event_hash: str

class AuditIntegrityError(Exception):
    pass

class AuditedActions:
    """Fachada explícita: operaciones deben pasar por esta API para ser auditadas."""
    def __init__(self,path: str | Path,principal: Principal, *, strict_policies=False):
        self.principal=principal
        self.actions=ControlledActions(path,principal,strict_policies=strict_policies)
        self.store=self.actions.store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jarvis_audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,
                project_id TEXT NOT NULL,kind TEXT NOT NULL,outcome TEXT NOT NULL,
                details TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS audit_owner_project ON jarvis_audit(owner_id,project_id,seq)")

    @staticmethod
    def _digest(owner,project,kind,outcome,details,previous):
        body=json.dumps([owner,project,kind,outcome,details,previous],ensure_ascii=False,separators=(",",":"))
        return sha256(body.encode("utf-8")).hexdigest()

    def _record_in_transaction(self,db,project_id,kind,outcome,details):
        # Datos de auditoría no incluyen secretos ni tickets.
        details=json.dumps(details,sort_keys=True,ensure_ascii=False,separators=(",",":"))
        row=db.execute("SELECT event_hash FROM jarvis_audit WHERE owner_id=? ORDER BY seq DESC LIMIT 1",
                       (self.principal.owner_id,)).fetchone()
        previous=row[0] if row else "GENESIS"
        digest=self._digest(self.principal.owner_id,project_id,kind,outcome,details,previous)
        db.execute("""INSERT INTO jarvis_audit(owner_id,project_id,kind,outcome,details,previous_hash,event_hash)
            VALUES(?,?,?,?,?,?,?)""",(self.principal.owner_id,project_id,kind,outcome,details,previous,digest))

    def _record(self,project_id,kind,outcome,details):
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._record_in_transaction(db,project_id,kind,outcome,details)

    def preview(self,action,project_id,params):
        try:
            result=self.actions.preview(action,project_id,params)
        except (PermissionError,ValueError,KeyError) as exc:
            self._record(project_id if isinstance(project_id,str) else "unknown",
                         "preview","rejected",{"reason":type(exc).__name__})
            raise
        self._record(project_id,"preview","approved",{"action":action,"risk":result.risk})
        return result

    def confirm(self,ticket,confirmation):
        try:
            result=self.actions.confirm(ticket,confirmation,audit_callback=lambda db,r: self._record_in_transaction(
                db,r.project_id,"confirm","executed",{"action":r.action,"before":r.before,
                "after":r.after,"version":r.version}))
        except Exception as exc:
            # Se registra la categoría, nunca el token ni la frase suministrada.
            self._record("unknown","confirm","rejected",{"reason":type(exc).__name__})
            raise
        return result

    def set_project_permission(self,project_id,allowed,expected_version=None):
        try:
            version=self.actions.set_project_permission(project_id,allowed,expected_version)
        except (PermissionError,ValueError,KeyError,Exception) as exc:
            self._record(project_id if isinstance(project_id,str) else "unknown",
                         "policy","rejected",{"reason":type(exc).__name__})
            raise
        self._record(project_id,"policy","updated",{"allowed":allowed,"version":version})
        return version

    def history(self,project_id=None):
        require_permission(self.principal,"memory:read")
        with self.store._connect() as db:
            if project_id is None:
                rows=db.execute("""SELECT seq,owner_id,project_id,kind,outcome,details,previous_hash,event_hash
                    FROM jarvis_audit WHERE owner_id=? ORDER BY seq""",
                    (self.principal.owner_id,)).fetchall()
            else:
                if self.actions.projects._get(db,project_id) is None:
                    raise KeyError("proyecto inexistente o sin acceso")
                rows=db.execute("""SELECT seq,owner_id,project_id,kind,outcome,details,previous_hash,event_hash
                    FROM jarvis_audit WHERE owner_id=? AND project_id=? ORDER BY seq""",
                    (self.principal.owner_id,project_id)).fetchall()
        return [AuditEvent(*r) for r in rows]

    def verify_integrity(self):
        require_permission(self.principal,"memory:read")
        previous="GENESIS"
        for event in self.history():
            expected=self._digest(event.owner_id,event.project_id,event.kind,
                                  event.outcome,event.details,previous)
            if event.previous_hash!=previous or event.event_hash!=expected:
                raise AuditIntegrityError("cadena de auditoría alterada")
            previous=event.event_hash
        return True

    def recovery_preview(self,project_id,previous_status):
        """Compensación NO automática; requiere autorización normal y nuevo ticket."""
        require_permission(self.principal,"action:execute")
        return self.preview("project.set_status",project_id,{"status":previous_status})
