import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from jarvis_core import AssistantEngine, Request
from jarvis_core.storage import SQLiteMemoryStore
from jarvis_core.security import Principal, require_permission

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.sqlite"
        self.alice = SQLiteMemoryStore(self.path, "alice")
        self.bob = SQLiteMemoryStore(self.path, "bob")

    def tearDown(self):
        self.temp.cleanup()

    def test_persists_between_instances(self):
        item = self.alice.add("work", "Revisar todo")
        reopened = SQLiteMemoryStore(self.path, "alice")
        self.assertEqual(reopened.list("work")[0].id, item.id)

    def test_owner_isolation(self):
        self.alice.add("work", "secreto")
        self.assertEqual(self.bob.list("work"), [])

    def test_project_isolation(self):
        self.alice.add("A", "regla A")
        self.assertEqual(self.alice.list("B"), [])

    def test_cannot_update_or_delete_other_owner(self):
        item = self.alice.add("A", "privado")
        self.assertFalse(self.bob.update("A", item.id, "cambio"))
        self.assertFalse(self.bob.delete("A", item.id))
        self.assertEqual(self.alice.list("A")[0].content, "privado")

    def test_cannot_update_other_project(self):
        item = self.alice.add("A", "privado")
        self.assertFalse(self.alice.update("B", item.id, "cambio"))

    def test_update_and_delete(self):
        item = self.alice.add("A", "antes")
        self.assertTrue(self.alice.update("A", item.id, "después"))
        self.assertEqual(self.alice.list("A")[0].content, "después")
        self.assertTrue(self.alice.delete("A", item.id))
        self.assertEqual(self.alice.list("A"), [])

    def test_rejects_invalid_content(self):
        with self.assertRaises(ValueError):
            self.alice.add("A", "")
        with self.assertRaises(ValueError):
            self.alice.add("A", "x" * 3001)

    def test_parameterized_sql(self):
        self.alice.add("A", "'; DROP TABLE lessons; --")
        self.assertEqual(len(self.alice.list("A")), 1)

    def test_file_private_permissions(self):
        if os.name == "posix":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_permission_denied(self):
        principal = Principal("alice", frozenset({"memory:read"}))
        require_permission(principal, "memory:read")
        with self.assertRaises(PermissionError):
            require_permission(principal, "memory:delete")

    def test_engine_uses_persistent_store(self):
        engine = AssistantEngine(self.alice)
        engine.respond(Request("aprende: prefiero validaciones rigurosas", "A"))
        other = AssistantEngine(SQLiteMemoryStore(self.path, "alice"))
        self.assertIn("prefiero validaciones", other.respond(Request("qué recuerdas", "A")).text)

if __name__ == "__main__":
    unittest.main()
