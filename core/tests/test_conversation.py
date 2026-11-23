import tempfile
import unittest
from pathlib import Path
from jarvis_core.conversation import ConversationContext
from jarvis_core.security import Principal

FULL=frozenset({"memory:read","memory:write","memory:delete"})

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"jarvis.sqlite"
        self.alice=ConversationContext(self.path,Principal("alice",FULL))
        self.bob=ConversationContext(self.path,Principal("bob",FULL))
        self.alice.engine.teach_example("status","dime el avance","A")
        self.alice.engine.teach_example("inventory","ver inventario","B")
    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_project_selection(self):
        self.assertEqual(self.alice.respond("s1","dime el avance").status,"clarify")

    def test_session_reference(self):
        self.alice.select_project("s1","A")
        self.assertEqual(self.alice.respond("s1","dime el avance").intent,"status")
        r=self.alice.respond("s1","lo anterior")
        self.assertEqual((r.status,r.intent,r.project),("referenced","status","A"))

    def test_same_owner_session_isolation(self):
        self.alice.select_project("s1","A")
        self.alice.select_project("s2","A")
        self.alice.respond("s1","dime el avance")
        self.assertEqual(self.alice.respond("s2","eso").status,"clarify")

    def test_owner_isolation(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        self.assertEqual(self.bob.respond("s1","eso").status,"clarify")

    def test_project_change_clears_reference(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        self.alice.select_project("s1","B")
        self.assertEqual(self.alice.respond("s1","lo anterior").status,"clarify")
        self.assertEqual(self.alice.respond("s1","ver inventario").intent,"inventory")

    def test_unknown_invalidates_reference(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        self.assertEqual(self.alice.respond("s1","frase desconocida").status,"unknown")
        self.assertEqual(self.alice.respond("s1","eso").status,"clarify")

    def test_ambiguity_invalidates_reference(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        self.alice.engine.teach_example("open","abre","A")
        self.alice.engine.teach_example("close","abre","A")
        self.assertEqual(self.alice.respond("s1","abre").status,"ambiguous")
        self.assertEqual(self.alice.respond("s1","eso").status,"clarify")

    def test_clear_session(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        self.assertTrue(self.alice.clear("s1"))
        self.assertEqual(self.alice.respond("s1","eso").status,"clarify")

    def test_persistence(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        reopened=ConversationContext(self.path,Principal("alice",FULL))
        self.assertEqual(reopened.respond("s1","lo anterior").intent,"status")

    def test_no_full_transcript_storage(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        with self.alice.store._connect() as db:
            cols=[r[1] for r in db.execute("PRAGMA table_info(conversation_sessions)")]
        self.assertNotIn("message_text",cols)
        self.assertNotIn("transcript",cols)

    def test_permission_read(self):
        restricted=ConversationContext(self.path,Principal("alice",frozenset({"memory:write"})))
        with self.assertRaises(PermissionError):
            restricted.respond("s1","hola")

    def test_permission_write(self):
        restricted=ConversationContext(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            restricted.select_project("s1","A")
        self.alice.select_project("s1","A")
        with self.assertRaises(PermissionError):
            restricted.respond("s1","dime el avance")

    def test_permission_delete(self):
        restricted=ConversationContext(self.path,Principal("alice",frozenset({"memory:read"})))
        with self.assertRaises(PermissionError):
            restricted.clear("s1")

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.alice.select_project("","A")
        with self.assertRaises(ValueError):
            self.alice.respond("s1","x"*241)
        with self.assertRaises(ValueError):
            self.alice.select_project("s1","__global__")

    def test_no_implicit_learning(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","una frase nueva")
        self.assertEqual(self.alice.engine.examples.resolve("una frase nueva","A").status,"unknown")

    def test_reference_does_not_execute(self):
        self.alice.select_project("s1","A")
        self.alice.respond("s1","dime el avance")
        result=self.alice.respond("s1","continúa")
        self.assertEqual(result.status,"referenced")
        self.assertFalse(hasattr(result,"execute"))

if __name__=="__main__":
    unittest.main()
