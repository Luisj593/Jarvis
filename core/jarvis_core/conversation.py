"""Contexto conversacional local por propietario y sesión; sin IA externa.

No se guarda el texto completo de los mensajes. Las referencias solo pueden
resolverse dentro de la misma sesión y el mismo proyecto seleccionado.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from .examples import normalize_expression
from .security import Principal, require_permission
from .unified import UnifiedIntentEngine, UnifiedResult

REFERENCES = frozenset({"ese proyecto", "este proyecto", "el proyecto", "lo anterior", "eso", "continua", "continua con eso"})
MAX_SESSION = 100

@dataclass(frozen=True)
class ConversationTurn:
    status: str
    project: str | None
    intent: str | None = None
    response: str = ""
    candidates: tuple[str, ...] = ()
    source: str | None = None

class ConversationContext:
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.engine = UnifiedIntentEngine(path, principal)
        self.store = self.engine.profile._store
        with self.store._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS conversation_sessions(
                owner_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                project TEXT,
                last_intent TEXT,
                last_status TEXT,
                PRIMARY KEY(owner_id,session_id)
            )""")

    @staticmethod
    def _session(session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id)>MAX_SESSION:
            raise ValueError("sesión inválida")
        return session_id.strip()

    def select_project(self, session_id: str, project: str) -> None:
        require_permission(self.principal, "memory:write")
        session_id=self._session(session_id)
        project=self.engine.examples._scope(project)
        if project=="__global__":
            raise ValueError("se requiere proyecto explícito")
        with self.store._connect() as db:
            db.execute("""INSERT INTO conversation_sessions(owner_id,session_id,project,last_intent,last_status)
                VALUES(?,?,?,NULL,NULL)
                ON CONFLICT(owner_id,session_id) DO UPDATE SET
                project=excluded.project,last_intent=NULL,last_status=NULL""",
                (self.principal.owner_id,session_id,project))

    def clear(self, session_id: str) -> bool:
        require_permission(self.principal, "memory:delete")
        session_id=self._session(session_id)
        with self.store._connect() as db:
            result=db.execute("DELETE FROM conversation_sessions WHERE owner_id=? AND session_id=?",
                              (self.principal.owner_id,session_id))
        return result.rowcount==1

    def _state(self, session_id: str):
        with self.store._connect() as db:
            return db.execute("""SELECT project,last_intent,last_status FROM conversation_sessions
                WHERE owner_id=? AND session_id=?""",(self.principal.owner_id,session_id)).fetchone()

    def respond(self, session_id: str, text: str) -> ConversationTurn:
        require_permission(self.principal, "memory:read")
        session_id=self._session(session_id)
        if not isinstance(text,str) or len(text)>240:
            raise ValueError("mensaje inválido")
        normalized=normalize_expression(text)
        if not normalized:
            return ConversationTurn("clarify",None,response="¿Qué deseas consultar?")
        state=self._state(session_id)
        if not state or not state[0]:
            return ConversationTurn("clarify",None,response="¿Sobre qué proyecto deseas conversar? Selecciónalo primero.")
        project,last_intent,last_status=state
        if normalized in REFERENCES:
            if not last_intent or last_status!="matched":
                return ConversationTurn("clarify",project,response="¿A qué instrucción anterior te refieres?")
            # Solo recupera la intención de la misma sesión y proyecto.
            return ConversationTurn("referenced",project,intent=last_intent,
                                    response="He identificado la intención anterior; no he ejecutado ninguna acción.",
                                    source="session")
        result=self.engine.resolve(text,project)
        if result.status=="matched":
            # El reconocimiento no ejecuta acciones, y se registra únicamente la
            # intención reconocida, nunca el texto o los datos personales.
            require_permission(self.principal,"memory:write")
            with self.store._connect() as db:
                db.execute("""UPDATE conversation_sessions SET last_intent=?,last_status=?
                    WHERE owner_id=? AND session_id=? AND project=?""",
                    (result.intent,result.status,self.principal.owner_id,session_id,project))
        elif result.status in ("ambiguous","conflict","unknown"):
            # Una duda invalida la referencia anterior para evitar acciones erróneas.
            require_permission(self.principal,"memory:write")
            with self.store._connect() as db:
                db.execute("""UPDATE conversation_sessions SET last_intent=NULL,last_status=?
                    WHERE owner_id=? AND session_id=? AND project=?""",
                    (result.status,self.principal.owner_id,session_id,project))
        return ConversationTurn(result.status,project,result.intent,result.response,result.candidates,result.source)
