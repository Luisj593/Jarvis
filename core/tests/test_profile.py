import tempfile
import unittest
from pathlib import Path
from jarvis_core.profile import ProfileMemory

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"jarvis.sqlite"
        self.alice=ProfileMemory(self.path,"alice")
        self.bob=ProfileMemory(self.path,"bob")

    def tearDown(self):
        self.temp.cleanup()

    def test_personal_memory_persists(self):
        self.alice.put("personal","idioma","español dominicano")
        reopened=ProfileMemory(self.path,"alice")
        self.assertEqual(reopened.get("personal","idioma").value,"español dominicano")

    def test_preferences_global(self):
        self.alice.put("preference","estilo","respuestas directas")
        self.assertEqual(self.alice.context("proyecto A")[0].value,"respuestas directas")

    def test_project_isolation(self):
        self.alice.put("project","prioridad","inventario",project="A")
        self.alice.put("project","prioridad","facturación",project="B")
        self.assertEqual(self.alice.get("project","prioridad","A").value,"inventario")
        self.assertEqual(self.alice.get("project","prioridad","B").value,"facturación")
        self.assertNotIn("facturación",[e.value for e in self.alice.context("A")])

    def test_owner_isolation(self):
        self.alice.put("personal","idioma","privado")
        self.assertIsNone(self.bob.get("personal","idioma"))
        self.assertEqual(self.bob.list("personal"),[])
        self.assertFalse(self.bob.delete("personal","idioma"))

    def test_upsert_without_duplicates(self):
        first=self.alice.put("preference","tono","formal")
        second=self.alice.put("preference","tono","conciso")
        self.assertEqual(first.id,second.id)
        self.assertEqual(len(self.alice.list("preference")),1)
        self.assertEqual(second.value,"conciso")

    def test_delete_scoped(self):
        self.alice.put("project","estado","activo","A")
        self.alice.put("project","estado","pendiente","B")
        self.assertTrue(self.alice.delete("project","estado","A"))
        self.assertIsNone(self.alice.get("project","estado","A"))
        self.assertIsNotNone(self.alice.get("project","estado","B"))

    def test_no_personal_in_default_context(self):
        self.alice.put("personal","nombre","dato privado")
        self.alice.put("preference","tono","breve")
        self.assertEqual([x.category for x in self.alice.context("A")],["preference"])
        self.assertEqual(len(self.alice.context("A",include_personal=True)),2)

    def test_invalid_category_and_scope(self):
        with self.assertRaises(ValueError):
            self.alice.put("secret","x","y")
        with self.assertRaises(ValueError):
            self.alice.put("project","x","y")
        with self.assertRaises(ValueError):
            self.alice.put("personal","x","y","A")
        with self.assertRaises(ValueError):
            self.alice.put("project","x","y","__personal__")

    def test_invalid_data(self):
        with self.assertRaises(ValueError):
            self.alice.put("preference","","x")
        with self.assertRaises(ValueError):
            self.alice.put("preference","x","")
        with self.assertRaises(ValueError):
            self.alice.put("preference","x","y"*3001)

    def test_sql_injection_is_data(self):
        self.alice.put("project","'; DROP TABLE profile_memories; --","seguro","A")
        self.assertEqual(len(self.alice.list("project","A")),1)

    def test_no_implicit_learning(self):
        self.assertEqual(self.alice.list("personal"),[])
        self.assertEqual(self.alice.list("preference"),[])
        self.assertEqual(self.alice.list("project","A"),[])

if __name__=="__main__":
    unittest.main()
