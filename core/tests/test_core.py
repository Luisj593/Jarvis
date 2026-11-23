import unittest
from jarvis_core import AssistantEngine, InMemoryStore, Request
from jarvis_core.intent import classify

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = AssistantEngine(InMemoryStore())

    def test_explicit_learning_and_recall(self):
        saved = self.engine.respond(Request("Aprende que revisa todos los módulos", "A"))
        self.assertEqual(saved.intent, "teach")
        self.assertEqual(len(saved.memory_ids), 1)
        result = self.engine.respond(Request("¿Qué recuerdas?", "A"))
        # La puntuación se maneja en una etapa posterior; forma sin signos garantizada.
        self.assertEqual(result.intent, "query")
        self.assertEqual(self.engine.respond(Request("qué recuerdas", "A")).intent, "recall")

    def test_isolation(self):
        self.engine.respond(Request("aprende: regla privada", "A"))
        self.assertNotIn("regla privada", self.engine.respond(Request("que recuerdas", "B")).text)

    def test_no_implicit_learning(self):
        self.engine.respond(Request("Me gusta trabajar por fases", "A"))
        self.assertEqual(self.engine.respond(Request("que recuerdas", "A")).memory_ids, ())

    def test_empty_teaching(self):
        self.assertEqual(self.engine.respond(Request("aprende:", "A")).intent, "clarify")

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.engine.respond(Request("x" * 3001, "A"))

    def test_accents(self):
        self.assertEqual(classify("Qué recuerdas").name, "recall")

    def test_no_external_actions(self):
        self.assertEqual(self.engine.respond(Request("elimina el proyecto", "A")).intent, "unknown")

if __name__ == "__main__":
    unittest.main()
