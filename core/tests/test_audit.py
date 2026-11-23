import tempfile
import threading
import unittest
from pathlib import Path
from jarvis_core.audit import AuditedActions,AuditIntegrityError
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","action:execute"})

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"audit.sqlite"
        self.a=AuditedActions(self.path,Principal("alice",FULL))
        self.b=AuditedActions(self.path,Principal("bob",FULL))
        self.p=self.a.actions.projects.create("A","B")
    def tearDown(self): self.tmp.cleanup()
    def test_preview_and_confirmation_audited(self):
        p=self.a.preview("project.set_status",self.p.id,{"status":"active"})
        self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual([x.outcome for x in self.a.history(self.p.id)],["approved","executed"])
    def test_rejected_preview(self):
        with self.assertRaises(ValueError):
            self.a.preview("shell.exec",self.p.id,{"status":"active"})
        self.assertEqual(self.a.history()[0].outcome,"rejected")
    def test_rejected_confirmation_no_token_leak(self):
        p=self.a.preview("project.set_status",self.p.id,{"status":"active"})
        with self.assertRaises(PermissionError):
            self.a.confirm(p.ticket,"incorrecto")
        self.assertNotIn(p.ticket,str(self.a.history()))
    def test_integrity(self):
        self.a.preview("project.set_status",self.p.id,{"status":"active"})
        self.assertTrue(self.a.verify_integrity())
    def test_tamper_detected(self):
        self.a.preview("project.set_status",self.p.id,{"status":"active"})
        with self.a.store._connect() as db:
            db.execute("UPDATE jarvis_audit SET outcome='forged' WHERE owner_id='alice'")
        with self.assertRaises(AuditIntegrityError): self.a.verify_integrity()
    def test_owner_isolation(self):
        self.a.preview("project.set_status",self.p.id,{"status":"active"})
        self.assertEqual(self.b.history(),[])
        with self.assertRaises(KeyError): self.b.history(self.p.id)
    def test_policy_audited(self):
        self.a.set_project_permission(self.p.id,False)
        self.assertEqual(self.a.history()[0].kind,"policy")
    def test_rejected_policy_audited(self):
        with self.assertRaises(ValueError): self.a.set_project_permission(self.p.id,"no")
        self.assertEqual(self.a.history()[0].outcome,"rejected")
    def test_recovery_requires_confirmation(self):
        p=self.a.preview("project.set_status",self.p.id,{"status":"active"})
        self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        recovery=self.a.recovery_preview(self.p.id,"planned")
        self.assertEqual(self.a.actions.projects.get(self.p.id).status,"active")
        self.a.confirm(recovery.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.a.actions.projects.get(self.p.id).status,"planned")
    def test_replay_logged(self):
        p=self.a.preview("project.set_status",self.p.id,{"status":"active"})
        self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        with self.assertRaises(PermissionError): self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.a.history()[-1].outcome,"rejected")
    def test_persistence(self):
        self.a.preview("project.set_status",self.p.id,{"status":"active"})
        reopened=AuditedActions(self.path,Principal("alice",FULL))
        self.assertTrue(reopened.verify_integrity())
    def test_read_permission(self):
        limited=AuditedActions(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError): limited.history()
    def test_concurrent_audit_chain(self):
        errors=[]
        def work(i):
            try: self.a.preview("not.allowed",self.p.id,{"status":"active"})
            except ValueError: pass
            except Exception as e: errors.append(e)
        threads=[threading.Thread(target=work,args=(i,)) for i in range(6)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertFalse(errors)
        self.assertEqual(len(self.a.history()),6)
        self.assertTrue(self.a.verify_integrity())
    def test_project_scope(self):
        q=self.a.actions.projects.create("C","D")
        self.a.preview("not.allowed",q.id,{"status":"active"}) if False else None
        with self.assertRaises(ValueError): self.a.preview("not.allowed",q.id,{"status":"active"})
        self.assertEqual(len(self.a.history(self.p.id)),0)
    def test_no_external_execution(self):
        self.assertFalse(hasattr(self.a,"deploy"))

if __name__=="__main__":
    unittest.main()
