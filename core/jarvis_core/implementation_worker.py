"""Trabajador persistente de análisis seguro.

Solo procesa la fase de análisis usando el inventario local y evidencias
observadas; nunca ejecuta código externo ni cambia proyectos.
"""
import json
import os
from datetime import datetime,timezone
from .implementation import ImplementationEngine
from .projects import ProjectRegistry
from .security import Principal

class AnalysisWorker:
 def __init__(self,path,principal):
  self.engine=ImplementationEngine(path,principal)
  self.projects=ProjectRegistry(path,principal)
  self.principal=principal
  self.store=self.engine.store
  with self.store._connect() as db:
   db.execute("""CREATE TABLE IF NOT EXISTS implementation_worker_leases(
     run_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,
     lease_until TEXT NOT NULL,claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
 def pending(self):
  return [r for r in self.engine.list() if r["stage"]=="analysis" and r["status"] in ("pending","in_progress")]
 def analyze(self,run_id):
  run=self.engine.get(run_id)
  if run["stage"]!="analysis" or run["status"] not in ("pending","in_progress"):
   return {"run_id":run_id,"result":"not_eligible"}
  project=self.projects.get(run["project_id"])
  if not project:raise KeyError("proyecto no disponible")
  request=run["request"].strip()
  evidence=json.dumps({"kind":"static_intake","project":project.name,
    "objective":project.objective,"request":request,
    "checks":["scope_identified","request_recorded","owner_isolated"],
    "limitations":["source_code_not_inspected","no_runtime_tests","no_automated_edits"],
    "next":"human_or_authorized_executor_must_plan"},ensure_ascii=False)
  updated=self.engine.advance(run_id,"analysis",evidence,True)
  return {"run_id":run_id,"result":"intake_recorded","status":updated["status"],
          "stage":updated["stage"],"evidence":evidence}
 def process_once(self,limit=10):
  if type(limit)!=int or not 1<=limit<=20:raise ValueError("límite inválido")
  # El estado se conserva en SQLite; si se reinicia el proceso, las tareas
  # pendientes se recuperan en la próxima invocación.
  outcomes=[]
  for run in self.pending()[:limit]:
   try:outcomes.append(self.analyze(run["id"]))
   except (KeyError,ValueError) as exc:
    outcomes.append({"run_id":run["id"],"result":"blocked","error":type(exc).__name__})
  return outcomes
