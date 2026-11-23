import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from jarvis_core.actions import ControlledActions
from jarvis_core.projects import ProjectConflict
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete","action:execute"})

class ActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"db.sqlite"
        self.a=ControlledActions(self.path,Principal("alice",FULL))
        self.b=ControlledActions(self.path,Principal("bob",FULL))
        self.project=self.a.projects.create("JARVIS","Asistente")
    def tearDown(self): self.tmp.cleanup()
    def preview(self): return self.a.preview("project.set_status",self.project.id,{"status":"active"})

    def test_catalog_closed(self):
        self.assertEqual(self.a.catalog(),("project.set_status",))
        with self.assertRaises(ValueError): self.a.preview("shell.exec",self.project.id,{"status":"active"})
    def test_preview_no_mutation(self):
        p=self.preview()
        self.assertFalse(p.executed)
        self.assertEqual(self.a.projects.get(self.project.id).status,"planned")
    def test_confirm(self):
        p=self.preview()
        result=self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertTrue(result.executed)
        self.assertEqual((result.after,result.version),("active",2))
    def test_confirmation_required(self):
        p=self.preview()
        with self.assertRaises(PermissionError): self.a.confirm(p.ticket,"sí")
        self.assertEqual(self.a.projects.get(self.project.id).status,"planned")
    def test_replay_denied(self):
        p=self.preview()
        self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        with self.assertRaises(PermissionError): self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_other_owner_ticket_denied(self):
        p=self.preview()
        with self.assertRaises(PermissionError): self.b.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_other_owner_project_denied(self):
        with self.assertRaises(KeyError): self.b.preview("project.set_status",self.project.id,{"status":"active"})
    def test_stale_preview(self):
        p=self.preview()
        self.a.projects.update(self.project.id,1,status="paused")
        with self.assertRaises(ProjectConflict): self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.a.projects.get(self.project.id).status,"paused")
    def test_invalid_params(self):
        for params in ({},{"status":"active","shell":"x"},{"status":"unknown"},["active"]):
            with self.subTest(params=params),self.assertRaises(ValueError):
                self.a.preview("project.set_status",self.project.id,params)
    def test_same_status_rejected(self):
        with self.assertRaises(ValueError):
            self.a.preview("project.set_status",self.project.id,{"status":"planned"})
    def test_tampered_token(self):
        p=self.preview()
        with self.assertRaises(PermissionError):
            self.a.confirm(p.ticket+"x","CONFIRMAR ACCIÓN")
    def test_expired_token(self):
        p=self.preview()
        identifier=p.ticket.split(".",1)[0]
        with self.a.store._connect() as db:
            db.execute("UPDATE action_tickets SET expires_at=? WHERE id=?",
                       ((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),identifier))
        with self.assertRaises(PermissionError): self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_missing_execute_permission(self):
        limited=ControlledActions(self.path,Principal("alice",frozenset({"memory:read","memory:write"})))
        with self.assertRaises(PermissionError):
            limited.preview("project.set_status",self.project.id,{"status":"active"})
        p=self.preview()
        with self.assertRaises(PermissionError): limited.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_missing_write_permission(self):
        limited=ControlledActions(self.path,Principal("alice",frozenset({"memory:read","action:execute"})))
        p=self.preview()
        with self.assertRaises(PermissionError): limited.confirm(p.ticket,"CONFIRMAR ACCIÓN")
    def test_missing_read_permission(self):
        limited=ControlledActions(self.path,Principal("alice",frozenset({"memory:write","action:execute"})))
        with self.assertRaises(PermissionError):
            limited.preview("project.set_status",self.project.id,{"status":"active"})
    def test_persistence(self):
        p=self.preview()
        reopened=ControlledActions(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.confirm(p.ticket,"CONFIRMAR ACCIÓN").after,"active")
    def test_invalid_ticket(self):
        with self.assertRaises(ValueError): self.a.confirm("invalid","CONFIRMAR ACCIÓN")
    def test_no_external_execution(self):
        self.assertFalse(hasattr(self.a,"shell"))
        self.assertFalse(hasattr(self.a,"deploy"))
    def test_project_isolation(self):
        other=self.a.projects.create("Otro","Objetivo")
        p=self.preview()
        self.assertEqual(self.a.projects.get(other.id).status,"planned")
        self.a.confirm(p.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.a.projects.get(other.id).status,"planned")

if __name__=="__main__":
    unittest.main()
