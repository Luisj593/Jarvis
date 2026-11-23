import tempfile
import unittest
from pathlib import Path
from jarvis_core.learning import VersionedLearning,VersionConflict
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.alice=VersionedLearning(self.path,Principal("alice",FULL))
        self.bob=VersionedLearning(self.path,Principal("bob",FULL))
    def tearDown(self):
        self.tmp.cleanup()
    def test_explicit_teach_and_persistence(self):
        a=self.alice.teach("preference","tono","breve")
        self.assertEqual(a.version,1)
        reopened=VersionedLearning(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.current("preference","tono").value,"breve")
    def test_no_silent_overwrite(self):
        self.alice.teach("personal","idioma","es")
        with self.assertRaises(ValueError):
            self.alice.teach("personal","idioma","en")
    def test_correction_history(self):
        self.alice.teach("preference","tono","formal")
        b=self.alice.correct("preference","tono","directo",1)
        self.assertEqual(b.version,2)
        self.assertEqual([x.value for x in self.alice.history("preference","tono")],["formal","directo"])
    def test_stale_version_conflict(self):
        self.alice.teach("preference","tono","formal")
        self.alice.correct("preference","tono","breve",1)
        with self.assertRaises(VersionConflict):
            self.alice.correct("preference","tono","otro",1)
    def test_soft_delete_and_restore(self):
        self.alice.teach("personal","idioma","es")
        d=self.alice.delete("personal","idioma",1)
        self.assertTrue(d.deleted)
        self.assertIsNone(self.alice.current("personal","idioma"))
        r=self.alice.restore("personal","idioma",2)
        self.assertFalse(r.deleted)
        self.assertEqual(r.version,3)
        self.assertEqual(len(self.alice.history("personal","idioma")),3)
    def test_revert_prior_version(self):
        self.alice.teach("project","regla","A","JARVIS")
        self.alice.correct("project","regla","B",1,"JARVIS")
        r=self.alice.revert("project","regla",2,1,"JARVIS")
        self.assertEqual(r.value,"A")
        self.assertEqual(r.version,3)
    def test_project_and_owner_isolation(self):
        self.alice.teach("project","regla","solo A","A")
        self.assertIsNone(self.alice.current("project","regla","B"))
        self.assertIsNone(self.bob.current("project","regla","A"))
        self.assertEqual(self.bob.history("project","regla","A"),[])
    def test_permission_denied(self):
        reader=VersionedLearning(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            reader.teach("preference","x","y")
        self.alice.teach("preference","x","y")
        with self.assertRaises(PermissionError):
            reader.delete("preference","x",1)
    def test_purge_requires_confirmation_and_soft_delete(self):
        self.alice.teach("personal","dato","valor")
        with self.assertRaises(PermissionError):
            self.alice.purge("personal","dato",1,"NO")
        with self.assertRaises(ValueError):
            self.alice.purge("personal","dato",1,"ELIMINAR DEFINITIVAMENTE")
        self.alice.delete("personal","dato",1)
        self.assertTrue(self.alice.purge("personal","dato",2,"ELIMINAR DEFINITIVAMENTE"))
        self.assertEqual(self.alice.history("personal","dato"),[])
    def test_purge_other_owner(self):
        self.alice.teach("personal","dato","privado")
        self.alice.delete("personal","dato",1)
        self.assertFalse(self.bob.purge("personal","dato",2,"ELIMINAR DEFINITIVAMENTE"))
        self.assertEqual(len(self.alice.history("personal","dato")),2)
    def test_invalid_historical_revision(self):
        self.alice.teach("preference","tono","A")
        with self.assertRaises(ValueError):
            self.alice.revert("preference","tono",1,99)
    def test_reteach_after_soft_delete_requires_restore(self):
        self.alice.teach("personal","idioma","es")
        self.alice.delete("personal","idioma",1)
        with self.assertRaises(ValueError):
            self.alice.teach("personal","idioma","en")
    def test_no_implicit_learning(self):
        self.assertIsNone(self.alice.current("preference","estilo"))
    def test_sql_payload_treated_as_data(self):
        self.alice.teach("project","'; DROP TABLE learning_items; --","texto","A")
        self.assertEqual(len(self.alice.history("project","'; DROP TABLE learning_items; --","A")),1)

if __name__=="__main__":
    unittest.main()
