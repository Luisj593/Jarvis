"""Orquestador: valida, interpreta y consulta memoria; sin red ni acciones externas."""
from .contracts import Request, Response
from .intent import classify, normalize
from .memory import MemoryStore

class AssistantEngine:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def respond(self, request: Request) -> Response:
        if not isinstance(request.text, str) or not isinstance(request.project, str):
            raise ValueError("invalid request")
        if len(request.text) > 3000 or not request.project.strip() or len(request.project) > 100:
            raise ValueError("invalid request size or project")
        intent = classify(request.text)
        if intent.name == "teach":
            if not intent.payload:
                return Response("Dime qué deseas enseñarme.", "clarify")
            lesson = self.memory.add(request.project, intent.payload)
            return Response("He guardado tu enseñanza.", "teach", (lesson.id,))
        if intent.name == "recall":
            lessons = self.memory.list(request.project)
            if not lessons:
                return Response("No tengo enseñanzas registradas en este proyecto.", "recall")
            return Response("Recuerdo: " + "; ".join(x.content for x in lessons[:8]), "recall", tuple(x.id for x in lessons[:8]))
        if intent.name == "query":
            # Coincidencia exacta, conservadora. No inventar comprensión semántica.
            matches = [x for x in self.memory.list(request.project) if normalize(x.content) == normalize(intent.payload)]
            if matches:
                return Response("Según tu enseñanza: " + matches[0].content, "query", (matches[0].id,))
            return Response("No tengo una regla verificada para esa solicitud. ¿Quieres enseñármela?", "unknown")
        return Response("¿Qué deseas que haga?", "clarify")
