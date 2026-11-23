import sqlite3
import tempfile
import unittest
from pathlib import Path
from jarvis_core.projects import ProjectRegistry,ProjectConflict
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.a=ProjectRegistry(self.path,Principal("alice",FULL))
        self.b=ProjectRegistry(self.path,Principal("bob",FULL))
    def tearDown(self):
        self.tmp.cleanup()
    def test_create_defaults(self):
        p=self.a.create("JARVIS","Asistente personal")
        self.assertEqual((p.priority,p.status,p.version),("medium","planned",1))
    def test_persistence(self):
        p=self.a.create("JARVIS","Asistente")
        reopened=ProjectRegistry(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.get(p.id).objective,"Asistente")
    def test_owner_isolation(self):
        p=self.a.create("JARVIS","Privado")
        self.assertIsNone(self.b.get(p.id))
        self.assertEqual(self.b.list(),[])
        with self.assertRaises(KeyError):
            self.b.update(p.id,1,status="active")
    def test_same_name_different_owners(self):
        self.a.create("JARVIS","A")
        self.b.create("JARVIS","B")
        self.assertEqual(self.b.list()[0].objective,"B")
    def test_duplicate_same_owner(self):
        self.a.create("JARVIS","A")
        with self.assertRaises(sqlite3.IntegrityError):
            self.a.create("JARVIS","B")
    def test_update_fields(self):
        p=self.a.create("JARVIS","A")
        q=self.a.update(p.id,1,name="JARVIS 2",objective="B",priority="high",status="active")
        self.assertEqual((q.name,q.objective,q.priority,q.status,q.version),("JARVIS 2","B","high","active",2))
    def test_conflict(self):
        p=self.a.create("JARVIS","A")
        self.a.update(p.id,1,status="active")
        with self.assertRaises(ProjectConflict):
            self.a.update(p.id,1,status="paused")
        self.assertEqual(self.a.get(p.id).status,"active")
    def test_list_filter(self):
        self.a.create("A","uno",status="active")
        self.a.create("B","dos",status="paused")
        self.assertEqual([p.name for p in self.a.list(status="active")],["A"])
    def test_invalid_fields(self):
        with self.assertRaises(ValueError): self.a.create("","A")
        with self.assertRaises(ValueError): self.a.create("A","")
        with self.assertRaises(ValueError): self.a.create("A","B",priority="urgent")
        with self.assertRaises(ValueError): self.a.create("A","B",status="unknown")
    def test_invalid_update(self):
        p=self.a.create("A","B")
        with self.assertRaises(ValueError): self.a.update(p.id,1)
        with self.assertRaises(ValueError): self.a.update(p.id,True,status="active")
        with self.assertRaises(ValueError): self.a.update(p.id,1,priority="wrong")
    def test_delete_confirmation(self):
        p=self.a.create("A","B")
        with self.assertRaises(PermissionError): self.a.delete(p.id,1,"NO")
        self.assertIsNotNone(self.a.get(p.id))
        self.assertTrue(self.a.delete(p.id,1,"ELIMINAR PROYECTO"))
        self.assertIsNone(self.a.get(p.id))
    def test_delete_conflict(self):
        p=self.a.create("A","B")
        self.a.update(p.id,1,status="active")
        with self.assertRaises(ProjectConflict): self.a.delete(p.id,1,"ELIMINAR PROYECTO")
    def test_delete_owner_isolation(self):
        p=self.a.create("A","B")
        self.assertFalse(self.b.delete(p.id,1,"ELIMINAR PROYECTO"))
        self.assertIsNotNone(self.a.get(p.id))
    def test_read_permission(self):
        limited=ProjectRegistry(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError): limited.list()
        with self.assertRaises(PermissionError): limited.get("x")
    def test_write_permission(self):
        limited=ProjectRegistry(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError): limited.create("A","B")
        p=self.a.create("A","B")
        with self.assertRaises(PermissionError): limited.update(p.id,1,status="active")
    def test_delete_permission(self):
        p=self.a.create("A","B")
        limited=ProjectRegistry(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError): limited.delete(p.id,1,"ELIMINAR PROYECTO")
    def test_no_implicit_project_creation(self):
        self.assertEqual(self.a.list(),[])
    def test_sql_injection_data(self):
        p=self.a.create("'; DROP TABLE registered_projects; --","Objetivo")
        self.assertEqual(self.a.get(p.id).name,"'; DROP TABLE registered_projects; --")
        self.assertEqual(len(self.a.list()),1)
    def test_independent_from_memory(self):
        p=self.a.create("A","B")
        self.a.delete(p.id,1,"ELIMINAR PROYECTO")
        self.assertEqual(self.a.list(),[])

if __name__=="__main__":
    unittest.main()
