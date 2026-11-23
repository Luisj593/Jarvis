"""Memoria explícita con aislamiento por proyecto; implementación en RAM para pruebas."""
from dataclasses import dataclass
from uuid import uuid4
from typing import Protocol

@dataclass(frozen=True)
class Lesson:
    id: str
    project: str
    content: str

class MemoryStore(Protocol):
    def add(self, project: str, content: str) -> Lesson: ...
    def list(self, project: str) -> list[Lesson]: ...

class InMemoryStore:
    def __init__(self):
        self._items: dict[str, Lesson] = {}

    def add(self, project: str, content: str) -> Lesson:
        if not project.strip() or not content.strip():
            raise ValueError("project and content are required")
        item = Lesson(str(uuid4()), project.strip(), content.strip())
        self._items[item.id] = item
        return item

    def list(self, project: str) -> list[Lesson]:
        # Las enseñanzas de otros proyectos nunca se devuelven.
        return [item for item in self._items.values() if item.project == project]
