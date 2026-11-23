"""Aprendizaje supervisado de frases equivalentes, sin modelos externos.

Las expresiones se enseñan explícitamente. La resolución es exacta tras
normalización Unicode, espacios y puntuación; no presupone similitud semántica.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
import unicodedata
from uuid import uuid4
from .profile import ProfileMemory
from .security import Principal, require_permission

GLOBAL_SCOPE = "__global__"
MAX_EXPRESSION = 240
MAX_INTENT = 100

def normalize_expression(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("expresión inválida")
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())

@dataclass(frozen=True)
class IntentMatch:
    status: str
    intent: str | None = None
    scope: str | None = None
    candidates: tuple[str, ...] = ()

class ExampleLearning:
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.profile = ProfileMemory(path, principal.owner_id)
        self.store = self.profile._store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS intent_examples(
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                intent TEXT NOT NULL,
                expression TEXT NOT NULL,
                normalized TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_id,scope,intent,normalized)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS intent_examples_lookup ON intent_examples(owner_id,scope,normalized)")

    @staticmethod
    def _scope(project: str | None) -> str:
        if project is None:
            return GLOBAL_SCOPE
        if not isinstance(project, str) or not project.strip() or len(project) > 100 or project.strip() == GLOBAL_SCOPE:
            raise ValueError("proyecto inválido")
        return project.strip()

    @staticmethod
    def _validate(intent: str, expression: str) -> tuple[str,str]:
        if not isinstance(intent, str) or not intent.strip() or len(intent) > MAX_INTENT:
            raise ValueError("intención inválida")
        if not isinstance(expression, str) or not expression.strip() or len(expression) > MAX_EXPRESSION:
            raise ValueError("expresión inválida")
        normalized = normalize_expression(expression)
        if not normalized:
            raise ValueError("expresión sin contenido")
        return intent.strip(), normalized

    def teach(self, intent: str, expression: str, project: str | None = None) -> str:
        """Registra ejemplo. Una misma frase con distintas intenciones genera ambigüedad."""
        require_permission(self.principal, "memory:write")
        scope = self._scope(project)
        intent, normalized = self._validate(intent, expression)
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT id FROM intent_examples WHERE
                owner_id=? AND scope=? AND intent=? AND normalized=?""",
                (self.principal.owner_id, scope, intent, normalized)).fetchone()
            if row:
                return row[0]
            identifier = str(uuid4())
            db.execute("""INSERT INTO intent_examples(id,owner_id,scope,intent,expression,normalized)
                VALUES(?,?,?,?,?,?)""", (identifier,self.principal.owner_id,scope,intent,expression.strip(),normalized))
        return identifier

    def resolve(self, expression: str, project: str | None = None) -> IntentMatch:
        require_permission(self.principal, "memory:read")
        scope = self._scope(project)
        if not isinstance(expression, str) or len(expression) > MAX_EXPRESSION:
            raise ValueError("expresión inválida")
        normalized = normalize_expression(expression)
        if not normalized:
            return IntentMatch("unknown")
        with self.store._connect() as db:
            # El alcance del proyecto tiene prioridad. Solo si no hay coincidencias
            # se consulta la biblioteca global de ejemplos.
            scopes = [scope] if scope == GLOBAL_SCOPE else [scope, GLOBAL_SCOPE]
            for candidate_scope in scopes:
                rows = db.execute("""SELECT DISTINCT intent FROM intent_examples WHERE
                    owner_id=? AND scope=? AND normalized=? ORDER BY intent""",
                    (self.principal.owner_id,candidate_scope,normalized)).fetchall()
                candidates = tuple(row[0] for row in rows)
                if len(candidates) > 1:
                    return IntentMatch("ambiguous",scope=candidate_scope,candidates=candidates)
                if len(candidates) == 1:
                    return IntentMatch("matched",intent=candidates[0],scope=candidate_scope)
        return IntentMatch("unknown")

    def remove(self, identifier: str, project: str | None = None) -> bool:
        require_permission(self.principal, "memory:delete")
        scope = self._scope(project)
        if not isinstance(identifier,str) or not identifier.strip():
            raise ValueError("identificador inválido")
        with self.store._connect() as db:
            result = db.execute("""DELETE FROM intent_examples
                WHERE id=? AND owner_id=? AND scope=?""",
                (identifier,self.principal.owner_id,scope))
        return result.rowcount == 1

    def examples(self, intent: str, project: str | None = None) -> list[str]:
        require_permission(self.principal, "memory:read")
        scope = self._scope(project)
        if not isinstance(intent,str) or not intent.strip():
            raise ValueError("intención inválida")
        with self.store._connect() as db:
            rows = db.execute("""SELECT expression FROM intent_examples WHERE
                owner_id=? AND scope=? AND intent=? ORDER BY expression""",
                (self.principal.owner_id,scope,intent.strip())).fetchall()
        return [row[0] for row in rows]
