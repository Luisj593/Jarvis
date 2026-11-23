import tempfile
import unittest
from pathlib import Path
from jarvis_core.security import Principal
from jarvis_core.projects import ProjectRegistry
from jarvis_core.implementation import ImplementationEngine,ExecutionConflict,STAGES

class ImplementationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=str(Path(self.tmp.name)/"core.sqlite")
  self.owner=Principal("owner",frozenset(("memory:read","memory:write")))
  self.project=ProjectRegistry(self.path,self.owner).create("Demo","Probar ejecución")
  self.engine=ImplementationEngine(self.path,self.owner)
 def tearDown(self):self.tmp.cleanup()
 def test_full_sequence(self):
  run=self.engine.create(self.project.id,"Crear función")
  for stage in STAGES:
   run=self.engine.advance(run["id"],stage,"verificado:"+stage,True)
  self.assertEqual(run["status"],"completed")
  self.assertEqual(len(run["evidence"]),6)
 def test_retry_and_block(self):
  run=self.engine.create(self.project.id,"Corregir error",max_attempts=2)
  run=self.engine.advance(run["id"],"analysis","falló",False)
  self.assertEqual(run["status"],"in_progress")
  run=self.engine.advance(run["id"],"analysis","falló de nuevo",False)
  self.assertEqual(run["status"],"blocked")
  with self.assertRaises(ExecutionConflict):
   self.engine.advance(run["id"],"analysis","otra vez",True)
 def test_approval_gate(self):
  run=self.engine.create(self.project.id,"Publicar")
  run=self.engine.advance(run["id"],"analysis","requiere cambio main",True,gate="main_merge")
  self.assertEqual(run["blocker"],"approval_required:main_merge")
  self.assertEqual(run["status"],"blocked")
 def test_cannot_skip_stage_or_complete_without_evidence(self):
  run=self.engine.create(self.project.id,"Analizar")
  with self.assertRaises(ExecutionConflict):self.engine.advance(run["id"],"delivery","hecho",True)
  with self.assertRaises(ValueError):self.engine.advance(run["id"],"analysis","",True)
 def test_owner_isolation(self):
  run=self.engine.create(self.project.id,"Analizar")
  other=ImplementationEngine(self.path,Principal("other",frozenset(("memory:read","memory:write"))))
  with self.assertRaises(KeyError):other.get(run["id"])
  with self.assertRaises(KeyError):other.advance(run["id"],"analysis","hecho",True)
if __name__=="__main__":unittest.main()
