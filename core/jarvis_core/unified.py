"""Motor unificado de intenciones, memoria y ejemplos; no ejecuta acciones.

El motor nunca aprende de una consulta. Las escrituras se realizan solo mediante
las operaciones explícitas de enseñanza/corrección de los módulos existentes.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .examples import ExampleLearning, normalize_expression
from .intent import classify
from .learning import VersionedLearning
from .profile import ProfileMemory, MemoryEntry
from .security import Principal, require_permission

@dataclass(frozen=True)
class UnifiedResult:
    status: str
    intent: str | None = None
    source: str | None = None
    candidates: tuple[str, ...] = ()
    context: tuple[MemoryEntry, ...] = ()
    response: str = ""

class UnifiedIntentEngine:
    """Enrutador de solo lectura. No convierte intenciones en acciones ejecutables."""
    def __init__(self, path: str | Path, principal: Principal):
        self.principal = principal
        self.examples = ExampleLearning(path, principal)
        self.learning = VersionedLearning(path, principal)
        self.profile = ProfileMemory(path, principal.owner_id)

    def resolve(self, text: str, project: str | None = None,
                include_personal: bool = False) -> UnifiedResult:
        require_permission(self.principal, "memory:read")
        # Validación previa incluso para comandos reservados.
        scope = self.examples._scope(project)
        if not isinstance(text, str) or len(text) > 240:
            raise ValueError("mensaje inválido")
        normalized = normalize_expression(text)
        if not normalized:
            return UnifiedResult("clarify", response="¿Qué deseas consultar?")
        # Reservar órdenes internas; una enseñanza no debe cambiar su significado.
        builtin = classify(text)
        reserved = builtin.name if builtin.name in ("teach", "recall") else None
        learned = self.examples.resolve(text, project)
        if learned.status == "ambiguous":
            return UnifiedResult("ambiguous", candidates=learned.candidates,
                                 response="La expresión tiene varias interpretaciones. Especifica cuál deseas.")
        if reserved and learned.status == "matched" and learned.intent != reserved:
            return UnifiedResult("conflict", candidates=tuple(sorted({reserved, learned.intent})),
                                 response="La expresión contradice un comando reservado. Corrige el ejemplo.")
        if reserved:
            # No escribir enseñanzas al reconocer una orden.
            return UnifiedResult("matched", intent=reserved, source="builtin",
                                 response="Comando reconocido; requiere procesamiento explícito.")
        if learned.status == "matched":
            return UnifiedResult("matched", intent=learned.intent, source="example",
                                 response="Intención reconocida; no se ha ejecutado ninguna acción.")
        return UnifiedResult("unknown", response="No tengo una intención enseñada para esa expresión.")

    def context(self, project: str | None = None,
                include_personal: bool = False) -> tuple[MemoryEntry, ...]:
        require_permission(self.principal, "memory:read")
        self.examples._scope(project)
        return tuple(self.profile.context(project, include_personal=include_personal))

    def current_rule(self, category: str, key: str, project: str | None = None):
        require_permission(self.principal, "memory:read")
        return self.learning.current(category, key, project)

    def teach_example(self, intent: str, expression: str, project: str | None = None) -> str:
        require_permission(self.principal, "memory:write")
        return self.examples.teach(intent, expression, project)

    def teach_rule(self, category: str, key: str, value: str, project: str | None = None):
        require_permission(self.principal, "memory:write")
        return self.learning.teach(category, key, value, project)

    def correct_rule(self, category: str, key: str, value: str, expected_version: int,
                     project: str | None = None):
        require_permission(self.principal, "memory:write")
        return self.learning.correct(category, key, value, expected_version, project)
