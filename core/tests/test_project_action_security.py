import tempfile
import threading
import unittest
from pathlib import Path
from jarvis_core.actions import ControlledActions
from jarvis_core.projects import ProjectConflict
from jarvis_core.security import Principal

PERMS=frozenset({"memory:read","memory:write","action:execute"})

class ProjectActionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"test.sqlite"
        self.a=ControlledActions(self.path,Principal("alice",PERMS))
        self.b=ControlledActions(self.path,Principal("bob",PERMS))
        self.p=self.a.projects.create("A","Objetivo")
        self.q=self.a.projects.create("B","Otro")
    def tearDown(self): self.tmp.cleanup()
    def preview(self,project=None,status="active"):
        return self.a.preview("project.set_status",project or self.p.id,{"status":status})

    def test_deny_project(self):
        self.a.set_project_permission(self.p.id,False)
        with self.assertRaises(PermissionError): self.preview()
        self.assertEqual(self.a.projects.get(self.p.id).status,"planned")

    def test_allow_project(self):
        self.a.set_project_permission(self.p.id,True)
        p=self.preview()
        self.assertEqual(self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN").after,"active")

    def test_project_specific(self):
        self.a.set_project_permission(self.p.id,False)
        self.assertEqual(self.preview(self.q.id).project_id,self.q.id)

    def test_revocation_invalidates_ticket(self):
        p=self.preview()
        self.a.set_project_permission(self.p.id,False)
        with self.assertRaises(PermissionError):
            self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")

    def test_policy_version_change_invalidates_ticket(self):
        self.a.set_project_permission(self.p.id,True)
        p=self.preview()
        self.a.set_project_permission(self.p.id,True,expected_version=1)
        with self.assertRaises(PermissionError):
            self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")

    def test_policy_conflict(self):
        self.a.set_project_permission(self.p.id,True)
        with self.assertRaises(ProjectConflict):
            self.a.set_project_permission(self.p.id,False,expected_version=2)

    def test_policy_missing_expected_version(self):
        with self.assertRaises(ProjectConflict):
            self.a.set_project_permission(self.p.id,True,expected_version=1)

    def test_high_risk_confirmation(self):
        p=self.preview(status="archived")
        self.assertEqual(p.risk,"high")
        with self.assertRaises(PermissionError):
            self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN DE ALTO RIESGO").after,"archived")

    def test_completed_is_high_risk(self):
        self.assertEqual(self.preview(status="completed").risk,"high")

    def test_low_risk_legacy_confirmation(self):
        p=self.preview()
        self.assertEqual(p.risk,"low")
        self.assertEqual(self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN").after,"active")

    def test_other_owner_cannot_change_policy(self):
        with self.assertRaises(KeyError):
            self.b.set_project_permission(self.p.id,True)

    def test_policy_permission(self):
        limited=ControlledActions(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            limited.set_project_permission(self.p.id,False)

    def test_concurrent_confirmation_one_wins(self):
        p=self.preview()
        results=[]
        barrier=threading.Barrier(2)
        def worker():
            client=ControlledActions(self.path,Principal("alice",PERMS))
            barrier.wait()
            try:
                client.confirm(p.ticket,"CONFIRMAR ACCIÓN")
                results.append("success")
            except (PermissionError,ProjectConflict):
                results.append("denied")
        threads=[threading.Thread(target=worker) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=10)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertCountEqual(results,["success","denied"])

    def test_invalid_permission_value(self):
        with self.assertRaises(ValueError):
            self.a.set_project_permission(self.p.id,1)

    def test_persistent_policy(self):
        self.a.set_project_permission(self.p.id,False)
        reopened=ControlledActions(self.path,Principal("alice",PERMS))
        with self.assertRaises(PermissionError):
            reopened.preview("project.set_status",self.p.id,{"status":"active"})

if __name__=="__main__":
    unittest.main()
