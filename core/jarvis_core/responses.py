"""Respuestas deterministas y conservadoras para el núcleo JARVIS.

Solo utiliza preferencias explícitas de formato. No inventa hechos, estados
de proyectos, resultados ni confirmaciones de acciones.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .conversation import ConversationContext, ConversationTurn
from .security import Principal, require_permission
from .examples import normalize_expression

@dataclass(frozen=True)
class PersonalizedResponse:
    text: str
    status: str
    intent: str | None
    project: str | None
    certainty: str
    source: str | None = None
    executed: bool = False

class ResponseComposer:
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.conversation = ConversationContext(path, principal)

    def _style(self) -> str:
        # Solo la preferencia general 'tono'; nunca consulta datos personales.
        entry = self.conversation.engine.profile.get("preference", "tono")
        if entry is None:
            return "normal"
        value = normalize_expression(entry.value)
        if value in ("breve", "conciso", "directo", "respuestas directas"):
            return "brief"
        if value in ("detallado", "explicativo", "formal"):
            return "detailed"
        return "normal"

    def compose(self, turn: ConversationTurn) -> PersonalizedResponse:
        require_permission(self.principal, "memory:read")
        if not isinstance(turn, ConversationTurn):
            raise ValueError("resultado de conversación inválido")
        style = self._style()
        if turn.status in ("matched", "referenced") and turn.intent:
            certainty = "recognized"
            if style == "brief":
                message = "Entendido: " + turn.intent + ". No he ejecutado acciones."
            elif style == "detailed":
                message = ("He reconocido la intención '" + turn.intent +
                           "' para el proyecto seleccionado. Esto no confirma el estado "
                           "del proyecto ni implica que se haya ejecutado alguna acción.")
            else:
                message = ("He identificado la intención '" + turn.intent +
                           "'. No he ejecutado ninguna acción.")
        elif turn.status == "ambiguous":
            certainty = "ambiguous"
            # Las opciones proceden del motor, no de generación libre.
            message = "Hay varias interpretaciones posibles: " + ", ".join(turn.candidates) + ". ¿Cuál deseas?"
        elif turn.status == "conflict":
            certainty = "conflict"
            message = "La instrucción entra en conflicto con una regla reservada. Necesito que la aclares."
        elif turn.status == "clarify":
            certainty = "insufficient"
            message = turn.response or "Necesito más información para continuar."
        else:
            certainty = "unknown"
            message = "No tengo información suficiente para interpretar esa solicitud. ¿Puedes explicarla?"
        return PersonalizedResponse(message,turn.status,turn.intent,turn.project,certainty,turn.source,False)

    def respond(self, session_id: str, text: str) -> PersonalizedResponse:
        require_permission(self.principal, "memory:read")
        turn = self.conversation.respond(session_id,text)
        return self.compose(turn)
