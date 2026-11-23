import tempfile
import unittest
from pathlib import Path
from jarvis_core.responses import ResponseComposer
from jarvis_core.conversation import ConversationTurn
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.a=ResponseComposer(self.path,Principal("alice",FULL))
        self.b=ResponseComposer(self.path,Principal("bob",FULL))
        self.a.conversation.engine.teach_example("status","dime el avance","A")
        self.a.conversation.select_project("s1","A")
    def tearDown(self):
        self.tmp.cleanup()

    def test_known_intent_no_fabricated_status(self):
        r=self.a.respond("s1","dime el avance")
        self.assertEqual((r.status,r.certainty,r.intent),("matched","recognized","status"))
        self.assertFalse(r.executed)
        self.assertNotIn("completado",r.text.lower())

    def test_brief_preference(self):
        self.a.conversation.engine.profile.put("preference","tono","breve")
        self.assertEqual(self.a.respond("s1","dime el avance").text,"Entendido: status. No he ejecutado acciones.")

    def test_detailed_preference(self):
        self.a.conversation.engine.profile.put("preference","tono","detallado")
        self.assertIn("no confirma el estado",self.a.respond("s1","dime el avance").text)

    def test_unknown_style_fallback(self):
        self.a.conversation.engine.profile.put("preference","tono","muy artístico")
        self.assertIn("No he ejecutado",self.a.respond("s1","dime el avance").text)

    def test_unknown_intent_requests_clarification(self):
        r=self.a.respond("s1","¿cómo está el servidor?")
        self.assertEqual((r.status,r.certainty),("unknown","unknown"))
        self.assertIn("¿Puedes explicarla?",r.text)

    def test_ambiguous_does_not_guess(self):
        self.a.conversation.engine.teach_example("open","abre","A")
        self.a.conversation.engine.teach_example("close","abre","A")
        r=self.a.respond("s1","abre")
        self.assertEqual(r.certainty,"ambiguous")
        self.assertIn("close",r.text)
        self.assertFalse(r.executed)

    def test_reserved_conflict(self):
        self.a.conversation.engine.teach_example("delete","qué recuerdas","A")
        r=self.a.respond("s1","qué recuerdas")
        self.assertEqual(r.certainty,"conflict")
        self.assertFalse(r.executed)

    def test_missing_project(self):
        r=self.a.respond("s2","dime el avance")
        self.assertEqual(r.certainty,"insufficient")
        self.assertIn("proyecto",r.text)

    def test_reference_context(self):
        self.a.respond("s1","dime el avance")
        r=self.a.respond("s1","eso")
        self.assertEqual(r.status,"referenced")
        self.assertEqual(r.intent,"status")
        self.assertFalse(r.executed)

    def test_owner_isolation(self):
        self.b.conversation.select_project("s1","A")
        self.assertEqual(self.b.respond("s1","dime el avance").status,"unknown")

    def test_project_isolation(self):
        self.a.conversation.select_project("s1","B")
        self.assertEqual(self.a.respond("s1","dime el avance").status,"unknown")

    def test_no_personal_data_leak(self):
        self.a.conversation.engine.profile.put("personal","nombre","INFORMACION_PRIVADA")
        self.a.conversation.engine.profile.put("preference","tono","breve")
        self.assertNotIn("INFORMACION_PRIVADA",self.a.respond("s1","dime el avance").text)

    def test_no_implicit_learning(self):
        self.a.respond("s1","frase nueva")
        self.assertEqual(self.a.conversation.engine.examples.resolve("frase nueva","A").status,"unknown")

    def test_permission_denied(self):
        restricted=ResponseComposer(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError):
            restricted.respond("s1","dime el avance")

    def test_invalid_turn(self):
        with self.assertRaises(ValueError):
            self.a.compose("texto")

    def test_empty_input(self):
        r=self.a.respond("s1","   ")
        self.assertEqual(r.certainty,"insufficient")

    def test_no_external_action(self):
        r=self.a.respond("s1","dime el avance")
        self.assertFalse(r.executed)
        self.assertFalse(hasattr(self.a,"execute"))

if __name__=="__main__":
    unittest.main()
