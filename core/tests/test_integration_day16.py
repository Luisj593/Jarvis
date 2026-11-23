"""Pruebas integrales de los módulos sin tocar Android ni servicios externos."""
import tempfile
import threading
import unittest
from pathlib import Path
from jarvis_core.security import Principal
from jarvis_core.conversation import ConversationContext
from jarvis_core.responses import ResponseComposer
from jarvis_core.projects import ProjectRegistry,ProjectConflict
from jarvis_core.procedures import ProcedureRegistry,DependencyBlocked
from jarvis_core.tracking import ProjectTracking
from jarvis_core.audit import AuditedActions,AuditIntegrityError

PERMS=frozenset({"memory:read","memory:write","memory:delete","action:execute"})

class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"integration.sqlite"
        self.alice=Principal("alice",PERMS)
        self.bob=Principal("bob",PERMS)
        self.projects=ProjectRegistry(self.path,self.alice)
        self.p=self.projects.create("JARVIS","Asistente sin modelos externos")
        self.procedures=ProcedureRegistry(self.path,self.alice)
        self.tracking=ProjectTracking(self.path,self.alice)
        self.actions=AuditedActions(self.path,self.alice)
    def tearDown(self):self.tmp.cleanup()

    def test_complete_project_lifecycle(self):
        proc=self.procedures.create_procedure(self.p.id,"Validación")
        first=self.procedures.add_task(self.p.id,proc.id,"Auditar")
        second=self.procedures.add_task(self.p.id,proc.id,"Verificar",depends_on=(first.id,))
        self.assertEqual(len(self.tracking.report(self.p.id).blockers),1)
        with self.assertRaises(DependencyBlocked):
            self.procedures.update_task(self.p.id,proc.id,second.id,1,status="done")
        self.procedures.update_task(self.p.id,proc.id,first.id,1,status="done")
        self.procedures.update_task(self.p.id,proc.id,second.id,1,status="done")
        self.assertEqual(self.tracking.report(self.p.id).percent,100)
        decision=self.tracking.decide(self.p.id,"Aprobar","Pruebas completadas","Permitir cambio local")
        self.assertEqual(len(self.tracking.history(self.p.id,decision.id)),1)
        preview=self.actions.preview("project.set_status",self.p.id,{"status":"completed"})
        self.assertEqual(preview.risk,"high")
        with self.assertRaises(PermissionError):
            self.actions.confirm(preview.ticket,"CONFIRMAR ACCIÓN")
        self.actions.confirm(preview.ticket,"CONFIRMAR ACCIÓN DE ALTO RIESGO")
        self.assertEqual(self.projects.get(self.p.id).status,"completed")
        self.assertTrue(self.actions.verify_integrity())

    def test_owner_isolation_across_modules(self):
        other=ProjectTracking(self.path,self.bob)
        with self.assertRaises(KeyError):other.report(self.p.id)
        with self.assertRaises(KeyError):other.decisions(self.p.id)
        with self.assertRaises(KeyError):AuditedActions(self.path,self.bob).history(self.p.id)
        with self.assertRaises(KeyError):ProcedureRegistry(self.path,self.bob).list_procedures(self.p.id)

    def test_conversation_and_response_isolation(self):
        a=ResponseComposer(self.path,self.alice)
        b=ResponseComposer(self.path,self.bob)
        a.conversation.engine.teach_example("status","estado del proyecto","JARVIS")
        a.conversation.select_project("s","JARVIS")
        b.conversation.select_project("s","JARVIS")
        self.assertEqual(a.respond("s","estado del proyecto").status,"matched")
        self.assertEqual(b.respond("s","estado del proyecto").status,"unknown")
        self.assertEqual(a.respond("s","eso").status,"referenced")

    def test_revoked_policy_prevents_action_and_logs_rejection(self):
        preview=self.actions.preview("project.set_status",self.p.id,{"status":"active"})
        self.actions.set_project_permission(self.p.id,False)
        with self.assertRaises(PermissionError):
            self.actions.confirm(preview.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.projects.get(self.p.id).status,"planned")
        self.assertEqual(self.actions.history()[-1].outcome,"rejected")
        self.assertTrue(self.actions.verify_integrity())

    def test_version_conflict_does_not_apply_action(self):
        preview=self.actions.preview("project.set_status",self.p.id,{"status":"active"})
        self.projects.update(self.p.id,1,status="paused")
        with self.assertRaises(ProjectConflict):
            self.actions.confirm(preview.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.projects.get(self.p.id).status,"paused")

    def test_recovery_requires_new_authorization(self):
        preview=self.actions.preview("project.set_status",self.p.id,{"status":"active"})
        self.actions.confirm(preview.ticket,"CONFIRMAR ACCIÓN")
        recovery=self.actions.recovery_preview(self.p.id,"planned")
        self.assertEqual(self.projects.get(self.p.id).status,"active")
        self.actions.confirm(recovery.ticket,"CONFIRMAR ACCIÓN")
        self.assertEqual(self.projects.get(self.p.id).status,"planned")

    def test_tamper_detection(self):
        self.actions.preview("project.set_status",self.p.id,{"status":"active"})
        with self.actions.store._connect() as db:
            db.execute("UPDATE jarvis_audit SET details='alterado' WHERE owner_id='alice'")
        with self.assertRaises(AuditIntegrityError):self.actions.verify_integrity()

    def test_concurrent_confirmation_once(self):
        preview=self.actions.preview("project.set_status",self.p.id,{"status":"active"})
        barrier=threading.Barrier(2)
        results=[]
        def worker():
            client=AuditedActions(self.path,self.alice)
            barrier.wait()
            try:
                client.confirm(preview.ticket,"CONFIRMAR ACCIÓN")
                results.append("ok")
            except PermissionError:results.append("denied")
        threads=[threading.Thread(target=worker) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=10)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertCountEqual(results,["ok","denied"])
        self.assertTrue(self.actions.verify_integrity())

    def test_no_external_execution(self):
        self.assertFalse(hasattr(self.actions,"deploy"))
        self.assertFalse(hasattr(self.actions,"shell"))

if __name__=="__main__":
    unittest.main()
