import tempfile
import time
import unittest
from pathlib import Path
from jarvis_core.actions import ControlledActions
from jarvis_core.audit import AuditedActions
from jarvis_core.security import Principal

PERMS=frozenset({"memory:read","memory:write","action:execute"})

class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"secure.sqlite"
        self.principal=Principal("owner",PERMS)
        self.audit=AuditedActions(self.path,self.principal,strict_policies=True)
        self.p=self.audit.actions.projects.create("Jarvis","Prueba")
    def tearDown(self):self.tmp.cleanup()
    def test_strict_default_denied(self):
        with self.assertRaises(PermissionError):
            self.audit.preview("project.set_status",self.p.id,{"status":"active"})
    def test_explicit_grant(self):
        self.audit.set_project_permission(self.p.id,True)
        p=self.audit.preview("project.set_status",self.p.id,{"status":"active"})
        self.audit.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.audit.actions.projects.get(self.p.id).status,"active")
        self.assertTrue(self.audit.verify_integrity())
    def test_strict_revocation(self):
        self.audit.set_project_permission(self.p.id,True)
        p=self.audit.preview("project.set_status",self.p.id,{"status":"active"})
        self.audit.set_project_permission(self.p.id,False,expected_version=1)
        with self.assertRaises(PermissionError):
            self.audit.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_audit_failure_rolls_back_action(self):
        self.audit.set_project_permission(self.p.id,True)
        p=self.audit.preview("project.set_status",self.p.id,{"status":"active"})
        with self.audit.store._connect() as db:
            db.execute("""CREATE TRIGGER deny_success BEFORE INSERT ON jarvis_audit
                WHEN NEW.kind='confirm' AND NEW.outcome='executed'
                BEGIN SELECT RAISE(ABORT,'audit unavailable'); END""")
        with self.assertRaises(Exception):
            self.audit.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.audit.actions.projects.get(self.p.id).status,"planned")
        with self.audit.store._connect() as db:
            db.execute("DROP TRIGGER deny_success")
        self.audit.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.audit.actions.projects.get(self.p.id).status,"active")
    def test_private_file_permissions(self):
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
    def test_no_token_in_audit(self):
        self.audit.set_project_permission(self.p.id,True)
        p=self.audit.preview("project.set_status",self.p.id,{"status":"active"})
        self.audit.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertNotIn(p.ticket,str(self.audit.history()))
    def test_legacy_mode_explicitly_opt_in(self):
        legacy=ControlledActions(self.path,self.principal,strict_policies=False)
        q=legacy.projects.create("Legacy","compatibilidad")
        self.assertEqual(legacy.preview("project.set_status",q.id,{"status":"active"}).risk,"low")
    def test_performance_smoke(self):
        self.audit.set_project_permission(self.p.id,True)
        start=time.perf_counter()
        for i in range(40):
            self.audit.preview("project.set_status",self.p.id,{"status":"active"})
        elapsed=time.perf_counter()-start
        self.assertEqual(len(self.audit.history()),41)
        self.assertTrue(self.audit.verify_integrity())
        # Umbral holgado para CI; no es benchmark de capacidad.
        self.assertLess(elapsed,15)

if __name__=="__main__":
    unittest.main()
