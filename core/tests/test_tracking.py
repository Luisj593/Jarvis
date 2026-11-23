import tempfile
import unittest
from pathlib import Path
from jarvis_core.tracking import ProjectTracking,DecisionConflict
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"db.sqlite"
        self.a=ProjectTracking(self.path,Principal("alice",FULL))
        self.b=ProjectTracking(self.path,Principal("bob",FULL))
        self.p=self.a.projects.create("JARVIS","Asistente")
        self.proc=self.a.procedures.create_procedure(self.p.id,"Auditoría")
    def tearDown(self): self.tmp.cleanup()

    def test_empty_report(self):
        r=self.a.report(self.p.id)
        self.assertEqual((r.procedures,r.tasks,r.percent,r.blockers),(1,0,0.0,()))

    def test_progress_and_dependency_blockers(self):
        x=self.a.procedures.add_task(self.p.id,self.proc.id,"Primero")
        self.a.procedures.add_task(self.p.id,self.proc.id,"Segundo",depends_on=(x.id,))
        r=self.a.report(self.p.id)
        self.assertEqual((r.tasks,r.completed,r.percent,len(r.blockers)),(2,0,0,1))
        self.a.procedures.update_task(self.p.id,self.proc.id,x.id,1,status="done")
        r=self.a.report(self.p.id)
        self.assertEqual((r.completed,r.percent,len(r.blockers)),(1,50,0))

    def test_explicit_blocked(self):
        t=self.a.procedures.add_task(self.p.id,self.proc.id,"Bloqueada")
        self.a.procedures.update_task(self.p.id,self.proc.id,t.id,1,status="blocked")
        self.assertEqual(self.a.report(self.p.id).blockers[0].reason,"explicitly_blocked")

    def test_cancelled_not_counted_as_completed(self):
        t=self.a.procedures.add_task(self.p.id,self.proc.id,"Cancelada")
        self.a.procedures.update_task(self.p.id,self.proc.id,t.id,1,status="cancelled")
        self.assertEqual(self.a.report(self.p.id).percent,0)

    def test_consolidated_reports(self):
        self.a.projects.create("Otro","Otro objetivo")
        self.assertEqual(len(self.a.reports()),2)

    def test_create_decision(self):
        d=self.a.decide(self.p.id,"No desplegar","Pruebas pendientes","Esperar")
        self.assertEqual((d.version,d.outcome),(1,"Esperar"))
        self.assertEqual(len(self.a.decisions(self.p.id)),1)

    def test_revise_and_history(self):
        d=self.a.decide(self.p.id,"A","Razón A","Esperar")
        newer=self.a.revise(self.p.id,d.id,1,"B","Razón B","Proceder")
        self.assertEqual(newer.version,2)
        self.assertEqual([x.outcome for x in self.a.history(self.p.id,d.id)],["Esperar","Proceder"])

    def test_conflict_preserves_history(self):
        d=self.a.decide(self.p.id,"A","B","C")
        self.a.revise(self.p.id,d.id,1,"A2","B2","C2")
        with self.assertRaises(DecisionConflict):
            self.a.revise(self.p.id,d.id,1,"A3","B3","C3")
        self.assertEqual(len(self.a.history(self.p.id,d.id)),2)

    def test_owner_isolation(self):
        d=self.a.decide(self.p.id,"Privado","Privado","Privado")
        with self.assertRaises(KeyError): self.b.report(self.p.id)
        with self.assertRaises(KeyError): self.b.decisions(self.p.id)
        with self.assertRaises(KeyError): self.b.history(self.p.id,d.id)
        with self.assertRaises(KeyError): self.b.revise(self.p.id,d.id,1,"X","Y","Z")

    def test_project_isolation(self):
        other=self.a.projects.create("Otro","Aparte")
        d=self.a.decide(self.p.id,"A","B","C")
        with self.assertRaises(KeyError): self.a.history(other.id,d.id)
        with self.assertRaises(KeyError): self.a.revise(other.id,d.id,1,"X","Y","Z")
        self.assertEqual(self.a.decisions(other.id),[])

    def test_permission_read(self):
        x=ProjectTracking(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError): x.report(self.p.id)
        with self.assertRaises(PermissionError): x.decisions(self.p.id)

    def test_permission_write(self):
        x=ProjectTracking(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError): x.decide(self.p.id,"A","B","C")
        d=self.a.decide(self.p.id,"A","B","C")
        with self.assertRaises(PermissionError): x.revise(self.p.id,d.id,1,"X","Y","Z")

    def test_persistence(self):
        d=self.a.decide(self.p.id,"A","B","C")
        reopened=ProjectTracking(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.history(self.p.id,d.id)[0].title,"A")

    def test_invalid_decision(self):
        with self.assertRaises(ValueError): self.a.decide(self.p.id,"","B","C")
        d=self.a.decide(self.p.id,"A","B","C")
        with self.assertRaises(ValueError): self.a.revise(self.p.id,d.id,True,"A","B","C")

    def test_unknown_project(self):
        with self.assertRaises(KeyError): self.a.decide("missing","A","B","C")

    def test_sql_injection(self):
        d=self.a.decide(self.p.id,"'; DROP TABLE project_decisions; --","B","C")
        self.assertEqual(len(self.a.history(self.p.id,d.id)),1)

    def test_no_external_execution(self):
        self.assertFalse(hasattr(self.a,"execute"))
        self.assertEqual(self.a.report(self.p.id).completed,0)

if __name__=="__main__":
    unittest.main()
