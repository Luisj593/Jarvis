import tempfile
import unittest
from pathlib import Path
from jarvis_core.procedures import ProcedureRegistry,TaskConflict,DependencyBlocked
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class ProceduresTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.a=ProcedureRegistry(self.path,Principal("alice",FULL))
        self.b=ProcedureRegistry(self.path,Principal("bob",FULL))
        self.pa=self.a.projects.create("JARVIS","Desarrollo")
        self.pb=self.b.projects.create("JARVIS","Otro propietario")
        self.proc=self.a.create_procedure(self.pa.id,"Preparar lanzamiento")
    def tearDown(self):
        self.tmp.cleanup()

    def test_procedure_and_task_creation(self):
        t=self.a.add_task(self.pa.id,self.proc.id,"Auditar",assignee="equipo")
        self.assertEqual((t.position,t.status,t.version,t.assignee),(1,"pending",1,"equipo"))
        self.assertEqual(len(self.a.list_procedures(self.pa.id)),1)

    def test_multistep_dependency(self):
        first=self.a.add_task(self.pa.id,self.proc.id,"Auditar")
        second=self.a.add_task(self.pa.id,self.proc.id,"Probar",depends_on=(first.id,))
        self.assertEqual(second.depends_on,(first.id,))
        with self.assertRaises(DependencyBlocked):
            self.a.update_task(self.pa.id,self.proc.id,second.id,1,status="done")
        self.a.update_task(self.pa.id,self.proc.id,first.id,1,status="done")
        self.assertEqual(self.a.update_task(self.pa.id,self.proc.id,second.id,1,status="done").status,"done")

    def test_progress(self):
        t1=self.a.add_task(self.pa.id,self.proc.id,"Uno")
        self.a.add_task(self.pa.id,self.proc.id,"Dos")
        self.assertEqual(self.a.progress(self.pa.id,self.proc.id).percent,0)
        self.a.update_task(self.pa.id,self.proc.id,t1.id,1,status="done")
        self.assertEqual(self.a.progress(self.pa.id,self.proc.id).percent,50)

    def test_empty_progress(self):
        self.assertEqual(self.a.progress(self.pa.id,self.proc.id).percent,0)

    def test_optimistic_task_version(self):
        t=self.a.add_task(self.pa.id,self.proc.id,"Uno")
        self.a.update_task(self.pa.id,self.proc.id,t.id,1,status="in_progress")
        with self.assertRaises(TaskConflict):
            self.a.update_task(self.pa.id,self.proc.id,t.id,1,status="done")

    def test_procedure_version(self):
        self.a.add_task(self.pa.id,self.proc.id,"Uno",expected_version=1)
        with self.assertRaises(TaskConflict):
            self.a.add_task(self.pa.id,self.proc.id,"Dos",expected_version=1)

    def test_owner_isolation(self):
        with self.assertRaises(KeyError):
            self.b.list_tasks(self.pa.id,self.proc.id)
        with self.assertRaises(KeyError):
            self.b.add_task(self.pa.id,self.proc.id,"Invasión")

    def test_project_isolation(self):
        other=self.a.projects.create("OTRO","Separado")
        with self.assertRaises(KeyError):
            self.a.list_tasks(other.id,self.proc.id)
        with self.assertRaises(KeyError):
            self.a.add_task(other.id,self.proc.id,"No permitido")

    def test_foreign_dependency(self):
        other=self.a.create_procedure(self.pa.id,"Otro procedimiento")
        t=self.a.add_task(self.pa.id,other.id,"Ajena")
        with self.assertRaises(KeyError):
            self.a.add_task(self.pa.id,self.proc.id,"Nueva",depends_on=(t.id,))

    def test_reopen_prerequisite_blocked(self):
        a=self.a.add_task(self.pa.id,self.proc.id,"Uno")
        b=self.a.add_task(self.pa.id,self.proc.id,"Dos",depends_on=(a.id,))
        self.a.update_task(self.pa.id,self.proc.id,a.id,1,status="done")
        self.a.update_task(self.pa.id,self.proc.id,b.id,1,status="done")
        with self.assertRaises(DependencyBlocked):
            self.a.update_task(self.pa.id,self.proc.id,a.id,2,status="pending")

    def test_persistence(self):
        self.a.add_task(self.pa.id,self.proc.id,"Persistente")
        reopened=ProcedureRegistry(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.list_tasks(self.pa.id,self.proc.id)[0].title,"Persistente")

    def test_read_permission(self):
        limited=ProcedureRegistry(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError):
            limited.list_tasks(self.pa.id,self.proc.id)

    def test_write_permission(self):
        limited=ProcedureRegistry(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            limited.create_procedure(self.pa.id,"Nuevo")
        with self.assertRaises(PermissionError):
            limited.add_task(self.pa.id,self.proc.id,"Nuevo")

    def test_invalid_fields(self):
        with self.assertRaises(ValueError):
            self.a.create_procedure(self.pa.id,"")
        with self.assertRaises(ValueError):
            self.a.add_task(self.pa.id,self.proc.id,"x",assignee="")
        with self.assertRaises(ValueError):
            self.a.add_task(self.pa.id,self.proc.id,"x",depends_on=("same","same"))

    def test_no_implicit_execution(self):
        t=self.a.add_task(self.pa.id,self.proc.id,"Desplegar")
        self.assertEqual(t.status,"pending")
        self.assertFalse(hasattr(self.a,"execute"))

    def test_unknown_project(self):
        with self.assertRaises(KeyError):
            self.a.create_procedure("missing","Sin proyecto")

    def test_update_assignee_and_title(self):
        t=self.a.add_task(self.pa.id,self.proc.id,"Antes")
        updated=self.a.update_task(self.pa.id,self.proc.id,t.id,1,title="Después",assignee="Luis")
        self.assertEqual((updated.title,updated.assignee,updated.version),("Después","Luis",2))

    def test_no_changes(self):
        t=self.a.add_task(self.pa.id,self.proc.id,"Uno")
        with self.assertRaises(ValueError):
            self.a.update_task(self.pa.id,self.proc.id,t.id,1)

if __name__=="__main__":
    unittest.main()
