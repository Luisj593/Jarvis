import tempfile
import unittest
from pathlib import Path
from jarvis_core.unified import UnifiedIntentEngine
from jarvis_core.security import Principal
from jarvis_core.learning import VersionConflict

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"memory.sqlite"
        self.a=UnifiedIntentEngine(self.path,Principal("alice",FULL))
        self.b=UnifiedIntentEngine(self.path,Principal("bob",FULL))
    def tearDown(self):
        self.tmp.cleanup()

    def test_equivalent_intents(self):
        self.a.teach_example("status","cómo vamos","A")
        self.a.teach_example("status","dame el avance","A")
        self.assertEqual(self.a.resolve("¿CÓMO VAMOS?", "A").intent,"status")
        self.assertEqual(self.a.resolve("Dame el avance!", "A").source,"example")

    def test_ambiguity(self):
        self.a.teach_example("open","abre","A")
        self.a.teach_example("summarize","abre","A")
        r=self.a.resolve("abre","A")
        self.assertEqual(r.status,"ambiguous")
        self.assertIsNone(r.intent)

    def test_reserved_conflict(self):
        self.a.teach_example("delete","qué recuerdas","A")
        r=self.a.resolve("qué recuerdas","A")
        self.assertEqual(r.status,"conflict")
        self.assertIn("recall",r.candidates)

    def test_reserved_builtin(self):
        self.assertEqual(self.a.resolve("qué recuerdas","A").intent,"recall")
        self.assertEqual(self.a.resolve("aprende: algo","A").intent,"teach")

    def test_builtin_same_intent(self):
        self.a.teach_example("recall","qué recuerdas","A")
        self.assertEqual(self.a.resolve("qué recuerdas","A").source,"builtin")

    def test_owner_isolation(self):
        self.a.teach_example("status","avance","A")
        self.assertEqual(self.b.resolve("avance","A").status,"unknown")
        self.a.teach_rule("project","estado","privado","A")
        self.assertIsNone(self.b.current_rule("project","estado","A"))

    def test_project_isolation(self):
        self.a.teach_example("a","avance","A")
        self.a.teach_example("b","avance","B")
        self.assertEqual(self.a.resolve("avance","A").intent,"a")
        self.assertEqual(self.a.resolve("avance","B").intent,"b")
        self.assertEqual(self.a.resolve("avance","C").status,"unknown")

    def test_profile_context_scoped(self):
        self.a.profile.put("preference","tono","breve")
        self.a.profile.put("personal","nombre","privado")
        self.a.profile.put("project","fase","pruebas","A")
        self.a.profile.put("project","fase","producción","B")
        values=[x.value for x in self.a.context("A")]
        self.assertEqual(values,["breve","pruebas"])
        self.assertNotIn("privado",values)
        self.assertNotIn("producción",values)

    def test_explicit_personal_context(self):
        self.a.profile.put("personal","idioma","es")
        self.assertEqual([x.value for x in self.a.context(include_personal=True)],["es"])

    def test_versioned_learning(self):
        a=self.a.teach_rule("project","regla","antes","A")
        self.assertEqual(a.version,1)
        b=self.a.correct_rule("project","regla","después",1,"A")
        self.assertEqual(b.version,2)
        self.assertEqual(self.a.current_rule("project","regla","A").value,"después")
        with self.assertRaises(VersionConflict):
            self.a.correct_rule("project","regla","mal",1,"A")

    def test_read_permission(self):
        denied=UnifiedIntentEngine(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError):
            denied.resolve("hola","A")
        with self.assertRaises(PermissionError):
            denied.context("A")
        with self.assertRaises(PermissionError):
            denied.current_rule("project","x","A")

    def test_write_permission(self):
        denied=UnifiedIntentEngine(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            denied.teach_example("x","hola","A")
        with self.assertRaises(PermissionError):
            denied.teach_rule("project","x","y","A")

    def test_no_implicit_learning(self):
        self.assertEqual(self.a.resolve("quiero que recuerdes esto","A").status,"unknown")
        self.assertEqual(self.a.examples.examples("memory","A"),[])

    def test_unknown_no_action(self):
        r=self.a.resolve("elimina toda la base de datos","A")
        self.assertEqual(r.status,"unknown")
        self.assertFalse(hasattr(r,"execute"))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.a.resolve("x"*241,"A")
        with self.assertRaises(ValueError):
            self.a.resolve("hola","__global__")

    def test_global_fallback(self):
        self.a.teach_example("help","ayuda")
        self.assertEqual(self.a.resolve("ayuda","A").intent,"help")

if __name__=="__main__":
    unittest.main()
