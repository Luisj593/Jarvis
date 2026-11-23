import tempfile
import unittest
from pathlib import Path
from jarvis_core.examples import ExampleLearning,normalize_expression
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class ExamplesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.alice=ExampleLearning(self.path,Principal("alice",FULL))
        self.bob=ExampleLearning(self.path,Principal("bob",FULL))
    def tearDown(self):
        self.tmp.cleanup()

    def test_equivalent_phrases(self):
        self.alice.teach("report_status","dime el avance",project="JARVIS")
        self.alice.teach("report_status","cómo vamos",project="JARVIS")
        self.assertEqual(self.alice.resolve("¿Cómo vamos?",project="JARVIS").intent,"report_status")
        self.assertEqual(self.alice.resolve("DIME EL AVANCE!",project="JARVIS").intent,"report_status")

    def test_normalization(self):
        self.assertEqual(normalize_expression(" ¿CÓMO   vamos?! "),"como vamos")

    def test_ambiguity_not_guessed(self):
        self.alice.teach("open_project","abre el proyecto",project="JARVIS")
        self.alice.teach("summarize_project","abre el proyecto",project="JARVIS")
        result=self.alice.resolve("abre el proyecto",project="JARVIS")
        self.assertEqual(result.status,"ambiguous")
        self.assertIsNone(result.intent)
        self.assertEqual(result.candidates,("open_project","summarize_project"))

    def test_project_isolation(self):
        self.alice.teach("task_A","ver pendientes",project="A")
        self.alice.teach("task_B","ver pendientes",project="B")
        self.assertEqual(self.alice.resolve("ver pendientes",project="A").intent,"task_A")
        self.assertEqual(self.alice.resolve("ver pendientes",project="B").intent,"task_B")
        self.assertEqual(self.alice.resolve("ver pendientes",project="C").status,"unknown")

    def test_owner_isolation(self):
        self.alice.teach("private","informe privado",project="A")
        self.assertEqual(self.bob.resolve("informe privado",project="A").status,"unknown")

    def test_global_fallback(self):
        self.alice.teach("help","ayuda")
        self.assertEqual(self.alice.resolve("ayuda",project="A").intent,"help")

    def test_project_overrides_global(self):
        self.alice.teach("general_help","ayuda")
        self.alice.teach("project_help","ayuda",project="A")
        self.assertEqual(self.alice.resolve("ayuda",project="A").intent,"project_help")
        self.assertEqual(self.alice.resolve("ayuda",project="B").intent,"general_help")

    def test_ambiguity_blocks_global_fallback(self):
        self.alice.teach("general","ayuda")
        self.alice.teach("first","ayuda",project="A")
        self.alice.teach("second","ayuda",project="A")
        self.assertEqual(self.alice.resolve("ayuda",project="A").status,"ambiguous")

    def test_duplicate_idempotent(self):
        first=self.alice.teach("status","qué tal",project="A")
        second=self.alice.teach("status","QUE TAL!",project="A")
        self.assertEqual(first,second)
        self.assertEqual(len(self.alice.examples("status",project="A")),1)

    def test_remove_scoped(self):
        identifier=self.alice.teach("status","cómo vamos",project="A")
        self.assertFalse(self.alice.remove(identifier,project="B"))
        self.assertFalse(self.bob.remove(identifier,project="A"))
        self.assertTrue(self.alice.remove(identifier,project="A"))
        self.assertEqual(self.alice.resolve("cómo vamos",project="A").status,"unknown")

    def test_persistence(self):
        self.alice.teach("status","dame el estado",project="A")
        again=ExampleLearning(self.path,Principal("alice",FULL))
        self.assertEqual(again.resolve("dame el estado",project="A").intent,"status")

    def test_no_implicit_learning(self):
        self.assertEqual(self.alice.resolve("hola",project="A").status,"unknown")

    def test_permission_denied(self):
        reader=ExampleLearning(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            reader.teach("x","y")
        with self.assertRaises(PermissionError):
            reader.remove("id")
        self.alice.teach("x","y")
        self.assertEqual(reader.resolve("y").intent,"x")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.alice.teach("","hola")
        with self.assertRaises(ValueError):
            self.alice.teach("x","?!")
        with self.assertRaises(ValueError):
            self.alice.teach("x","hola",project="__global__")
        with self.assertRaises(ValueError):
            self.alice.resolve("x"*241)

    def test_no_substring_guessing(self):
        self.alice.teach("delete","elimina proyecto",project="A")
        self.assertEqual(self.alice.resolve("no elimines el proyecto",project="A").status,"unknown")

    def test_sql_injection_treated_as_data(self):
        self.alice.teach("x","'; DROP TABLE intent_examples; --",project="A")
        self.assertEqual(self.alice.resolve("DROP TABLE intent_examples",project="A").status,"matched")
        self.assertEqual(len(self.alice.examples("x",project="A")),1)

if __name__=="__main__":
    unittest.main()
