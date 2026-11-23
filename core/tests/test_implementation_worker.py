import tempfile
import unittest
from pathlib import Path
from jarvis_core.security import Principal
from jarvis_core.projects import ProjectRegistry
from jarvis_core.implementation import ImplementationEngine
from jarvis_core.implementation_worker import AnalysisWorker

class WorkerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=str(Path(self.tmp.name)/"worker.sqlite")
  self.principal=Principal("owner",frozenset(("memory:read","memory:write")))
  self.project=ProjectRegistry(self.path,self.principal).create("Proyecto A","Pruebas")
  self.engine=ImplementationEngine(self.path,self.principal)
 def tearDown(self):self.tmp.cleanup()
 def test_resume_after_restart_and_no_false_completion(self):
  run=self.engine.create(self.project.id,"Revisar error de login")
  first=AnalysisWorker(self.path,self.principal).process_once()
  self.assertEqual(first[0]["result"],"intake_recorded")
  self.assertEqual(AnalysisWorker(self.path,self.principal).process_once(),[])
  state=self.engine.get(run["id"])
  self.assertEqual(state["stage"],"plan")
  self.assertEqual(state["status"],"in_progress")
  self.assertIn("source_code_not_inspected",state["evidence"][0]["evidence"])
 def test_scope_isolation(self):
  self.engine.create(self.project.id,"Diagnosticar")
  other=Principal("other",frozenset(("memory:read","memory:write")))
  self.assertEqual(AnalysisWorker(self.path,other).process_once(),[])
 def test_limit_validation(self):
  with self.assertRaises(ValueError):AnalysisWorker(self.path,self.principal).process_once(0)
if __name__=="__main__":unittest.main()
