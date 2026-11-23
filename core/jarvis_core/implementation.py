"""Motor persistente de implementación: estados, evidencia y compuertas de seguridad.

No ejecuta código remoto ni despliega; un trabajador autorizado debe aportar
resultados verificables. Nunca interpreta 'solicitado' como 'completado'.
"""
import json
from dataclasses import asdict,dataclass
from uuid import uuid4
from .projects import ProjectRegistry
from .security import require_permission

STAGES=("analysis","plan","implementation","tests","verification","delivery")
TERMINAL=("completed","blocked","cancelled")
GATES=frozenset(("main_merge","production_deploy","database_migration","secrets_change","destructive_action"))
MAX_STEPS=100

class ExecutionConflict(Exception):pass

class ImplementationEngine:
 def __init__(self,path,principal):
  self.principal=principal
  self.projects=ProjectRegistry(path,principal)
  self.store=self.projects.store
  with self.store._connect() as db:
   db.execute("""CREATE TABLE IF NOT EXISTS implementation_runs(
     id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, project_id TEXT NOT NULL,
     request TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
     attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
     evidence TEXT NOT NULL DEFAULT '[]', blocker TEXT,
     created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
     updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
 def _get(self,db,run_id):
  row=db.execute("""SELECT id,project_id,request,stage,status,attempts,max_attempts,evidence,blocker
     FROM implementation_runs WHERE id=? AND owner_id=?""",(run_id,self.principal.owner_id)).fetchone()
  if not row:raise KeyError("ejecución inexistente")
  return {"id":row[0],"project_id":row[1],"request":row[2],"stage":row[3],
          "status":row[4],"attempts":row[5],"max_attempts":row[6],
          "evidence":json.loads(row[7]),"blocker":row[8]}
 def create(self,project_id,request,max_attempts=3):
  require_permission(self.principal,"memory:write")
  if not isinstance(request,str) or not request.strip() or len(request)>3000:raise ValueError("solicitud inválida")
  if type(max_attempts)!=int or not 1<=max_attempts<=10:raise ValueError("intentos inválidos")
  if not self.projects.get(project_id):raise KeyError("proyecto inexistente")
  run_id=str(uuid4())
  with self.store._connect() as db:
   db.execute("""INSERT INTO implementation_runs(id,owner_id,project_id,request,stage,status,max_attempts)
     VALUES(?,?,?,?,?,?,?)""",(run_id,self.principal.owner_id,project_id,request.strip(),"analysis","pending",max_attempts))
   return self._get(db,run_id)
 def get(self,run_id):
  require_permission(self.principal,"memory:read")
  with self.store._connect() as db:return self._get(db,run_id)
 def list(self):
  require_permission(self.principal,"memory:read")
  with self.store._connect() as db:
   ids=db.execute("SELECT id FROM implementation_runs WHERE owner_id=? ORDER BY created_at DESC,id",
       (self.principal.owner_id,)).fetchall()
   return [self._get(db,r[0]) for r in ids]
 def advance(self,run_id,stage,evidence,passed,gate=None):
  require_permission(self.principal,"memory:write")
  if stage not in STAGES or type(passed)!=bool:raise ValueError("estado inválido")
  if not isinstance(evidence,str) or not evidence.strip() or len(evidence)>4000:raise ValueError("evidencia requerida")
  if gate is not None and gate not in GATES:raise ValueError("compuerta desconocida")
  with self.store._connect() as db:
   db.execute("BEGIN IMMEDIATE")
   run=self._get(db,run_id)
   if run["status"] in TERMINAL:raise ExecutionConflict("ejecución cerrada")
   if run["stage"]!=stage:raise ExecutionConflict("etapa fuera de orden")
   events=run["evidence"]
   if gate:
    events.append({"stage":stage,"result":"approval_required","gate":gate,"evidence":evidence})
    status="blocked";next_stage=stage;blocker="approval_required:"+gate;attempts=run["attempts"]
   elif passed:
    events.append({"stage":stage,"result":"passed","evidence":evidence})
    idx=STAGES.index(stage)
    next_stage=STAGES[min(idx+1,len(STAGES)-1)]
    status="completed" if stage=="delivery" else "in_progress"
    blocker=None;attempts=0
   else:
    attempts=run["attempts"]+1
    events.append({"stage":stage,"result":"failed","evidence":evidence,"attempt":attempts})
    next_stage=stage
    status="blocked" if attempts>=run["max_attempts"] else "in_progress"
    blocker="retry_limit" if status=="blocked" else None
   db.execute("""UPDATE implementation_runs SET stage=?,status=?,attempts=?,evidence=?,blocker=?,
     updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=?""",
     (next_stage,status,attempts,json.dumps(events,ensure_ascii=False),blocker,run_id,self.principal.owner_id))
   return self._get(db,run_id)
